from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.utils import timezone
from institucional.models import AuditoriaAcceso, TipoAccion, Usuario, Persona, TipoAccionDatos
from institucional.auditoria import registrar_cambio, obtener_valores_modelo, set_current_user, set_current_ip
import threading

# Thread-local storage para mantener el estado original de la instancia antes de guardarse
_original_instance_data = threading.local()

def obtener_ip_cliente(request):
    """Obtiene la IP del cliente desde el request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def obtener_user_agent(request):
    """Obtiene el User-Agent desde el request"""
    return request.META.get('HTTP_USER_AGENT', '')


@receiver(user_logged_in)
def registrar_login(sender, request, user, **kwargs):
    """Registra cuando un usuario inicia sesión exitosamente"""
    AuditoriaAcceso.objects.create(
        usuario=user,
        email=user.email,
        tipo_accion=TipoAccion.LOGIN,
        ip_address=obtener_ip_cliente(request),
        user_agent=obtener_user_agent(request),
        exitoso=True,
        detalles=f"Login exitoso para {user.email}"
    )


@receiver(user_logged_out)
def registrar_logout(sender, request, user, **kwargs):
    """Registra cuando un usuario cierra sesión"""
    if user:
        AuditoriaAcceso.objects.create(
            usuario=user,
            email=user.email,
            tipo_accion=TipoAccion.LOGOUT,
            ip_address=obtener_ip_cliente(request),
            user_agent=obtener_user_agent(request),
            exitoso=True,
            detalles=f"Logout exitoso para {user.email}"
        )


@receiver(user_login_failed)
def registrar_login_fallido(sender, credentials, request, **kwargs):
    """Registra intentos fallidos de inicio de sesión"""
    email = credentials.get('username', credentials.get('email', 'desconocido'))

    AuditoriaAcceso.objects.create(
        usuario=None,
        email=email,
        tipo_accion=TipoAccion.LOGIN_FALLIDO,
        ip_address=obtener_ip_cliente(request) if request else None,
        user_agent=obtener_user_agent(request) if request else '',
        exitoso=False,
        detalles=f"Intento de login fallido para {email}"
    )


@receiver(pre_save, sender=Usuario)
@receiver(pre_save, sender=Persona)
def pre_save_auditoria_data(sender, instance, **kwargs):
    """
    Captura los valores de la instancia antes de que sea modificada.
    Se usa un Thread-Local Storage para que sea seguro en entornos multi-hilo.
    """
    if instance.pk: # Solo para instancias existentes (modificaciones)
        try:
            # Obtener el estado original de la instancia desde la base de datos
            original_instance = sender.objects.get(pk=instance.pk)
            _original_instance_data.values = obtener_valores_modelo(original_instance)
        except sender.DoesNotExist:
            _original_instance_data.values = None
    else: # Para nuevas instancias (creación), no hay valores anteriores
        _original_instance_data.values = None


@receiver(post_save, sender=Usuario)
@receiver(post_save, sender=Persona)
def post_save_auditoria_data(sender, instance, created, **kwargs):
    """
    Registra la creación o modificación de una instancia.
    """
    valores_nuevos = obtener_valores_modelo(instance)
    valores_anteriores = getattr(_original_instance_data, 'values', None)

    # Limpiar el Thread-Local Storage después de usarlo
    if hasattr(_original_instance_data, 'values'):
        del _original_instance_data.values

    if created:
        registrar_cambio(
            instance,
            TipoAccionDatos.CREAR,
            valores_nuevos=valores_nuevos,
            detalles=f"Creado vía señal post_save para {sender.__name__}"
        )
    elif valores_anteriores and valores_anteriores != valores_nuevos:
        registrar_cambio(
            instance,
            TipoAccionDatos.MODIFICAR,
            valores_anteriores=valores_anteriores,
            valores_nuevos=valores_nuevos,
            detalles=f"Modificado vía señal post_save para {sender.__name__}"
        )


@receiver(post_delete, sender=Usuario)
@receiver(post_delete, sender=Persona)
def post_delete_auditoria_data(sender, instance, **kwargs):
    """
    Registra la eliminación de una instancia.
    """
    valores_anteriores = obtener_valores_modelo(instance)
    registrar_cambio(
        instance,
        TipoAccionDatos.ELIMINAR,
        valores_anteriores=valores_anteriores,
        detalles=f"Eliminado vía señal post_delete para {sender.__name__}"
    )

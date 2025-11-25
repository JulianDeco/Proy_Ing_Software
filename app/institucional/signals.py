from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver
from django.utils import timezone
from institucional.models import AuditoriaAcceso, TipoAccion


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

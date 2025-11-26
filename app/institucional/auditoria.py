"""
Utilidades para auditoría de cambios de datos.
Proporciona funciones y mixins para registrar automáticamente los cambios en modelos.
"""
import threading
from decimal import Decimal
from datetime import date, datetime
from django.db.models.fields.files import FieldFile

# Thread-local storage para el usuario actual
_thread_locals = threading.local()


def set_current_user(user):
    """Establece el usuario actual en el thread local"""
    _thread_locals.user = user


def get_current_user():
    """Obtiene el usuario actual del thread local"""
    return getattr(_thread_locals, 'user', None)


def set_current_ip(ip):
    """Establece la IP actual en el thread local"""
    _thread_locals.ip = ip


def get_current_ip():
    """Obtiene la IP actual del thread local"""
    return getattr(_thread_locals, 'ip', None)


def serializar_valor(valor):
    """Convierte un valor a formato serializable para JSON"""
    if valor is None:
        return None
    if isinstance(valor, (str, int, float, bool)):
        return valor
    if isinstance(valor, Decimal):
        return float(valor)
    if isinstance(valor, (date, datetime)):
        return valor.isoformat()
    if isinstance(valor, FieldFile):
        return valor.name if valor else None
    if hasattr(valor, 'pk'):
        return str(valor.pk)
    return str(valor)


def obtener_valores_modelo(instance, campos_excluidos=None):
    """
    Obtiene un diccionario con los valores actuales del modelo.

    Args:
        instance: Instancia del modelo
        campos_excluidos: Lista de campos a excluir (ej: ['password', 'last_login'])

    Returns:
        dict: Diccionario con los valores serializables
    """
    if campos_excluidos is None:
        campos_excluidos = []

    # Campos sensibles que nunca se deben auditar
    campos_sensibles = ['password', 'last_login', 'session_key']
    campos_excluidos = list(set(campos_excluidos + campos_sensibles))

    valores = {}
    for field in instance._meta.fields:
        if field.name not in campos_excluidos:
            valor = getattr(instance, field.name, None)
            valores[field.name] = serializar_valor(valor)

    return valores


def registrar_cambio(instance, tipo_accion, valores_anteriores=None, valores_nuevos=None, detalles=None):
    """
    Registra un cambio en la auditoría de datos.

    Args:
        instance: Instancia del modelo que cambió
        tipo_accion: Tipo de acción (CREAR, MODIFICAR, ELIMINAR)
        valores_anteriores: Diccionario con valores antes del cambio
        valores_nuevos: Diccionario con valores después del cambio
        detalles: Texto adicional con detalles del cambio
    """
    from institucional.models import AuditoriaDatos, TipoAccionDatos

    # No auditar los propios registros de auditoría
    if instance._meta.model_name in ['auditoriadatos', 'auditoriaacceso']:
        return

    usuario = get_current_user()
    ip = get_current_ip()

    AuditoriaDatos.objects.create(
        usuario=usuario,
        tipo_accion=tipo_accion,
        modelo=f"{instance._meta.app_label}.{instance._meta.model_name}",
        objeto_id=str(instance.pk) if instance.pk else "N/A",
        objeto_repr=str(instance)[:255],
        valores_anteriores=valores_anteriores,
        valores_nuevos=valores_nuevos,
        ip_address=ip,
        detalles=detalles
    )


class AuditoriaMiddleware:
    """
    Middleware para capturar el usuario y la IP de cada request.
    Esto permite que las señales de auditoría sepan quién hizo el cambio.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Establecer usuario e IP en thread local
        if hasattr(request, 'user') and request.user.is_authenticated:
            set_current_user(request.user)
        else:
            set_current_user(None)

        # Obtener IP
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        set_current_ip(ip)

        response = self.get_response(request)

        # Limpiar thread local después del request
        set_current_user(None)
        set_current_ip(None)

        return response


class AuditoriaMixin:
    """
    Mixin para ModelAdmin que automáticamente audita cambios.
    Usar en lugar de admin.ModelAdmin para modelos que necesitan auditoría.
    """

    # Campos a excluir de la auditoría (sobrescribir en subclases si es necesario)
    campos_auditoria_excluidos = []

    def save_model(self, request, obj, form, change):
        """Guarda el modelo y registra el cambio"""
        from institucional.models import TipoAccionDatos

        if change:
            # Modificación: obtener valores anteriores
            try:
                obj_anterior = obj.__class__.objects.get(pk=obj.pk)
                valores_anteriores = obtener_valores_modelo(obj_anterior, self.campos_auditoria_excluidos)
            except obj.__class__.DoesNotExist:
                valores_anteriores = None

            super().save_model(request, obj, form, change)

            valores_nuevos = obtener_valores_modelo(obj, self.campos_auditoria_excluidos)

            # Solo registrar si hubo cambios reales
            if valores_anteriores != valores_nuevos:
                registrar_cambio(
                    obj,
                    TipoAccionDatos.MODIFICAR,
                    valores_anteriores=valores_anteriores,
                    valores_nuevos=valores_nuevos,
                    detalles=f"Modificado por {request.user.email} desde el admin"
                )
        else:
            # Creación
            super().save_model(request, obj, form, change)

            valores_nuevos = obtener_valores_modelo(obj, self.campos_auditoria_excluidos)
            registrar_cambio(
                obj,
                TipoAccionDatos.CREAR,
                valores_nuevos=valores_nuevos,
                detalles=f"Creado por {request.user.email} desde el admin"
            )

    def delete_model(self, request, obj):
        """Elimina el modelo y registra el cambio"""
        from institucional.models import TipoAccionDatos

        valores_anteriores = obtener_valores_modelo(obj, self.campos_auditoria_excluidos)

        registrar_cambio(
            obj,
            TipoAccionDatos.ELIMINAR,
            valores_anteriores=valores_anteriores,
            detalles=f"Eliminado por {request.user.email} desde el admin"
        )

        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        """Elimina múltiples objetos y registra cada eliminación"""
        from institucional.models import TipoAccionDatos

        for obj in queryset:
            valores_anteriores = obtener_valores_modelo(obj, self.campos_auditoria_excluidos)
            registrar_cambio(
                obj,
                TipoAccionDatos.ELIMINAR,
                valores_anteriores=valores_anteriores,
                detalles=f"Eliminado por {request.user.email} desde el admin (eliminación masiva)"
            )

        super().delete_queryset(request, queryset)

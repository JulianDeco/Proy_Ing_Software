from django.http import HttpResponse
from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.utils.html import format_html
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from institucional.models import Institucion, Usuario, Persona, Empleado, AuditoriaAcceso, AuditoriaDatos, PreguntaFrecuente
from institucional.auditoria import AuditoriaMixin

@admin.register(Institucion)
class InstitucionAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'direccion','nro_telefono','email_contacto')

@admin.register(PreguntaFrecuente)
class PreguntaFrecuenteAdmin(admin.ModelAdmin):
    list_display = ('pregunta', 'orden', 'publicada')
    list_editable = ('orden', 'publicada')
    search_fields = ('pregunta', 'respuesta')

@admin.register(Usuario)
class UsuarioAdmin(BaseUserAdmin):
    list_display = ('email','empleado', 'habilitado', 'is_staff', 'is_superuser')
    search_fields = ('email',)
    ordering = ('email',)
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Permisos', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'habilitado', 'groups', 'is_staff', 'is_superuser'),
        }),
    )

@admin.register(Empleado)
class EmpleadoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'apellido', 'dni', 'usuario_asociado')
    search_fields = ('nombre', 'apellido', 'dni', 'usuario__email')

    def usuario_asociado(self, obj):
        return obj.usuario.email if obj.usuario else '—'
    usuario_asociado.short_description = 'Usuario'


@admin.register(AuditoriaAcceso)
class AuditoriaAccesoAdmin(admin.ModelAdmin):
    list_display = ('fecha_hora', 'email', 'tipo_accion', 'exitoso', 'ip_address', 'usuario_display')
    list_filter = ('tipo_accion', 'exitoso', 'fecha_hora')
    search_fields = ('email', 'ip_address', 'detalles')
    readonly_fields = ('usuario', 'email', 'tipo_accion', 'fecha_hora', 'ip_address', 'user_agent', 'exitoso', 'detalles')
    date_hierarchy = 'fecha_hora'
    ordering = ('-fecha_hora',)

    def usuario_display(self, obj):
        if obj.usuario:
            return format_html('<span style="color: green;">✓</span> {}', obj.usuario.email)
        return format_html('<span style="color: red;">✗</span> Usuario no encontrado')
    usuario_display.short_description = 'Usuario'

    def has_add_permission(self, request):
        # No permitir agregar registros manualmente
        return False

    def has_delete_permission(self, request, obj=None):
        # No permitir eliminar registros (solo lectura)
        return False

    def has_change_permission(self, request, obj=None):
        # No permitir modificar registros (solo lectura)
        return False


@admin.register(AuditoriaDatos)
class AuditoriaDatosAdmin(admin.ModelAdmin):
    list_display = ('fecha_hora', 'usuario_display', 'tipo_accion', 'modelo', 'objeto_repr', 'cambios_cortos')
    list_filter = ('tipo_accion', 'modelo', 'fecha_hora')
    search_fields = ('modelo', 'objeto_repr', 'detalles', 'usuario__email')
    readonly_fields = (
        'usuario', 'tipo_accion', 'fecha_hora', 'modelo', 'objeto_id',
        'objeto_repr', 'valores_anteriores', 'valores_nuevos', 'ip_address', 'detalles'
    )
    date_hierarchy = 'fecha_hora'
    ordering = ('-fecha_hora',)

    fieldsets = (
        ('Información General', {
            'fields': ('fecha_hora', 'usuario', 'tipo_accion', 'ip_address')
        }),
        ('Objeto Afectado', {
            'fields': ('modelo', 'objeto_id', 'objeto_repr')
        }),
        ('Cambios Realizados', {
            'fields': ('valores_anteriores', 'valores_nuevos', 'detalles'),
            'classes': ('collapse',)
        }),
    )

    def usuario_display(self, obj):
        if obj.usuario:
            return obj.usuario.email
        return '(Sistema/Anónimo)'
    usuario_display.short_description = 'Usuario'

    def cambios_cortos(self, obj):
        resumen = obj.cambios_resumidos
        if len(resumen) > 80:
            return resumen[:80] + '...'
        return resumen
    cambios_cortos.short_description = 'Cambios'

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False
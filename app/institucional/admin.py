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
    search_fields = ('nombre', 'direccion', 'email_contacto')

@admin.register(PreguntaFrecuente)
class PreguntaFrecuenteAdmin(admin.ModelAdmin):
    list_display = ('pregunta', 'orden', 'publicada_display')
    list_editable = ('orden',)
    search_fields = ('pregunta', 'respuesta')
    list_filter = ('publicada',)
    list_per_page = 25
    save_on_top = True

    def publicada_display(self, obj):
        if obj.publicada:
            return format_html('<span style="color: green; font-size: 16px;">✓</span> Publicada')
        return format_html('<span style="color: gray; font-size: 16px;">✗</span> No publicada')
    publicada_display.short_description = 'Estado'

@admin.register(Usuario)
class UsuarioAdmin(BaseUserAdmin):
    list_display = ('email', 'empleado', 'habilitado_display', 'is_staff_display', 'is_superuser_display')
    search_fields = ('email', 'empleado__nombre', 'empleado__apellido', 'empleado__dni')
    list_filter = ('is_staff', 'is_superuser', 'habilitado')
    ordering = ('email',)
    list_per_page = 50
    save_on_top = True
    empty_value_display = '—'

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

    def habilitado_display(self, obj):
        if obj.habilitado:
            return format_html('<span style="color: green; font-size: 16px;">✓</span>')
        return format_html('<span style="color: red; font-size: 16px;">✗</span>')
    habilitado_display.short_description = 'Habilitado'

    def is_staff_display(self, obj):
        if obj.is_staff:
            return format_html('<span style="color: green; font-size: 16px;">✓</span>')
        return format_html('<span style="color: red; font-size: 16px;">✗</span>')
    is_staff_display.short_description = 'Staff'

    def is_superuser_display(self, obj):
        if obj.is_superuser:
            return format_html('<span style="color: green; font-size: 16px;">✓</span>')
        return format_html('<span style="color: red; font-size: 16px;">✗</span>')
    is_superuser_display.short_description = 'Superusuario'

@admin.register(Persona)
class PersonaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'apellido', 'dni')
    list_display_links = ('nombre', 'apellido')
    search_fields = ('nombre', 'apellido', 'dni')
    list_per_page = 50
    save_on_top = True

@admin.register(Empleado)
class EmpleadoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'apellido', 'dni', 'usuario_asociado')
    list_display_links = ('nombre', 'apellido')
    search_fields = ('nombre', 'apellido', 'dni', 'usuario__email')
    autocomplete_fields = ['usuario']
    list_select_related = ('usuario',)
    list_per_page = 50
    save_on_top = True
    empty_value_display = '—'

    fieldsets = (
        ('Datos Personales', {
            'fields': ('nombre', 'apellido', 'dni')
        }),
        ('Usuario Asociado', {
            'fields': ('usuario',)
        }),
    )

    def usuario_asociado(self, obj):
        return obj.usuario.email if obj.usuario else '—'
    usuario_asociado.short_description = 'Usuario'


@admin.register(AuditoriaAcceso)
class AuditoriaAccesoAdmin(admin.ModelAdmin):
    list_display = ('fecha_hora', 'email', 'tipo_accion', 'exitoso_display', 'ip_address', 'usuario_display')
    list_filter = ('tipo_accion', 'exitoso', 'fecha_hora')
    search_fields = ('email', 'ip_address', 'detalles')
    readonly_fields = ('usuario', 'email', 'tipo_accion', 'fecha_hora', 'ip_address', 'user_agent', 'exitoso', 'detalles')
    date_hierarchy = 'fecha_hora'
    ordering = ('-fecha_hora',)
    list_select_related = ('usuario',)
    list_per_page = 100
    empty_value_display = '—'

    def exitoso_display(self, obj):
        if obj.exitoso:
            return format_html('<span style="color: green; font-size: 16px;">✓</span> Exitoso')
        return format_html('<span style="color: red; font-size: 16px;">✗</span> Fallido')
    exitoso_display.short_description = 'Resultado'

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
    list_display = ('fecha_hora', 'usuario_display', 'tipo_accion_display', 'modelo', 'objeto_repr', 'cambios_cortos')
    list_filter = ('tipo_accion', 'modelo', 'fecha_hora')
    search_fields = ('modelo', 'objeto_repr', 'detalles', 'usuario__email')
    readonly_fields = (
        'usuario', 'tipo_accion', 'fecha_hora', 'modelo', 'objeto_id',
        'objeto_repr', 'valores_anteriores', 'valores_nuevos', 'ip_address', 'detalles'
    )
    date_hierarchy = 'fecha_hora'
    ordering = ('-fecha_hora',)
    list_select_related = ('usuario',)
    list_per_page = 100
    empty_value_display = '—'

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

    def tipo_accion_display(self, obj):
        colors = {
            'CREATE': '#28a745',
            'UPDATE': '#ffc107',
            'DELETE': '#dc3545'
        }
        color = colors.get(obj.tipo_accion, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            color, obj.get_tipo_accion_display()
        )
    tipo_accion_display.short_description = 'Acción'

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
from django.http import HttpResponse
from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.utils.html import format_html
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from institucional.models import Institucion, Usuario, Persona, Empleado, AuditoriaAcceso

@admin.register(Institucion)
class InstitucionAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'direccion','nro_telefono','nro_celular','logo')

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
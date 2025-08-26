from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from institucional.models import Usuario, Persona, Empleado
from academico.models import Alumno

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


@admin.register(Alumno)
class AlumnoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'apellido', 'dni', 'promedio', 'estado')
    search_fields = ('nombre', 'apellido', 'dni')

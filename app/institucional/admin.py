from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from institucional.models import Persona, Rol, Usuario

@admin.register(Usuario)
class UsuarioAdmin(BaseUserAdmin):
    list_display = ('username', 'persona', 'habilitado', 'is_staff', 'is_superuser')
    search_fields = ('username', 'persona__nombre', 'persona__apellido')

@admin.register(Persona)
class PersonaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'apellido', 'dni')
    search_fields = ('nombre', 'apellido', 'dni')

@admin.register(Rol)
class RolAdmin(admin.ModelAdmin):
    list_display = ('nombre',)
    search_fields = ('nombre',)
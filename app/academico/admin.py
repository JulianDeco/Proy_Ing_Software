from django.contrib import admin

from academico.models import Comision, Materia

@admin.register(Materia)
class MateriaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'codigo', 'plan_estudio')
    search_fields = ('nombre', 'codigo', 'plan_estudio__nombre')

@admin.register(Comision)
class ComisionAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'materia', 'horario_inicio', 'horario_fin', 'turno')
    search_fields = ('codigo', 'materia__nombre')

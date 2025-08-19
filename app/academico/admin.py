from django.contrib import admin

from academico.models import Comision, EstadosAlumno, Materia, InscripcionesAlumnosComisiones

@admin.register(Materia)
class MateriaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'codigo', 'plan_estudio')
    search_fields = ('nombre', 'codigo', 'plan_estudio__nombre')

@admin.register(Comision)
class ComisionAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'materia', 'horario_inicio', 'horario_fin', 'turno')
    search_fields = ('codigo', 'materia__nombre')
    
@admin.register(EstadosAlumno)
class EstadosAlumnoAdmin(admin.ModelAdmin):
    list_display = ('descripcion',)
    search_fields = ('descripcion',)
    
@admin.register(InscripcionesAlumnosComisiones)
class InscripcionesAlumnosComisionesAdmin(admin.ModelAdmin):
    list_display = ('alumno','comision',)
    search_fields = ('alumno','comision','creado',)

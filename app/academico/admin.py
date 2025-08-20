from django.contrib import admin

from academico.models import Asistencia, Calificacion, Comision, EstadosAlumno, Materia, InscripcionesAlumnosComisiones

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

@admin.register(Calificacion)
class CalificacionAdmin(admin.ModelAdmin):
    list_display = ('alumno_comision', 'tipo' ,'nota',)
    search_fields = ('alumno_comision', 'tipo' ,'nota',)

@admin.register(Asistencia)
class CalificacionAdmin(admin.ModelAdmin):
    list_display = ('alumno_comision', 'es_presente' ,'fecha_asistencia',)
    search_fields = ('alumno_comision', 'es_presente' ,'fecha_asistencia',)
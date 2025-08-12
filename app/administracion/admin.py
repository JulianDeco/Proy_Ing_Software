# admin.py
from django.contrib import admin
from .models import (
    TipoCalificacion, TipoEstado, Persona, Administrativo, Docente,
    Correlativa, Materia, PlanEstudio, Comision, Alumno, Inscripcion,
    Calificacion, Asistencia
)

@admin.register(TipoCalificacion)
class TipoCalificacionAdmin(admin.ModelAdmin):
    list_display = ('descripcion',)
    search_fields = ('descripcion',)

@admin.register(TipoEstado)
class TipoEstadoAdmin(admin.ModelAdmin):
    list_display = ('descripcion',)
    search_fields = ('descripcion',)

@admin.register(Persona)
class PersonaAdmin(admin.ModelAdmin):
    list_display = ('dni', 'nombre', 'apellido')
    search_fields = ('dni', 'nombre', 'apellido')

@admin.register(Administrativo)
class AdministrativoAdmin(admin.ModelAdmin):
    list_display = ('persona', 'area')
    search_fields = ('persona__dni', 'persona__nombre', 'persona__apellido', 'area')
    
@admin.register(Docente)
class DocenteAdmin(admin.ModelAdmin):
    list_display = ('persona', 'legajo')
    search_fields = ('persona__dni', 'persona__nombre', 'persona__apellido', 'legajo')

@admin.register(Correlativa)
class CorrelativaAdmin(admin.ModelAdmin):
    list_display = ('nombre',)
    search_fields = ('nombre',)

@admin.register(Materia)
class MateriaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'codigo', 'cupo_maximo', 'profesor')
    search_fields = ('nombre', 'codigo', 'profesor__persona__nombre', 'profesor__persona__apellido')
    filter_horizontal = ('correlativas',)

@admin.register(PlanEstudio)
class PlanEstudioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'codigo')
    search_fields = ('nombre', 'codigo')
    filter_horizontal = ('materias',)

@admin.register(Comision)
class ComisionAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'horario_completo', 'turno', 'materia')
    search_fields = ('codigo', 'turno', 'materia__nombre')

    def horario_completo(self, obj):
        return f"{obj.horario_inicio.strftime('%H:%M')} - {obj.horario_fin.strftime('%H:%M')}"
    horario_completo.short_description = 'Horario'

@admin.register(Alumno)
class AlumnoAdmin(admin.ModelAdmin):
    list_display = ('persona', 'estado')
    search_fields = ('persona__dni', 'persona__nombre', 'persona__apellido', 'estado__descripcion')

@admin.register(Inscripcion)
class InscripcionAdmin(admin.ModelAdmin):
    list_display = ('alumno', 'comision', 'fecha', 'estado')
    search_fields = ('alumno__persona__nombre', 'alumno__persona__apellido', 'comision__codigo', 'estado')
    list_filter = ('estado',)

@admin.register(Calificacion)
class CalificacionAdmin(admin.ModelAdmin):
    list_display = ('alumno', 'comision', 'fecha', 'nota', 'tipo')
    search_fields = ('alumno__persona__nombre', 'alumno__persona__apellido', 'comision__codigo', 'tipo__descripcion')
    list_filter = ('tipo',)

@admin.register(Asistencia)
class AsistenciaAdmin(admin.ModelAdmin):
    list_display = ('alumno', 'comision', 'fecha', 'presente')
    search_fields = ('alumno__persona__nombre', 'alumno__persona__apellido', 'comision__codigo')
    list_filter = ('presente',)

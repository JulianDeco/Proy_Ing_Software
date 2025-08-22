from django.contrib import admin

from academico.models import AnioAcademico, Asistencia, CalendarioAcademico, Calificacion, Comision, EstadosAlumno, Materia, InscripcionesAlumnosComisiones

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
class AsistenciaAdmin(admin.ModelAdmin):
    list_display = ('alumno_comision', 'esta_presente', 'fecha_asistencia',)
    list_filter = ('esta_presente', 'fecha_asistencia', 'alumno_comision__comision',)
    search_fields = (
        'alumno_comision__alumno__nombre',
        'alumno_comision__alumno__apellido', 
        'alumno_comision__alumno__dni',
        'alumno_comision__comision__codigo'
    )
    date_hierarchy = 'fecha_asistencia'
    

@admin.register(AnioAcademico)
class AnioAcademicoAdmin(admin.ModelAdmin):
    list_display =('nombre','fecha_inicio', 'fecha_fin' ,'activo') 
    search_fields = ('nombre','fecha_inicio', 'fecha_fin' ,'activo') 

@admin.register(CalendarioAcademico)
class CalendarioAcademico(admin.ModelAdmin):
    list_display = ('anio_academico','fecha','es_dia_clase','descripcion',)
    search_fields= ('anio_academico','fecha','es_dia_clase','descripcion',)
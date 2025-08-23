from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import CalendarioAcademico, Comision, InscripcionesAlumnosComisiones, Asistencia, Alumno
from institucional.models import Empleado

class ServiciosAcademico:
    @staticmethod
    def obtener_docente_actual(usuario):
        return get_object_or_404(Empleado, usuario=usuario)
    
    @staticmethod
    def obtener_comisiones_docente(docente):
        return Comision.objects.filter(docente=docente)
    
    @staticmethod
    def obtener_comision_por_codigo(codigo):
        return get_object_or_404(Comision, codigo=codigo)
    
    @staticmethod
    def obtener_alumnos_comision(comision):
        return InscripcionesAlumnosComisiones.objects.filter(comision=comision)
    
    @staticmethod
    def contar_inscriptos_comision(comision):
        return InscripcionesAlumnosComisiones.objects.filter(comision=comision).count()
    
    @staticmethod
    def obtener_fechas_clases(comision):
        fechas_clase = CalendarioAcademico.objects.filter(
        anio_academico=comision.anio_academico,
        fecha__week_day=comision.dia_cursado + 1,
        es_dia_clase=True,
        fecha__lte=timezone.now().date()
        ).order_by('-fecha')
        fecha_seleccionada = fechas_clase.first().fecha if fechas_clase.exists() else None
        return fechas_clase, fecha_seleccionada

    @staticmethod
    def obtener_asistencia_alumno_hoy(alumno_comision, fecha_seleccionada):
        try:
            return Asistencia.objects.get(
                alumno_comision=alumno_comision,
                fecha_asistencia=fecha_seleccionada
            )
        except Asistencia.DoesNotExist:
            return None
    
    @staticmethod
    def registrar_asistencia(alumno, comision, esta_presente, fecha_asistencia):
        inscripcion = get_object_or_404(
            InscripcionesAlumnosComisiones,
            alumno=alumno,
            comision=comision
        )
        
        asistencia = Asistencia.objects.get(
                alumno_comision=inscripcion,
                fecha_asistencia=fecha_asistencia
            )
        asistencia.esta_presente = esta_presente
        asistencia.save()
        
        return asistencia, fecha_asistencia
    
    @staticmethod
    def obtener_estadisticas_docente(docente):
        comisiones = Comision.objects.filter(docente=docente)
        clases_hoy = comisiones.filter(dia_cursado=timezone.now().weekday() + 1).count()
        
        total_alumnos = 0
        for comision in comisiones:
            total_alumnos += InscripcionesAlumnosComisiones.objects.filter(comision=comision).count()
        
        return {
            'total_comisiones': comisiones.count(),
            'clases_hoy': clases_hoy,
            'total_alumnos': total_alumnos
        }
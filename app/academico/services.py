from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import Comision, InscripcionesAlumnosComisiones, Asistencia, Alumno
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
    def obtener_asistencia_alumno_hoy(alumno_comision):
        fecha_actual = timezone.now().date()
        try:
            return Asistencia.objects.get(
                alumno_comision=alumno_comision,
                fecha_asistencia=fecha_actual
            )
        except Asistencia.DoesNotExist:
            return None
    
    @staticmethod
    def registrar_asistencia(alumno, comision, esta_presente):
        fecha_actual = timezone.now().date()

        inscripcion = get_object_or_404(
            InscripcionesAlumnosComisiones,
            alumno=alumno,
            comision=comision
        )
        
        asistencia = Asistencia.objects.get(
                alumno_comision=inscripcion,
                fecha_asistencia=fecha_actual
            )
        asistencia.esta_presente = esta_presente
        asistencia.save()
        
        return asistencia, fecha_actual
    
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
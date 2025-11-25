from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import CalendarioAcademico, Calificacion, Comision, InscripcionAlumnoComision, Asistencia, Alumno, TipoCalificacion
from institucional.models import Empleado
from .exceptions import (
    TipoCalificacionInvalidoError,
    RangoCalificacionInvalidoError,
    AsistenciaNoExisteError,
    FechaNoClaseError
)

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
        return InscripcionAlumnoComision.objects.filter(comision=comision)
    
    @staticmethod
    def contar_inscriptos_comision(comision):
        return InscripcionAlumnoComision.objects.filter(comision=comision).count()
    
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
            raise AsistenciaNoExisteError(
                f"No existe registro de asistencia para el alumno en la fecha {fecha_seleccionada}"
            )
    
    @staticmethod
    def obtener_porcentaje_asistencia(alumno_comision, fecha_seleccionada):
        asistencias = Asistencia.objects.filter(
                alumno_comision=alumno_comision, 
                fecha_asistencia__lt=fecha_seleccionada
                )
        total_asistencias = asistencias.count()
        presentes = 0
        for asistencia in asistencias:
            if asistencia.esta_presente == True:
                presentes += 1
        return round(presentes * 100 / total_asistencias, 2)
    
    @staticmethod
    def registrar_asistencia(alumno, comision, esta_presente, fecha_asistencia):
        # Verificar que la fecha sea un día de clase
        try:
            dia_calendario = CalendarioAcademico.objects.get(
                anio_academico=comision.anio_academico,
                fecha=fecha_asistencia
            )
            if not dia_calendario.es_dia_clase:
                raise FechaNoClaseError(
                    f"La fecha {fecha_asistencia} no es un día de clase. Motivo: {dia_calendario.descripcion}"
                )
        except CalendarioAcademico.DoesNotExist:
            raise FechaNoClaseError(
                f"La fecha {fecha_asistencia} no existe en el calendario académico"
            )

        inscripcion = get_object_or_404(
            InscripcionAlumnoComision,
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
    def crear_calificacion(alumno, fecha, tipo_calificacion, calificacion):
        valores_calificacion = [choice[0] for choice in TipoCalificacion.choices]

        if tipo_calificacion not in valores_calificacion:
            raise TipoCalificacionInvalidoError(
                f"El tipo de calificación '{tipo_calificacion}' no es válido. "
                f"Valores permitidos: {', '.join(valores_calificacion)}"
            )

        # Validar rango de calificación (0-10)
        if calificacion < 0 or calificacion > 10:
            raise RangoCalificacionInvalidoError(
                f"La calificación debe estar entre 0 y 10. Valor recibido: {calificacion}"
            )

        calificacion_nuevo = Calificacion.objects.create(
            alumno_comision= alumno,
            tipo =  tipo_calificacion,
            nota = calificacion,
            fecha_creacion= fecha
        )
        return calificacion_nuevo
    
    @staticmethod
    def obtener_estadisticas_docente(docente):
        comisiones = Comision.objects.filter(docente=docente)
        clases_hoy = comisiones.filter(dia_cursado=timezone.now().weekday() + 1).count()
        
        total_alumnos = 0
        for comision in comisiones:
            total_alumnos += InscripcionAlumnoComision.objects.filter(comision=comision).count()
        
        return {
            'total_comisiones': comisiones.count(),
            'clases_hoy': clases_hoy,
            'total_alumnos': total_alumnos
        }
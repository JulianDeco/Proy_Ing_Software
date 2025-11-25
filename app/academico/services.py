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
        from django.db import IntegrityError

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

        # Verificar si ya existe una calificación del mismo tipo
        calificacion_existente = Calificacion.objects.filter(
            alumno_comision=alumno,
            tipo=tipo_calificacion
        ).first()

        if calificacion_existente:
            # Actualizar la calificación existente en lugar de crear una nueva
            calificacion_existente.nota = calificacion
            calificacion_existente.fecha_creacion = fecha
            calificacion_existente.save()
            return calificacion_existente

        try:
            calificacion_nuevo = Calificacion.objects.create(
                alumno_comision= alumno,
                tipo =  tipo_calificacion,
                nota = calificacion,
                fecha_creacion= fecha
            )
            return calificacion_nuevo
        except IntegrityError:
            # Si por alguna razón se intenta crear duplicado, obtenemos y actualizamos
            calificacion_existente = Calificacion.objects.get(
                alumno_comision=alumno,
                tipo=tipo_calificacion
            )
            calificacion_existente.nota = calificacion
            calificacion_existente.fecha_creacion = fecha
            calificacion_existente.save()
            return calificacion_existente
    
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

    @staticmethod
    def calcular_nota_final(inscripcion):
        """
        Calcula la nota final de un alumno en una comisión.

        Lógica:
        1. Si tiene nota FINAL: usa esa nota
        2. Si NO tiene FINAL pero tiene otras calificaciones: promedio de todas
        3. Si NO tiene calificaciones: retorna None

        Args:
            inscripcion: InscripcionAlumnoComision

        Returns:
            Decimal o None
        """
        from academico.models import Calificacion, TipoCalificacion
        from django.db.models import Avg

        # Buscar si tiene calificación FINAL
        calificacion_final = Calificacion.objects.filter(
            alumno_comision=inscripcion,
            tipo=TipoCalificacion.FINAL
        ).first()

        if calificacion_final:
            return calificacion_final.nota

        # Si no tiene FINAL, calcular promedio de todas las calificaciones
        calificaciones = Calificacion.objects.filter(alumno_comision=inscripcion)

        if calificaciones.exists():
            promedio = calificaciones.aggregate(Avg('nota'))['nota__avg']
            return round(promedio, 2) if promedio else None

        return None

    @staticmethod
    def cerrar_inscripcion(inscripcion, usuario):
        """
        Cierra una inscripción individual calculando la nota final y actualizando el estado.

        Args:
            inscripcion: InscripcionAlumnoComision
            usuario: User que realiza el cierre

        Returns:
            tuple: (success: bool, mensaje: str)
        """
        from django.utils import timezone

        # Calcular nota final
        nota_final = ServiciosAcademico.calcular_nota_final(inscripcion)

        if nota_final is None:
            return False, f"El alumno {inscripcion.alumno} no tiene calificaciones registradas."

        # Determinar estado según nota
        if nota_final >= 6:
            nuevo_estado = 'APROBADA'
        else:
            nuevo_estado = 'DESAPROBADA'

        # Actualizar inscripción
        inscripcion.nota_final = nota_final
        inscripcion.estado_inscripcion = nuevo_estado
        inscripcion.fecha_cierre = timezone.now()
        inscripcion.cerrada_por = usuario
        inscripcion.save()

        return True, f"Inscripción cerrada. Nota final: {nota_final} - Estado: {nuevo_estado}"

    @staticmethod
    def cerrar_comision(comision, usuario):
        """
        Cierra una comisión completa procesando todas las inscripciones.

        Args:
            comision: Comision
            usuario: User que realiza el cierre

        Returns:
            dict: {
                'success': bool,
                'mensaje': str,
                'procesadas': int,
                'aprobadas': int,
                'desaprobadas': int,
                'sin_calificaciones': int
            }
        """
        from academico.models import InscripcionAlumnoComision, EstadoComision
        from django.db import transaction

        inscripciones = InscripcionAlumnoComision.objects.filter(
            comision=comision,
            estado_inscripcion='REGULAR'  # Solo procesar las que están en curso
        )

        if not inscripciones.exists():
            return {
                'success': False,
                'mensaje': 'No hay inscripciones en estado REGULAR para cerrar.',
                'procesadas': 0,
                'aprobadas': 0,
                'desaprobadas': 0,
                'sin_calificaciones': 0
            }

        procesadas = 0
        aprobadas = 0
        desaprobadas = 0
        sin_calificaciones = 0

        with transaction.atomic():
            for inscripcion in inscripciones:
                success, mensaje = ServiciosAcademico.cerrar_inscripcion(inscripcion, usuario)

                if success:
                    procesadas += 1
                    if inscripcion.estado_inscripcion == 'APROBADA':
                        aprobadas += 1
                    elif inscripcion.estado_inscripcion == 'DESAPROBADA':
                        desaprobadas += 1
                else:
                    sin_calificaciones += 1

            # Actualizar estado de la comisión
            comision.estado = EstadoComision.FINALIZADA
            comision.save()

        mensaje = (
            f"Comisión cerrada exitosamente.\n"
            f"Procesadas: {procesadas} | Aprobadas: {aprobadas} | "
            f"Desaprobadas: {desaprobadas} | Sin calificaciones: {sin_calificaciones}"
        )

        return {
            'success': True,
            'mensaje': mensaje,
            'procesadas': procesadas,
            'aprobadas': aprobadas,
            'desaprobadas': desaprobadas,
            'sin_calificaciones': sin_calificaciones
        }
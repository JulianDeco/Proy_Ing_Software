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
    def calcular_promedio_cursada(inscripcion):
        """
        Calcula el promedio de notas de PARCIAL y TP de un alumno en una comisión.
        Ignora la nota FINAL ya que esa es posterior a la cursada.

        Args:
            inscripcion: InscripcionAlumnoComision

        Returns:
            Decimal o None
        """
        from academico.models import Calificacion, TipoCalificacion
        from django.db.models import Avg, Q

        # Calcular promedio solo de PARCIAL y TP
        calificaciones = Calificacion.objects.filter(
            alumno_comision=inscripcion
        ).filter(
            Q(tipo=TipoCalificacion.PARCIAL) | Q(tipo=TipoCalificacion.TRABAJO_PRACTICO)
        )

        if calificaciones.exists():
            promedio = calificaciones.aggregate(Avg('nota'))['nota__avg']
            return round(promedio, 2) if promedio else None

        return None

    @staticmethod
    def regularizar_alumno(inscripcion, usuario, nota_aprobacion, porcentaje_asistencia_req):
        """
        Determina la condición de un alumno (Regular/Libre) al cerrar la cursada.

        Args:
            inscripcion: InscripcionAlumnoComision
            usuario: User que realiza la acción
            nota_aprobacion: Decimal (del AnioAcademico)
            porcentaje_asistencia_req: int (del AnioAcademico)

        Returns:
            tuple: (condicion: str, mensaje: str)
        """
        from django.utils import timezone
        from academico.models import CondicionInscripcion

        # Calcular promedio de cursada
        promedio = ServiciosAcademico.calcular_promedio_cursada(inscripcion)
        
        # Obtener porcentaje de asistencia (asumimos fecha actual como corte)
        porcentaje_asistencia = ServiciosAcademico.obtener_porcentaje_asistencia(
            inscripcion, 
            timezone.now().date()
        )

        if promedio is None:
            condicion = CondicionInscripcion.LIBRE
            mensaje = "Libre por falta de calificaciones."
        else:
            # Lógica de regularización
            cumple_nota = promedio >= nota_aprobacion
            cumple_asistencia = porcentaje_asistencia >= porcentaje_asistencia_req

            if cumple_nota and cumple_asistencia:
                condicion = CondicionInscripcion.REGULAR
                mensaje = f"Regular (Prom: {promedio}, Asist: {porcentaje_asistencia}%)"
            else:
                condicion = CondicionInscripcion.LIBRE
                motivo = []
                if not cumple_nota: motivo.append(f"Nota insuficiente ({promedio})")
                if not cumple_asistencia: motivo.append(f"Faltas ({porcentaje_asistencia}%)")
                mensaje = f"Libre por: {', '.join(motivo)}"

        # Actualizar inscripción
        inscripcion.condicion = condicion
        inscripcion.nota_cursada = promedio
        inscripcion.fecha_regularizacion = timezone.now()
        # Nota: No cambiamos estado_inscripcion a APROBADA/DESAPROBADA aún.
        # Eso sucede en el final.
        inscripcion.save()

        return condicion, mensaje

    @staticmethod
    def regularizar_comision(comision, usuario):
        """
        Cierra la cursada de una comisión completa, asignando la condición (Regular/Libre)
        a cada alumno basándose en las reglas del Año Académico.

        Args:
            comision: Comision
            usuario: User que realiza el cierre

        Returns:
            dict con estadísticas
        """
        from academico.models import InscripcionAlumnoComision, EstadoComision, CondicionInscripcion
        from django.db import transaction

        # Verificar configuración del año académico
        anio = comision.anio_academico
        if not anio.cierre_cursada_habilitado:
            return {
                'success': False,
                'mensaje': 'El cierre de cursada no está habilitado para este Año Académico.',
            }

        inscripciones = InscripcionAlumnoComision.objects.filter(
            comision=comision,
            estado_inscripcion='REGULAR' # Filtramos los que siguen activos
        )

        if not inscripciones.exists():
            return {
                'success': False,
                'mensaje': 'No hay alumnos activos para regularizar.',
            }

        regulares = 0
        libres = 0
        
        with transaction.atomic():
            for inscripcion in inscripciones:
                condicion, _ = ServiciosAcademico.regularizar_alumno(
                    inscripcion, 
                    usuario,
                    anio.nota_aprobacion,
                    anio.porcentaje_asistencia_req
                )

                if condicion == CondicionInscripcion.REGULAR:
                    regulares += 1
                else:
                    libres += 1

            # Actualizar estado de la comisión
            comision.estado = EstadoComision.FINALIZADA
            comision.save()

        mensaje = (
            f"Cursada cerrada exitosamente.\n"
            f"Alumnos Regulares: {regulares} | Alumnos Libres: {libres}"
        )

        return {
            'success': True,
            'mensaje': mensaje,
            'regulares': regulares,
            'libres': libres
        }

    @staticmethod
    def cargar_nota_examen_final(inscripcion_mesa, nota, usuario):
        """
        Carga la nota de un examen final y actualiza el estado definitivo del alumno en la materia.

        Args:
            inscripcion_mesa: InscripcionMesaExamen
            nota: Decimal (nota del examen)
            usuario: User que carga la nota

        Returns:
            tuple: (success: bool, mensaje: str)
        """
        from academico.models import InscripcionAlumnoComision, EstadoMateria
        from django.utils import timezone

        if nota < 0 or nota > 10:
            return False, "La nota debe estar entre 0 y 10."

        # Obtener nota de aprobación del año académico correspondiente a la mesa
        nota_aprobacion = inscripcion_mesa.mesa_examen.anio_academico.nota_aprobacion

        # Actualizar nota en la inscripción a la mesa
        inscripcion_mesa.nota_examen = nota

        # Determinar resultado del examen
        aprobado = nota >= nota_aprobacion
        
        if aprobado:
            inscripcion_mesa.estado_inscripcion = 'APROBADO'
            # Si aprobó el examen, aprueba la materia definitivamente
            nuevo_estado_materia = EstadoMateria.APROBADA
        else:
            inscripcion_mesa.estado_inscripcion = 'DESAPROBADO'
            # Si desaprobó, la materia queda en su estado anterior (ej: REGULAR) o pasa a DESAPROBADA?
            # Generalmente si desaprueba el final, sigue debiendo la materia pero mantiene su regularidad
            # hasta que se venza. Por ahora no tocamos el estado 'REGULAR' de la cursada,
            # salvo que queramos marcar explícitamente que falló un intento.
            # Pero el requerimiento dice: "si la nota examen final es mayor o igual a nota de aprobación que marque al alumno como aprobado"
            # Implica que si no, no lo marca como aprobado.
            nuevo_estado_materia = None 

        inscripcion_mesa.save()

        # Actualizar el estado de la cursada del alumno SOLO si aprobó
        cursada = InscripcionAlumnoComision.objects.filter(
            alumno=inscripcion_mesa.alumno,
            comision__materia=inscripcion_mesa.mesa_examen.materia
        ).first()

        if cursada and aprobado:
            cursada.nota_final = nota
            cursada.estado_inscripcion = nuevo_estado_materia
            cursada.fecha_cierre = timezone.now()
            cursada.cerrada_por = usuario
            cursada.save()

        mensaje = (
            f"Nota cargada: {nota}. "
            f"Resultado: {'APROBADO' if aprobado else 'DESAPROBADO'}"
        )

        return True, mensaje

    @staticmethod
    def finalizar_mesa_examen(mesa, usuario):
        """
        Finaliza una mesa de examen y marca como ausentes a quienes no rindieron.

        Args:
            mesa: MesaExamen
            usuario: User que finaliza

        Returns:
            dict con estadísticas
        """
        from academico.models import InscripcionMesaExamen, EstadoMesaExamen

        inscripciones = InscripcionMesaExamen.objects.filter(
            mesa_examen=mesa,
            estado_inscripcion='INSCRIPTO'  # Solo los que no tienen nota
        )

        ausentes = 0
        for inscripcion in inscripciones:
            inscripcion.estado_inscripcion = 'AUSENTE'
            inscripcion.save()
            ausentes += 1

        # Cambiar estado de la mesa
        mesa.estado = EstadoMesaExamen.FINALIZADA
        mesa.save()

        total_inscriptos = InscripcionMesaExamen.objects.filter(mesa_examen=mesa).count()
        aprobados = InscripcionMesaExamen.objects.filter(
            mesa_examen=mesa,
            estado_inscripcion='APROBADO'
        ).count()
        desaprobados = InscripcionMesaExamen.objects.filter(
            mesa_examen=mesa,
            estado_inscripcion='DESAPROBADO'
        ).count()

        return {
            'success': True,
            'total_inscriptos': total_inscriptos,
            'aprobados': aprobados,
            'desaprobados': desaprobados,
            'ausentes': ausentes
        }

    @staticmethod
    def inscribir_alumno_mesa(alumno, mesa):
        """
        Inscribe un alumno a una mesa de examen validando las reglas de negocio.

        Args:
            alumno: Alumno
            mesa: MesaExamen

        Returns:
            tuple: (success: bool, mensaje: str)
        """
        from academico.models import InscripcionMesaExamen, EstadoMateria, CondicionAlumnoMesa
        from django.core.exceptions import ValidationError

        try:
            # Crear instancia (se ejecutará clean() automáticamente al guardar o manual)
            inscripcion = InscripcionMesaExamen(
                alumno=alumno,
                mesa_examen=mesa
            )
            
            # Ejecutar validaciones de modelo (clean)
            inscripcion.clean()

            # Si pasó validaciones, guardar
            inscripcion.save()
            
            return True, "Inscripción realizada con éxito."

        except ValidationError as e:
            # Extraer mensajes de error
            if hasattr(e, 'message_dict'):
                errores = [v[0] for k, v in e.message_dict.items()]
                return False, " | ".join(errores)
            else:
                return False, str(e.message)
        except Exception as e:
            return False, f"Error inesperado: {str(e)}"
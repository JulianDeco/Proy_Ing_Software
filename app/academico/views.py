import datetime
from django.utils import timezone
from django.db.models import Count, Avg
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import transaction
from django.contrib import messages
from django.core.exceptions import ValidationError

from academico.services import ServiciosAcademico
from main.services import ActionFlag, LogAction
from main.utils import group_required
from .models import CalendarioAcademico, Calificacion, Materia, Comision, InscripcionAlumnoComision, Asistencia, Alumno
from institucional.models import Empleado, Persona
from .exceptions import (
    TipoCalificacionInvalidoError,
    RangoCalificacionInvalidoError,
    AsistenciaNoExisteError,
    FechaNoClaseError
)
from .forms import RegistroAsistenciaForm, CalificacionForm, NotaIndividualForm


class DocenteRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.groups.filter(name='Docente').exists()

    def handle_no_permission(self):
        return redirect('acceso-denegado')


class DashboardProfesoresView(DocenteRequiredMixin, View):
    servicios_academico = ServiciosAcademico()

    def get(self, request):
        empleado = self.servicios_academico.obtener_docente_actual(request.user)
        estadisticas = self.servicios_academico.obtener_estadisticas_docente(empleado)
        # Optimizar query con select_related para evitar N+1
        comisiones = self.servicios_academico.obtener_comisiones_docente(empleado).select_related(
            'materia', 'anio_academico'
        ).filter(estado='EN_CURSO')

        # Obtener comisiones con clases hoy
        dia_hoy = timezone.now().weekday() + 1
        comisiones_hoy = comisiones.filter(dia_cursado=dia_hoy).order_by('horario_inicio')

        # Calcular estadísticas adicionales por comisión
        comisiones_con_stats = []
        for comision in comisiones:
            inscripciones = InscripcionAlumnoComision.objects.filter(comision=comision)
            total_alumnos = inscripciones.count()

            # Calificaciones pendientes (alumnos sin todas las evaluaciones)
            tipos_evaluacion = Calificacion.objects.filter(
                alumno_comision__comision=comision
            ).values('tipo').distinct().count()

            alumnos_con_calificaciones_completas = 0
            if tipos_evaluacion > 0:
                for inscripcion in inscripciones:
                    calif_alumno = Calificacion.objects.filter(alumno_comision=inscripcion).count()
                    if calif_alumno >= tipos_evaluacion:
                        alumnos_con_calificaciones_completas += 1

            pendientes = total_alumnos - alumnos_con_calificaciones_completas if tipos_evaluacion > 0 else total_alumnos

            comisiones_con_stats.append({
                'comision': comision,
                'total_alumnos': total_alumnos,
                'calificaciones_pendientes': pendientes,
                'tiene_pendientes': pendientes > 0
            })

        return render(request, 'academico/docentes.html', {
            'docente': empleado,
            'comisiones_con_stats': comisiones_con_stats,
            'comisiones_hoy': comisiones_hoy,
            'clases_hoy': estadisticas['clases_hoy'],
            'total_alumnos': estadisticas['total_alumnos'],
            'total_comisiones': comisiones.count()
        })

class CalificacionesCursoView(DocenteRequiredMixin, View):
    servicios_academico = ServiciosAcademico()

    def get(self, request, codigo):
        comision = get_object_or_404(Comision, codigo=codigo)

        # Obtener todas las inscripciones de alumnos
        inscripciones = InscripcionAlumnoComision.objects.filter(
            comision=comision
        ).select_related('alumno').order_by('alumno__apellido', 'alumno__nombre')

        # Obtener todos los tipos de calificación que existen para esta comisión
        tipos_calificacion = Calificacion.objects.filter(
            alumno_comision__comision=comision
        ).values('tipo').distinct().order_by('tipo')

        # Crear matriz de calificaciones
        matriz_calificaciones = []
        for inscripcion in inscripciones:
            fila = {
                'inscripcion': inscripcion,
                'alumno': inscripcion.alumno,
                'calificaciones': {},
                'promedio': 0,
                'total_calificaciones': 0
            }

            # Obtener todas las calificaciones del alumno
            calificaciones_alumno = Calificacion.objects.filter(
                alumno_comision=inscripcion
            )

            suma_notas = 0
            cantidad_notas = 0

            for calif in calificaciones_alumno:
                fila['calificaciones'][calif.tipo] = {
                    'nota': calif.nota,
                    'fecha': calif.fecha_creacion
                }
                suma_notas += float(calif.nota)
                cantidad_notas += 1

            if cantidad_notas > 0:
                fila['promedio'] = round(suma_notas / cantidad_notas, 2)
                fila['total_calificaciones'] = cantidad_notas

            matriz_calificaciones.append(fila)

        # Calcular promedios por tipo de evaluación
        promedios_por_tipo = {}
        for tipo in tipos_calificacion:
            promedio = Calificacion.objects.filter(
                alumno_comision__comision=comision,
                tipo=tipo['tipo']
            ).aggregate(promedio=Avg('nota'))
            promedios_por_tipo[tipo['tipo']] = round(promedio['promedio'], 2) if promedio['promedio'] else 0

        # Calcular promedio general del curso
        promedio_general = Calificacion.objects.filter(
            alumno_comision__comision=comision
        ).aggregate(promedio=Avg('nota'))

        return render(request, 'academico/calificaciones_curso.html', {
            'comision': comision,
            'matriz_calificaciones': matriz_calificaciones,
            'tipos_calificacion': tipos_calificacion,
            'promedios_por_tipo': promedios_por_tipo,
            'promedio_general': round(promedio_general['promedio'], 2) if promedio_general['promedio'] else 0,
            'total_alumnos': inscripciones.count()
        })

class GestionAsistenciaView(DocenteRequiredMixin, View):
    servicios_academico = ServiciosAcademico()

    def get(self, request, codigo, fecha_guardado = None):
            comision = self.servicios_academico.obtener_comision_por_codigo(codigo)
            # Optimizar con select_related para evitar N+1 en alumno
            alumnos_comision = self.servicios_academico.obtener_alumnos_comision(comision).select_related('alumno')

            # Obtener todas las fechas de clase disponibles
            fechas_clase, fecha_default = self.servicios_academico.obtener_fechas_clases(comision)

            if not fecha_guardado:
                fecha_seleccionada_str = request.GET.get('fecha')
            else:
                fecha_seleccionada_str = fecha_guardado

            # Determinar la fecha seleccionada
            if fecha_seleccionada_str:
                try:
                    fecha_seleccionada = timezone.datetime.strptime(str(fecha_seleccionada_str), '%Y-%m-%d').date()
                except ValueError:
                    fecha_seleccionada = fecha_default
            else:
                fecha_seleccionada = fecha_default

            # Cargar asistencias para la fecha seleccionada
            for alumno_comision in alumnos_comision:
                try:
                    asistencia = self.servicios_academico.obtener_asistencia_alumno_hoy(alumno_comision, fecha_seleccionada)
                    alumno_comision.alumno.presente = asistencia.esta_presente
                except AsistenciaNoExisteError:
                    alumno_comision.alumno.presente = False

                if fecha_seleccionada:
                    alumno_comision.alumno.porcentaje_asistencia = self.servicios_academico.obtener_porcentaje_asistencia(alumno_comision, fecha_seleccionada)
                else:
                    alumno_comision.alumno.porcentaje_asistencia = 0

            contexto = {
                    'comision': comision,
                    'alumnos_comision': alumnos_comision,
                    'fecha_seleccionada': fecha_seleccionada,
                    'fechas_clase': fechas_clase
                }
            return render(request, 'academico/asistencia_curso.html', context = contexto)


    @transaction.atomic
    def post(self, request, codigo):
        try:
            # Validar datos del formulario principal
            form = RegistroAsistenciaForm(request.POST)
            if not form.is_valid():
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, error)
                return redirect('asistencia_curso', codigo=codigo)

            datos = request.POST
            comision = self.servicios_academico.obtener_comision_por_codigo(codigo)
            fecha_asistencia = form.cleaned_data['fecha_asistencia']

            for d in datos:
                if d.startswith('asistencia_'):
                    alumno_id = int(d.replace('asistencia_',''))
                    estado_alumno_asistencia = datos[d]

                    alumno = get_object_or_404(Alumno, id=alumno_id)

                    if estado_alumno_asistencia == 'PRESENTE':
                        estado_alumno_asistencia = True
                    elif estado_alumno_asistencia == 'AUSENTE':
                        estado_alumno_asistencia = False

                    asistencia, _ = self.servicios_academico.registrar_asistencia(
                        alumno, comision, estado_alumno_asistencia, fecha_asistencia
                    )

                    if asistencia.esta_presente:
                        asistencia.esta_presente = 'Presente'
                    else:
                        asistencia.esta_presente = 'Ausente'

                    LogAction(
                        user=request.user,
                        model_instance_or_queryset=asistencia,
                        action=ActionFlag.CHANGE,
                        change_message="Cambio de estado de asistencia"
                    ).log()

            messages.success(request, 'Asistencias registradas correctamente.')
            return self.get(request, codigo, fecha_asistencia)

        except FechaNoClaseError as e:
            messages.error(request, str(e))
            return redirect('asistencia_curso', codigo=codigo)
        except ValueError as e:
            messages.error(request, f'Error en los datos enviados: {str(e)}')
            return redirect('asistencia_curso', codigo=codigo)
        except Exception as e:
            messages.error(request, f'Error inesperado al registrar asistencias: {str(e)}')
            return redirect('asistencia_curso', codigo=codigo)

class GestionClasesView(DocenteRequiredMixin, View):
    servicios_academico = ServiciosAcademico()
    
    def get(self, request):
        persona = get_object_or_404(Empleado, usuario=request.user)
        # Optimizar con select_related para materia y año académico
        comisiones = Comision.objects.filter(
            docente=persona,
            estado='EN_CURSO'
        ).select_related('materia', 'anio_academico')
        comisiones_con_fechas = []
        for comision in comisiones:
            fechas_clase, _ = self.servicios_academico.obtener_fechas_clases(comision)
            
            comisiones_con_fechas.append({
                'comision': comision,
                'fechas_clase': fechas_clase,
                'proxima_clase': fechas_clase.first() if fechas_clase else None
            })
        
        return render(request, 'academico/seleccionar_clase_asistencia.html', {
            'comisiones_con_fechas': comisiones_con_fechas
        })

class GestionCalificacionesView(DocenteRequiredMixin, View):
    servicios_academico = ServiciosAcademico()

    def get(self, request, codigo):
        comision = self.servicios_academico.obtener_comision_por_codigo(codigo)
        # Optimizar con select_related para alumno
        inscripciones = self.servicios_academico.obtener_alumnos_comision(codigo).select_related('alumno')
        contexto = {
            'hoy':datetime.datetime.now(),
            'comision': comision,
            'materia': comision.materia,
            'inscripciones': inscripciones
        }
        return render(request, 'academico/carga_calificacion.html', context=contexto)

    @transaction.atomic
    def post(self, request, codigo):
        try:
            # Validar datos del formulario principal
            form = CalificacionForm(request.POST)
            if not form.is_valid():
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, error)
                return redirect('crear_calificacion', codigo=codigo)

            datos = request.POST
            fecha = form.cleaned_data['fecha']
            tipo_calificacion = form.cleaned_data['tipo']

            alumnos_comision = self.servicios_academico.obtener_alumnos_comision(codigo)
            calificaciones_creadas = 0

            for dato in datos:
                if dato.startswith('nota_'):
                    alumno_id = int(dato.replace('nota_', ''))

                    # Validar cada nota individual
                    nota_form = NotaIndividualForm({'nota': datos[dato][0]})
                    if not nota_form.is_valid():
                        for error in nota_form.errors.get('nota', []):
                            messages.error(request, f'Alumno ID {alumno_id}: {error}')
                        continue

                    calificacion = nota_form.cleaned_data['nota']
                    alumno = alumnos_comision.get(alumno__id=alumno_id)

                    calificacion_nuevo = self.servicios_academico.crear_calificacion(
                        alumno, fecha, tipo_calificacion, calificacion
                    )

                    LogAction(
                        user=request.user,
                        model_instance_or_queryset=calificacion_nuevo,
                        action=ActionFlag.ADDITION,
                        change_message="Se crea calificación"
                    ).log()

                    calificaciones_creadas += 1

            messages.success(
                request,
                f'Se crearon {calificaciones_creadas} calificaciones correctamente.'
            )
            return redirect('calificaciones_curso', codigo=codigo)

        except TipoCalificacionInvalidoError as e:
            messages.error(request, str(e))
            return redirect('crear_calificacion', codigo=codigo)
        except RangoCalificacionInvalidoError as e:
            messages.error(request, str(e))
            return redirect('crear_calificacion', codigo=codigo)
        except ValueError as e:
            messages.error(request, f'Error en el formato de las calificaciones: {str(e)}')
            return redirect('crear_calificacion', codigo=codigo)
        except Exception as e:
            messages.error(request, f'Error inesperado al crear calificaciones: {str(e)}')
            return redirect('crear_calificacion', codigo=codigo)
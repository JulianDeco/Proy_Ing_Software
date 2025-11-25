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
        )

        return render(request, 'academico/docentes.html', {
            'docente': empleado,
            'comisiones': comisiones,
            'clases_hoy': estadisticas['clases_hoy'],
            'total_alumnos': estadisticas['total_alumnos']
        })

class CalificacionesCursoView(DocenteRequiredMixin, View):
    servicios_academico = ServiciosAcademico()

    def get(self, request, codigo):
        comision = get_object_or_404(Comision, codigo=codigo)
        calificaciones = Calificacion.objects.filter(
            alumno_comision__comision=comision
        ).values('tipo', 'fecha_creacion').annotate(
            promedio=Avg('nota')
        ).order_by('tipo', '-fecha_creacion')
        
        resumen = []
        for calif in calificaciones:
            resumen.append({
                'tipo': calif['tipo'],
                'fecha_creacion': calif['fecha_creacion'].strftime('%d/%m/%Y') if calif['fecha_creacion'] else 'Sin fecha',
                'promedio': round(calif['promedio'], 2) if calif['promedio'] else 0
            })
        
        return render(request, 'academico/calificaciones_curso.html', {
            'comision': comision,
            'calificaciones': resumen
        })

class GestionAsistenciaView(DocenteRequiredMixin, View):
    servicios_academico = ServiciosAcademico()

    def get(self, request, codigo, fecha_guardado = None):
            comision = self.servicios_academico.obtener_comision_por_codigo(codigo)
            # Optimizar con select_related para evitar N+1 en alumno
            alumnos_comision = self.servicios_academico.obtener_alumnos_comision(comision).select_related('alumno')

            if not fecha_guardado:
                fecha_seleccionada = request.GET.get('fecha')
            else:
                fecha_seleccionada = fecha_guardado

            for alummo_comision in alumnos_comision:
                try:
                    asistencia = self.servicios_academico.obtener_asistencia_alumno_hoy(alummo_comision, fecha_seleccionada)
                    alummo_comision.alumno.presente = asistencia.esta_presente
                except AsistenciaNoExisteError:
                    alummo_comision.alumno.presente = False

                alummo_comision.alumno.porcentaje_asistencia = self.servicios_academico.obtener_porcentaje_asistencia(alummo_comision, fecha_seleccionada)

            if fecha_seleccionada:
                try:
                    fechas_clase, _= self.servicios_academico.obtener_fechas_clases(comision)
                    fecha_seleccionada = timezone.datetime.strptime(fecha_seleccionada, '%Y-%m-%d').date()
                except ValueError:
                    fecha_seleccionada = None
            else:
                fechas_clase, fecha_seleccionada = self.servicios_academico.obtener_fechas_clases(comision)

            contexto = {
                    'comision': comision,
                    'alumnos_comision': alumnos_comision,
                    'fecha_seleccionada': fecha_seleccionada
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
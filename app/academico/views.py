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
from django.http import HttpResponse
from django.template.loader import render_to_string
from weasyprint import HTML

from academico.services import ServiciosAcademico
from main.services import ActionFlag, LogAction
from main.utils import group_required
from .models import (
    CalendarioAcademico, Calificacion, Materia, Comision, InscripcionAlumnoComision,
    Asistencia, Alumno, MesaExamen, InscripcionMesaExamen, TipoCalificacion
)
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
        messages.error(self.request, "No tiene permisos para acceder a esta sección.")
        return redirect('home')


class CierreCursadaView(DocenteRequiredMixin, View):
    """Vista para previsualizar y ejecutar el cierre de cursada (Regularización)"""
    servicios_academico = ServiciosAcademico()

    def get(self, request, codigo):
        comision = get_object_or_404(Comision, codigo=codigo)
        docente = get_object_or_404(Empleado, usuario=request.user)
        
        # Validar que el docente sea el titular
        if comision.docente_id != docente.id:
            messages.error(request, "No tiene permiso para cerrar esta comisión.")
            return redirect('docentes')

        if comision.estado == 'FINALIZADA':
            messages.warning(request, "Esta comisión ya fue cerrada.")
            return redirect('docentes')

        # Simulación de resultados
        inscripciones = InscripcionAlumnoComision.objects.filter(
            comision=comision,
            estado_inscripcion='REGULAR'
        ).select_related('alumno')

        anio = comision.anio_academico
        simulacion = []
        
        for inscripcion in inscripciones:
            promedio = self.servicios_academico.calcular_promedio_cursada(inscripcion)
            asistencia = self.servicios_academico.obtener_porcentaje_asistencia(
                inscripcion, timezone.now().date()
            )
            
            cumple_nota = promedio is not None and promedio >= anio.nota_aprobacion
            cumple_asistencia = asistencia >= anio.porcentaje_asistencia_req
            
            condicion = 'REGULAR' if cumple_nota and cumple_asistencia else 'LIBRE'
            motivo = ""
            if not cumple_nota: motivo += "Nota insuficiente. "
            if not cumple_asistencia: motivo += "Faltas."

            simulacion.append({
                'alumno': inscripcion.alumno,
                'promedio': promedio,
                'asistencia': asistencia,
                'condicion': condicion,
                'motivo': motivo
            })

        return render(request, 'academico/cierre_cursada.html', {
            'comision': comision,
            'simulacion': simulacion
        })

    def post(self, request, codigo):
        comision = get_object_or_404(Comision, codigo=codigo)
        docente = get_object_or_404(Empleado, usuario=request.user)

        if comision.docente_id != docente.id:
            messages.error(request, "No tiene permiso para cerrar esta comisión.")
            return redirect('docentes')

        resultado = self.servicios_academico.regularizar_comision(comision, request.user)

        if resultado['success']:
            messages.success(request, resultado['mensaje'])
            LogAction(
                user=request.user,
                model_instance_or_queryset=comision,
                action=ActionFlag.CHANGE,
                change_message=f"Cierre de cursada: {resultado['mensaje']}"
            ).log()
        else:
            messages.error(request, resultado['mensaje'])
            return redirect('cerrar_cursada', codigo=codigo)

        return redirect('docentes')


class DocenteRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.groups.filter(name='Docente').exists()

    def handle_no_permission(self):
        messages.error(self.request, "No tiene permisos para acceder a esta sección.")
        return redirect('home')


class DashboardProfesoresView(DocenteRequiredMixin, View):
    servicios_academico = ServiciosAcademico()

    def get(self, request):
        empleado = self.servicios_academico.obtener_docente_actual(request.user)
        estadisticas = self.servicios_academico.obtener_estadisticas_docente(empleado)
        # Optimizar query con select_related para evitar N+1
        comisiones_queryset = self.servicios_academico.obtener_comisiones_docente(empleado).select_related(
            'materia', 'anio_academico'
        )
        
        comisiones_activas = comisiones_queryset.filter(estado='EN_CURSO')
        comisiones_finalizadas = comisiones_queryset.filter(estado='FINALIZADA').order_by('-anio_academico__nombre', '-materia__nombre')

        # Obtener comisiones con clases hoy (solo de las activas)
        dia_hoy = timezone.now().weekday() + 1
        comisiones_hoy = comisiones_activas.filter(dia_cursado=dia_hoy).order_by('horario_inicio')

        # Calcular estadísticas adicionales por comisión (solo activas)
        comisiones_con_stats = []
        for comision in comisiones_activas:
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
            'comisiones_finalizadas': comisiones_finalizadas,
            'comisiones_hoy': comisiones_hoy,
            'clases_hoy': estadisticas['clases_hoy'],
            'total_alumnos': estadisticas['total_alumnos'],
            'total_comisiones': comisiones_activas.count()
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
                'total_calificaciones': 0,
                'condicion': inscripcion.get_condicion_display(),
                'asistencia': self.servicios_academico.obtener_porcentaje_asistencia(
                    inscripcion, timezone.now().date()
                )
            }

            # Obtener todas las calificaciones del alumno
            calificaciones_alumno = Calificacion.objects.filter(
                alumno_comision=inscripcion
            )

            suma_notas = 0
            cantidad_notas = 0

            for calif in calificaciones_alumno:
                if calif.tipo not in fila['calificaciones']:
                    fila['calificaciones'][calif.tipo] = []
                
                fila['calificaciones'][calif.tipo].append({
                    'id': calif.id,
                    'nota': calif.nota,
                    'fecha': calif.fecha_creacion,
                    'numero': calif.numero
                })
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

import json # Importar json
# ...
class GestionCalificacionesView(DocenteRequiredMixin, View):
    servicios_academico = ServiciosAcademico()

    def get(self, request, codigo):
        comision = self.servicios_academico.obtener_comision_por_codigo(codigo)
        inscripciones = self.servicios_academico.obtener_alumnos_comision(comision).select_related('alumno')
        
        # Obtener parámetros de la URL para precargar
        pre_selected_tipo = request.GET.get('tipo')
        pre_selected_alumno_id = request.GET.get('alumno_id')

        # Obtener todas las calificaciones de la comisión para precargar
        calificaciones_existentes = Calificacion.objects.filter(
            alumno_comision__comision=comision
        ).values('alumno_comision__alumno__id', 'tipo', 'numero', 'nota')

        # Convertir a un formato fácil de usar en JS:
        # {alumno_id: {tipo_calificacion: {numero: nota}, ...}, ...}
        notas_por_alumno = {}
        for calif in calificaciones_existentes:
            alumno_id = str(calif['alumno_comision__alumno__id']) # Convertir a str para coincidir con JS
            tipo = calif['tipo']
            numero = calif['numero']
            nota = float(calif['nota'])
            
            if alumno_id not in notas_por_alumno:
                notas_por_alumno[alumno_id] = {}
            
            if tipo not in notas_por_alumno[alumno_id]:
                notas_por_alumno[alumno_id][tipo] = {}
            
            notas_por_alumno[alumno_id][tipo][numero] = nota

        contexto = {
            'hoy':timezone.now().date(), # Usar date() para compatibilidad con input type="date"
            'comision': comision,
            'materia': comision.materia,
            'inscripciones': inscripciones,
            'tipos_calificacion': TipoCalificacion.choices, # Pasar los choices para el select
            'notas_por_alumno_json': json.dumps(notas_por_alumno), # Para usar en JS
            'pre_selected_tipo': pre_selected_tipo,
            'pre_selected_alumno_id': pre_selected_alumno_id,
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
            try:
                numero_instancia = int(request.POST.get('numero', 1))
            except (ValueError, TypeError):
                numero_instancia = 1

            comision = self.servicios_academico.obtener_comision_por_codigo(codigo)
            alumnos_comision = self.servicios_academico.obtener_alumnos_comision(comision)
            calificaciones_creadas = 0

            for dato in datos:
                if dato.startswith('nota_'):
                    alumno_id = int(dato.replace('nota_', ''))

                    # Validar cada nota individual
                    nota_form = NotaIndividualForm({'nota': datos[dato]})
                    if not nota_form.is_valid():
                        for error in nota_form.errors.get('nota', []):
                            messages.error(request, f'Alumno ID {alumno_id}: {error}')
                        continue

                    calificacion = nota_form.cleaned_data['nota']
                    alumno = alumnos_comision.get(alumno__id=alumno_id)

                    calificacion_nuevo = self.servicios_academico.crear_calificacion(
                        alumno, fecha, tipo_calificacion, calificacion, numero=numero_instancia
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


class EditarCalificacionView(DocenteRequiredMixin, View):
    def get(self, request, id):
        calificacion = get_object_or_404(Calificacion, id=id)
        
        # Verificar que el docente sea el titular de la comisión
        docente = get_object_or_404(Empleado, usuario=request.user)
        if calificacion.alumno_comision.comision.docente_id != docente.id:
            messages.error(request, "No tiene permiso para editar esta calificación.")
            return redirect('docentes')

        return render(request, 'academico/editar_calificacion.html', {
            'calificacion': calificacion
        })

    def post(self, request, id):
        calificacion = get_object_or_404(Calificacion, id=id)
        docente = get_object_or_404(Empleado, usuario=request.user)
        
        if calificacion.alumno_comision.comision.docente_id != docente.id:
            messages.error(request, "No tiene permiso para editar esta calificación.")
            return redirect('docentes')

        try:
            nueva_nota = float(request.POST.get('nota'))
            if nueva_nota < 0 or nueva_nota > 10:
                messages.error(request, "La nota debe estar entre 0 y 10.")
                return render(request, 'academico/editar_calificacion.html', {'calificacion': calificacion})
            
            calificacion.nota = nueva_nota
            calificacion.save()
            
            LogAction(
                user=request.user,
                model_instance_or_queryset=calificacion,
                action=ActionFlag.CHANGE,
                change_message=f"Nota modificada a {nueva_nota}"
            ).log()

            messages.success(request, "Calificación actualizada correctamente.")
            return redirect('calificaciones_curso', codigo=calificacion.alumno_comision.comision.codigo)

        except ValueError:
            messages.error(request, "Formato de nota inválido.")
            return render(request, 'academico/editar_calificacion.html', {'calificacion': calificacion})

class MesasExamenDocenteView(DocenteRequiredMixin, View):
    """Vista para que docentes vean las mesas donde son parte del tribunal"""

    def get(self, request):
        docente = get_object_or_404(Empleado, usuario=request.user)

        # Obtener mesas donde el docente es parte del tribunal
        mesas = MesaExamen.objects.filter(
            tribunal=docente
        ).select_related('materia', 'anio_academico').prefetch_related('inscripciones_mesa__alumno')

        # Agregar información de inscripciones a cada mesa
        mesas_con_info = []
        for mesa in mesas:
            inscripciones = mesa.inscripciones_mesa.select_related('alumno').all()

            mesas_con_info.append({
                'mesa': mesa,
                'total_inscriptos': inscripciones.filter(estado_inscripcion='INSCRIPTO').count(),
                'aprobados': inscripciones.filter(estado_inscripcion='APROBADO').count(),
                'desaprobados': inscripciones.filter(estado_inscripcion='DESAPROBADO').count(),
                'ausentes': inscripciones.filter(estado_inscripcion='AUSENTE').count(),
            })

        return render(request, 'academico/mesas_examen_docente.html', {
            'mesas_con_info': mesas_con_info,
            'docente': docente
        })


class DetalleInscriptosMesaView(DocenteRequiredMixin, View):
    """Vista para ver el detalle de alumnos inscriptos a una mesa"""

    def get(self, request, mesa_id):
        mesa = get_object_or_404(MesaExamen, id=mesa_id)
        docente = get_object_or_404(Empleado, usuario=request.user)

        # Verificar que el docente sea parte del tribunal
        if not mesa.tribunal.filter(id=docente.id).exists():
            messages.error(request, 'No tiene permisos para ver esta mesa.')
            return redirect('mesas_examen_docente')

        # Obtener inscripciones ordenadas por apellido
        inscripciones = InscripcionMesaExamen.objects.filter(
            mesa_examen=mesa
        ).select_related('alumno').order_by('alumno__apellido', 'alumno__nombre')

        # Separar por condición
        inscripciones_regulares = inscripciones.filter(condicion='REGULAR')
        inscripciones_libres = inscripciones.filter(condicion='LIBRE')

        return render(request, 'academico/detalle_inscriptos_mesa.html', {
            'mesa': mesa,
            'inscripciones_regulares': inscripciones_regulares,
            'inscripciones_libres': inscripciones_libres,
            'total_inscriptos': inscripciones.count(),
            'puede_editar': mesa.estado != 'FINALIZADA'
        })

    @transaction.atomic
    def post(self, request, mesa_id):
        """Procesar carga de notas de examen"""
        mesa = get_object_or_404(MesaExamen, id=mesa_id)
        docente = get_object_or_404(Empleado, usuario=request.user)

        # Verificar permisos
        if not mesa.tribunal.filter(id=docente.id).exists():
            messages.error(request, 'No tiene permisos para modificar esta mesa.')
            return redirect('mesas_examen_docente')

        if mesa.estado == 'FINALIZADA':
            messages.error(request, 'Esta mesa ya está finalizada.')
            return redirect('detalle_inscriptos_mesa', mesa_id=mesa_id)

        try:
            notas_cargadas = 0
            errores = []

            for key, value in request.POST.items():
                if key.startswith('nota_'):
                    inscripcion_id = int(key.replace('nota_', ''))

                    try:
                        inscripcion = InscripcionMesaExamen.objects.get(id=inscripcion_id)

                        if value and value.strip():
                            nota = float(value)

                            if nota < 0 or nota > 10:
                                errores.append(f'{inscripcion.alumno}: La nota debe estar entre 0 y 10')
                                continue

                            # Cargar nota usando el servicio
                            success, mensaje = ServiciosAcademico.cargar_nota_examen_final(
                                inscripcion, nota, request.user
                            )

                            if success:
                                notas_cargadas += 1
                            else:
                                errores.append(f'{inscripcion.alumno}: {mensaje}')

                    except InscripcionMesaExamen.DoesNotExist:
                        errores.append(f'Inscripción {inscripcion_id} no encontrada')
                    except ValueError:
                        errores.append(f'{inscripcion.alumno}: Formato de nota inválido')

            if notas_cargadas > 0:
                messages.success(request, f'Se cargaron {notas_cargadas} notas correctamente.')

            if errores:
                for error in errores:
                    messages.warning(request, error)

            return redirect('detalle_inscriptos_mesa', mesa_id=mesa_id)

        except Exception as e:
            messages.error(request, f'Error al procesar notas: {str(e)}')
            return redirect('detalle_inscriptos_mesa', mesa_id=mesa_id)


class ActaExamenPDFView(DocenteRequiredMixin, View):
    """Vista para generar el acta de examen en PDF"""

    def get(self, request, mesa_id):
        mesa = get_object_or_404(MesaExamen, id=mesa_id)
        docente = get_object_or_404(Empleado, usuario=request.user)

        # Verificar que el docente sea parte del tribunal
        if not mesa.tribunal.filter(id=docente.id).exists():
            messages.error(request, 'No tiene permisos para generar el acta de esta mesa.')
            return redirect('mesas_examen_docente')

        # Obtener inscripciones
        inscripciones = InscripcionMesaExamen.objects.filter(
            mesa_examen=mesa
        ).select_related('alumno').order_by('alumno__apellido', 'alumno__nombre')

        inscripciones_regulares = inscripciones.filter(condicion='REGULAR')
        inscripciones_libres = inscripciones.filter(condicion='LIBRE')

        # Calcular estadísticas
        total_inscriptos = inscripciones.count()
        total_regulares = inscripciones_regulares.count()
        total_libres = inscripciones_libres.count()
        total_aprobados = inscripciones.filter(estado_inscripcion='APROBADO').count()
        total_desaprobados = inscripciones.filter(estado_inscripcion='DESAPROBADO').count()
        total_ausentes = inscripciones.filter(estado_inscripcion='AUSENTE').count()

        # Contexto para el template
        context = {
            'mesa': mesa,
            'tribunal': mesa.tribunal.all(),
            'inscripciones_regulares': inscripciones_regulares,
            'inscripciones_libres': inscripciones_libres,
            'total_inscriptos': total_inscriptos,
            'total_regulares': total_regulares,
            'total_libres': total_libres,
            'total_aprobados': total_aprobados,
            'total_desaprobados': total_desaprobados,
            'total_ausentes': total_ausentes,
            'fecha_generacion': timezone.now(),
        }

        # Renderizar HTML
        html_string = render_to_string('academico/acta_examen_pdf.html', context)

        # Generar PDF
        html = HTML(string=html_string)
        pdf = html.write_pdf()

        # Crear respuesta HTTP
        response = HttpResponse(pdf, content_type='application/pdf')
        filename = f'acta_examen_{mesa.materia.codigo}_{mesa.fecha_examen.strftime("%Y%m%d")}.pdf'
        response['Content-Disposition'] = f'inline; filename="{filename}"'

        return response


class HistoricoMesasAlumnoView(DocenteRequiredMixin, View):
    """Vista para ver el histórico de mesas rendidas por un alumno"""

    def get(self, request, alumno_id):
        alumno = get_object_or_404(Alumno, id=alumno_id)

        # Obtener todas las inscripciones a mesas del alumno
        inscripciones = InscripcionMesaExamen.objects.filter(
            alumno=alumno
        ).select_related('mesa_examen__materia', 'mesa_examen__anio_academico').order_by('-mesa_examen__fecha_examen')

        # Separar por estado
        mesas_aprobadas = inscripciones.filter(estado_inscripcion='APROBADO')
        mesas_desaprobadas = inscripciones.filter(estado_inscripcion='DESAPROBADO')
        mesas_ausentes = inscripciones.filter(estado_inscripcion='AUSENTE')
        mesas_inscriptas = inscripciones.filter(estado_inscripcion='INSCRIPTO')

        # Calcular estadísticas
        total_mesas = inscripciones.count()
        total_aprobadas = mesas_aprobadas.count()
        total_desaprobadas = mesas_desaprobadas.count()
        total_ausentes = mesas_ausentes.count()

        # Calcular promedio de notas en exámenes
        notas = [i.nota_examen for i in inscripciones if i.nota_examen]
        promedio_examenes = sum(notas) / len(notas) if notas else 0

        return render(request, 'academico/historico_mesas_alumno.html', {
            'alumno': alumno,
            'inscripciones': inscripciones,
            'mesas_aprobadas': mesas_aprobadas,
            'mesas_desaprobadas': mesas_desaprobadas,
            'mesas_ausentes': mesas_ausentes,
            'mesas_inscriptas': mesas_inscriptas,
            'total_mesas': total_mesas,
            'total_aprobadas': total_aprobadas,
            'total_desaprobadas': total_desaprobadas,
            'total_ausentes': total_ausentes,
            'promedio_examenes': round(promedio_examenes, 2)
        })
import datetime
from django.utils import timezone
from django.db.models import Count, Avg
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.views import View

from academico.services import ServiciosAcademico
from main.services import ActionFlag, LogAction
from main.utils import group_required
from .models import CalendarioAcademico, Calificacion, Materia, Comision, InscripcionesAlumnosComisiones, Asistencia, Alumno
from institucional.models import Empleado, Persona

@login_required
@group_required('Docente')
def dashboard_profesores(request):
    datos_usuario = request.user
    datos_persona = Empleado.objects.get(usuario = datos_usuario)
    comisiones = Comision.objects.filter(docente = datos_persona)
    clases_hoy = comisiones.filter(dia_cursado=datetime.datetime.now().weekday() + 1).count()
    total_alumnos = 0
    for comision in comisiones:
        consulta_inscriptos_comision = InscripcionesAlumnosComisiones.objects.filter(comision = comision)
        total_alumnos = total_alumnos + consulta_inscriptos_comision.count()
    return render(  request, 
                    'academico/docentes.html', 
                    context= {
                    'docente': datos_persona,
                    'comisiones':comisiones,
                    'clases_hoy':clases_hoy,
                    'total_alumnos':total_alumnos
                    }
    )

@login_required
@group_required('Docente')
def asistencia_curso(request, codigo, param_asistencia = None):
    comision = Comision.objects.get(codigo=codigo)
    alumnos_comision = InscripcionesAlumnosComisiones.objects.filter(comision=comision)
    if not param_asistencia:
        contexto = {
            'comision': comision,
            'alumnos_comision': alumnos_comision
        }
        return render(request, 'academico/asistencia_curso.html', context = contexto)
    
    for alummo_comision in alumnos_comision:
        fecha_actual = timezone.now().date()
        asistencia = Asistencia.objects.get(alumno_comision = alummo_comision, fecha_asistencia=fecha_actual)
        alummo_comision.alumno.presente = asistencia.esta_presente

    contexto = {
            'comision': comision,
            'alumnos_comision': alumnos_comision
        }
    return render(request, 'academico/asistencia_curso.html', context = contexto)

@login_required
@group_required('Docente')
def registrar_asistencia(request, codigo):
    datos = request.POST
    comision = get_object_or_404(Comision, codigo=codigo)
    for d in datos:
        if d.startswith('asistencia_'):
            alumno_id = int(d.replace('asistencia_',''))
            estado_alumno_asistencia = datos[d]

            alumno = Alumno.objects.get(id = alumno_id)

            if estado_alumno_asistencia == 'PRESENTE':
                estado_alumno_asistencia = True
            elif estado_alumno_asistencia == 'AUSENTE':
                estado_alumno_asistencia = False

            fecha_actual = timezone.now().date()

            inscripcion_alumno = get_object_or_404(
                        InscripcionesAlumnosComisiones,
                        alumno=alumno, 
                        comision=comision,
                    )
            Asistencia.objects.update_or_create(
                        alumno_comision=inscripcion_alumno,
                        fecha_asistencia=fecha_actual,
                        defaults={
                            'esta_presente': estado_alumno_asistencia 
                        }
                    )
    param_asistencia = True
    return asistencia_curso(request, codigo, param_asistencia)

def calificaciones_curso(request, codigo):
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
    
    return render(request, 'academico/calificaciones_curso.html', 
        context = {
            'comision': comision,
            'calificaciones': resumen
    })

def crear_evaluacion(request, codigo):
    comision = get_object_or_404(InscripcionesAlumnosComisiones, comision__id=codigo)
    print(comision)

def guardar_calificaciones(request, codigo):
    pass

class DocenteRequiredMixin:
    def test_func(self):
        return self.request.user.groups.filter(name='Docente').exists()
    
    def dispatch(self, request, *args, **kwargs):
        if not self.test_func():
            return redirect('acceso-denegado')
        return super().dispatch(request, *args, **kwargs)
    
class GestionAsistenciaView(DocenteRequiredMixin, View):
    servicios_academico = ServiciosAcademico()

    def get(self, request, codigo, fecha_guardado = None):
            comision = self.servicios_academico.obtener_comision_por_codigo(codigo)
            alumnos_comision = self.servicios_academico.obtener_alumnos_comision(comision)

            if not fecha_guardado:
                fecha_seleccionada = request.GET.get('fecha')
            else:
                fecha_seleccionada = fecha_guardado

            for alummo_comision in alumnos_comision:
                asistencia = self.servicios_academico.obtener_asistencia_alumno_hoy(alummo_comision, fecha_seleccionada)
                if asistencia:
                    alummo_comision.alumno.presente = asistencia.esta_presente
            
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


    def post(self, request, codigo):
        datos = request.POST
        comision = self.servicios_academico.obtener_comision_por_codigo(codigo)
        fecha_asistencia = datos['fecha_asistencia']
        for d in datos:
            if d.startswith('asistencia_'):
                alumno_id = int(d.replace('asistencia_',''))
                estado_alumno_asistencia = datos[d]

                alumno = get_object_or_404(Alumno, id = alumno_id)

                if estado_alumno_asistencia == 'PRESENTE':
                    estado_alumno_asistencia = True
                elif estado_alumno_asistencia == 'AUSENTE':
                    estado_alumno_asistencia = False
                asistencia, _ = self.servicios_academico.registrar_asistencia(alumno, comision, estado_alumno_asistencia, fecha_asistencia)
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
        param_asistencia = True
        return self.get(request, codigo, fecha_asistencia)

class GestionClasesView(DocenteRequiredMixin, View):
    servicios_academico = ServiciosAcademico()
    
    def get(self, request):
        persona = get_object_or_404(Empleado, usuario=request.user)
        comisiones = Comision.objects.filter(
            docente=persona,
            estado='EN_CURSO'
        )
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
        inscripciones = self.servicios_academico.obtener_alumnos_comision(codigo)
        contexto = {
            'hoy':datetime.datetime.now(),
            'comision': comision,
            'materia': comision.materia,
            'inscripciones': inscripciones
        }
        return render(request, 'academico/carga_calificacion.html', context=contexto)

    def post(self, request, codigo):
        datos = request.POST
        fecha = datos.get('fecha')
        tipo_calificacion = datos.get('tipo')
        alumnos_comision = self.servicios_academico.obtener_alumnos_comision(codigo)
        for dato in datos:
            if dato.startswith('nota_'):
                alumno_id = int(dato.replace('nota_', ''))
                calificacion = int(datos[dato][0])
                alumno = alumnos_comision.get(alumno__id = alumno_id)
                calificacion_nuevo = self.servicios_academico.crear_calificacion(alumno, fecha, tipo_calificacion, calificacion)
                LogAction(
                    user=request.user,
                    model_instance_or_queryset=calificacion_nuevo,
                    action=ActionFlag.ADDITION,
                    change_message="Se crea calificación"
                    ).log()
        return calificaciones_curso(request, codigo)
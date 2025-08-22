import datetime
from django.utils import timezone
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.views import View

from academico.services import ServiciosAcademico
from main.utils import group_required
from .models import Materia, Comision, InscripcionesAlumnosComisiones, Asistencia, Alumno
from institucional.models import Empleado

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
    return render(request, 'academico/calificaciones_curso.html', 
        context = {
            'comision':comision
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

    def get(self, request, codigo, param_asistencia = None):
            comision = self.servicios_academico.obtener_comision_por_codigo(codigo)
            alumnos_comision = self.servicios_academico.obtener_alumnos_comision(comision)
            if not param_asistencia:
                contexto = {
                    'comision': comision,
                    'alumnos_comision': alumnos_comision
                }
                return render(request, 'academico/asistencia_curso.html', context = contexto)
            
            for alummo_comision in alumnos_comision:
                asistencia = self.servicios_academico.obtener_asistencia_alumno_hoy(alummo_comision)
                alummo_comision.alumno.presente = asistencia.esta_presente

            contexto = {
                    'comision': comision,
                    'alumnos_comision': alumnos_comision
                }
            return render(request, 'academico/asistencia_curso.html', context = contexto)


    def post(self, request, codigo):
        datos = request.POST
        comision = self.servicios_academico.obtener_comision_por_codigo(codigo)
        for d in datos:
            if d.startswith('asistencia_'):
                alumno_id = int(d.replace('asistencia_',''))
                estado_alumno_asistencia = datos[d]

                alumno = get_object_or_404(Alumno, id = alumno_id)

                if estado_alumno_asistencia == 'PRESENTE':
                    estado_alumno_asistencia = True
                elif estado_alumno_asistencia == 'AUSENTE':
                    estado_alumno_asistencia = False
                self.servicios_academico.registrar_asistencia(alumno, comision, estado_alumno_asistencia)
        param_asistencia = True
        return self.get(request, codigo, param_asistencia)

class GestionCalificacionesView(DocenteRequiredMixin, View):
    def get(self, request):
        pass

    def post(self, request):
        pass
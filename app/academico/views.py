from django.utils import timezone
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required

from main.utils import group_required
from .models import Materia, Comision, InscripcionesAlumnosComisiones, Asistencia, Alumno
from institucional.models import Empleado


@login_required
@group_required('Docente')
def home_academico(request):
    return render(request, 'academico/academico.html')


@login_required
@group_required('Docente')
def dashboard_profesores(request):
    datos_usuario = request.user
    datos_persona = Empleado.objects.get(usuario = datos_usuario)
    comisiones = Comision.objects.filter(docente = datos_persona)
    return render(  request, 
                    'profesores/dashboard.html', 
                    context= {
                    'docente': datos_persona,
                    'comisiones':comisiones
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

        asistencia = Asistencia.objects.get(alumno_comision = alummo_comision)
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
                        comision=comision
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
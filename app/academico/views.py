from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Materia, Comision, InscripcionesAlumnosComisiones
from institucional.models import Empleado


@login_required
def home_academico(request):
    return render(request, 'academico/academico.html')


@login_required
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
def asistencia_curso(request, codigo):
    comision = Comision.objects.get(codigo=codigo)
    alumnos_comision = InscripcionesAlumnosComisiones.objects.filter(comision=comision)
    contexto = {
        'comision': comision,
        'alumnos_comision': alumnos_comision
    }

    return render(request, 'academico/asistencia_curso.html', context = contexto)

@login_required
def registrar_asistencia(request):
    pass
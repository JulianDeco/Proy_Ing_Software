from django.shortcuts import render
from .models import Materia

def lista_materias(request):
    materias = Materia.objects.all()
    return render(request, 'academico/materia_list.html', {'materias': materias})
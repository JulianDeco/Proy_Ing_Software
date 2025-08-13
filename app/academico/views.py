from django.shortcuts import render
from .models import Materia

def home_academico(request):
    return render(request, 'academico/academico.html')
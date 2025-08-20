from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Materia


@login_required
def home_academico(request):
    return render(request, 'academico/academico.html')
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from main.utils import group_required

@login_required
@group_required('Administrativo')
def home_administracion(request):
    return render(request, 'administracion/administracion.html')
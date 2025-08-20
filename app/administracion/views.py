from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def home_administracion(request):
    return render(request, 'administracion/administracion.html')
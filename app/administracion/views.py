from django.shortcuts import render

def home_administracion(request):
    return render(request, 'administracion/administracion.html')
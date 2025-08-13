from django.http import HttpResponse

def vista_prueba(request):
    return HttpResponse("Hola desde la vista de prueba en institucional.")
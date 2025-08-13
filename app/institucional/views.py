from django.shortcuts import render

def home_institucional(request):
    return render(request, 'institucional/institucional.html')
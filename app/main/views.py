from django.http import HttpResponse

from django.shortcuts import render

def home(request):
    return render(request, 'main/index.html')

def dashboard_profesores(request):
    return render(request, 'profesores/dashboard.html')

def login(request):
    return render(request, 'security/login.html')
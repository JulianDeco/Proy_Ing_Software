from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.contrib.auth.views import LoginView
from django.contrib.auth import logout

from .forms import LoginEmailForm

def home(request):
    return render(request, 'main/index.html')

def dashboard_profesores(request):
    return render(request, 'profesores/dashboard.html')

class LoginEmailView(LoginView):
    template_name = 'security/login.html'
    authentication_form = LoginEmailForm
    
    
def redirect_based_group(request):
    if not request.user.is_authenticated:
        return redirect('login')

    user = request.user
    groups = user.groups.values_list('name', flat=True)  

    if 'Docente' in groups:
        return redirect('dashboard_docente')  
    elif 'Administrativo' in groups:
        return redirect('dashboard_admin')   
    elif 'Alumno' in groups:
        return redirect('dashboard_alumno')  
    else:
        return redirect('home')
    
def logout_view(request):
    logout(request)
    return redirect('login')
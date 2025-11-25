from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.contrib.auth.views import LoginView
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages

from .utils import group_required
from .forms import LoginEmailForm
from administracion.utils import crear_backup_completo

@login_required
@group_required('Administrativo')
def home(request):
    return render(request, 'main/index.html')

class LoginEmailView(LoginView):
    template_name = 'security/login.html'
    authentication_form = LoginEmailForm
    
    
def redirect_based_group(request):
    if not request.user.is_authenticated:
        return redirect('login')

    user = request.user
    groups = user.groups.values_list('name', flat=True)  

    if 'Docente' in groups:
        return redirect('docentes')  
    elif 'Administrativo' in groups:
        return redirect('dashboard_admin')   
    elif 'Alumno' in groups:
        return redirect('dashboard_alumno')  
    else:
        return redirect('home')
    
def logout_view(request):
    logout(request)
    return redirect('login')

@staff_member_required
def download_backup(request):
    """Vista para descargar backup completo del sistema"""
    try:
        zip_buffer, filename = crear_backup_completo()

        response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        messages.success(request, 'Backup generado exitosamente.')
        return response

    except Exception as e:
        messages.error(request, f'Error al generar el backup: {str(e)}')
        return redirect('/admin/')
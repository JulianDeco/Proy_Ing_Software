from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.contrib.auth.views import LoginView
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages

from .utils import group_required
from .forms import LoginEmailForm
from administracion.utils import crear_backup_completo, restaurar_backup

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
    """Vista para descargar backup completo del sistema (opcionalmente encriptado)"""
    try:
        # Obtener contraseña del formulario (si se proporcionó)
        password = request.GET.get('password', '') or request.POST.get('password', '')

        zip_buffer, filename = crear_backup_completo(password if password else None)

        # Determinar el content type según si está encriptado
        if filename.endswith('.enc'):
            content_type = 'application/octet-stream'
            messages.success(request, 'Backup encriptado generado exitosamente. Guarde la contraseña en un lugar seguro.')
        else:
            content_type = 'application/zip'
            messages.success(request, 'Backup generado exitosamente.')

        response = HttpResponse(zip_buffer.getvalue(), content_type=content_type)
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        return response

    except Exception as e:
        messages.error(request, f'Error al generar el backup: {str(e)}')
        return redirect('/admin/')


@staff_member_required
def upload_restore_backup(request):
    """Vista para subir y restaurar un backup del sistema (puede estar encriptado)"""
    if request.method == 'POST':
        if 'backup_file' not in request.FILES:
            messages.error(request, 'No se ha seleccionado ningún archivo.')
            return redirect('/admin/')

        archivo_backup = request.FILES['backup_file']
        password = request.POST.get('restore_password', '')

        # Validar extensión
        if not (archivo_backup.name.endswith('.zip') or archivo_backup.name.endswith('.enc')):
            messages.error(request, 'El archivo debe ser un ZIP o un archivo encriptado (.enc).')
            return redirect('/admin/')

        try:
            success, mensaje = restaurar_backup(archivo_backup, password if password else None)

            if success:
                messages.success(request, mensaje)
            else:
                messages.error(request, mensaje)

        except Exception as e:
            messages.error(request, f'Error inesperado: {str(e)}')

        return redirect('/admin/')

    return redirect('/admin/')

@login_required
def help_view(request):
    return render(request, 'main/help.html')
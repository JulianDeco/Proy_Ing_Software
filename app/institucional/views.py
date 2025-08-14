from datetime import timedelta
from time import localtime
from django.http import JsonResponse
from django.shortcuts import render
from django.contrib.admin.models import LogEntry
from django.contrib.auth.models import Group
from django.db.models import Q

from institucional.forms import UsuarioForm
from institucional.models import Usuario

def home_institucional(request):
    logs = LogEntry.objects.select_related('user', 'content_type').order_by('-action_time')[:10]
    
    user_objects = Usuario.objects.all()
    context = {
        'usuarios': user_objects,
        'logs': logs
    }
    return render(request, 'institucional/institucional.html', context)

def mas_usuarios(request):
    user_objects = Usuario.objects.all()
    grupos = Group.objects.all()
    print(user_objects[0].groups.all())
    
    for usuario in user_objects:
        grupos_usuario = usuario.groups.all()
        # usuarios.group_str = ",".join(str(x) for x in grupos_usuario)
        usuario.group = "".join(str(x) for x in grupos_usuario)
    
    context = {
        'usuarios': user_objects,
        'usuarios_totales': len(user_objects),
    }
    return render(request, 'institucional/nuevos_usuarios.html', context)

def filtro_usuarios(request):
    if request.method != 'GET':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    query = request.GET.get('q', '').strip()
    role = request.GET.get('role', '').strip()
    status_param = request.GET.get('status', '').strip()

    usuarios = Usuario.objects.all()

    if query:
        usuarios = usuarios.filter(email__icontains=query)
    if role:
        usuarios = usuarios.filter(groups__name__iexact=role)
    if status_param:
        if status_param == 'active':
            usuarios = usuarios.filter(habilitado=True)
        elif status_param == 'inactive':
            usuarios = usuarios.filter(habilitado=False)

    data = []
    for u in usuarios:
        grupos_usuario = u.groups.all()
        first_group = grupos_usuario.first().name if grupos_usuario.exists() else ''
        data.append({
            'id': u.id,
            'full_name': u.get_full_name(),
            'email': u.email,
            'group': first_group,
            'is_active': u.habilitado,
            'last_login': (u.last_login-timedelta(hours=3)).strftime("%d/%m/%Y %H:%M") if u.last_login else None,
            'profile_picture': getattr(u, 'profile_picture', None) and u.profile_picture.url or None,
        })

    return JsonResponse({'usuarios': data})
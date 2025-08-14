from django.shortcuts import render
from django.contrib.admin.models import LogEntry

from institucional.models import Usuario

def home_institucional(request):
    logs = LogEntry.objects.select_related('user', 'content_type').order_by('-action_time')[:10]
    
    user_objects = Usuario.objects.all()
    context = {
        'usuarios': user_objects,
        'logs': logs
    }
    return render(request, 'institucional/institucional.html', context)
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required

from main.utils import group_required

@login_required
@group_required('Administrativo')
def home_administracion(request):
    return redirect('/admin/')
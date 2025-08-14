from django import forms
from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError
from django.core.validators import validate_email

class UsuarioForm(forms.Form):
    first_name = forms.CharField(
        label='Nombres',
        max_length=100,
    )
    
    last_name = forms.CharField(
        label='Apellidos',
        max_length=100,
    )
    
    email = forms.EmailField(
        label='Correo Electrónico',
    )
    
    role = forms.ChoiceField(
        label='Rol',
        choices=(('', 'Seleccionar rol...'), ('admin', 'Administrativo'), ('teacher', 'Profesor')),
    )
    
    is_active = forms.ChoiceField(
        label='Estado',
        choices=((1, 'Activo'), (0, 'Inactivo')),
    )
    
    password1 = forms.CharField(
        label='Contraseña',
        min_length=8
    )
    
    password2 = forms.CharField(
        label='Confirmar Contraseña',
    )
    
    profile_picture = forms.ImageField(
        label='Foto de Perfil',
        required=False,
    )
from django import forms
from django.contrib.auth.forms import AuthenticationForm

class LoginEmailForm(AuthenticationForm):
    username = forms.EmailField(label="Correo electrónico")
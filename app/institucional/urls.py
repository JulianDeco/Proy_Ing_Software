from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_institucional, name='home_institucional'),
    path('usuarios', views.mas_usuarios, name='mas_usuarios'),
    path('filtro-usuarios', views.filtro_usuarios, name='filtro_usuarios'),
]
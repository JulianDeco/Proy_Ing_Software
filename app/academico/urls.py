from django.urls import path
from . import views

urlpatterns = [
    path('materias/', views.lista_materias, name='lista_materias'),
]
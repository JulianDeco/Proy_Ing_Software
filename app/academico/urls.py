from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_academico, name='home_academico'),
    path('docentes', views.dashboard_profesores, name='dashboard_profesores'),
    path('asistencia/curso/<int:codigo>', views.asistencia_curso, name='asistencia_curso'),
    path('registrar_asistencia/<int:codigo>', views.registrar_asistencia, name='registrar_asistencia')
]
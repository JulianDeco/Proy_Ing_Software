from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_profesores, name='docentes'),
    path('asistencia/curso/<int:codigo>', views.GestionAsistenciaView.as_view(), name='asistencia_curso'),
    path('calificaciones/<int:codigo>/', views.calificaciones_curso, name='calificaciones_curso'),
    path('crear_evaluacion/<int:codigo>', views.crear_evaluacion, name='crear_evaluacion'),
    path('guardar_calificaciones/<int:codigo>', views.guardar_calificaciones, name='guardar_calificaciones'),
]
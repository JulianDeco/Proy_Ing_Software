from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_profesores, name='docentes'),
    path('asistencia/', views.GestionClasesView.as_view(), name='seleccionar_clase_asistencia'),
    path('asistencia/curso/<int:codigo>', views.GestionAsistenciaView.as_view(), name='asistencia_curso'),
    path('calificaciones/<int:codigo>/', views.calificaciones_curso, name='calificaciones_curso'),
    path('calificaciones/<int:codigo>/crear_calificacion/', views.GestionCalificacionesView.as_view(), name='crear_calificacion'),
    path('guardar_calificaciones/<int:codigo>', views.guardar_calificaciones, name='guardar_calificaciones'),
]
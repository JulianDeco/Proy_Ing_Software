from django.urls import path
from . import views

urlpatterns = [
    path('', views.DashboardProfesoresView.as_view(), name='docentes'),
    path('asistencia/', views.GestionClasesView.as_view(), name='seleccionar_clase_asistencia'),
    path('asistencia/curso/<int:codigo>', views.GestionAsistenciaView.as_view(), name='asistencia_curso'),
    path('calificaciones/<int:codigo>/', views.CalificacionesCursoView.as_view(), name='calificaciones_curso'),
    path('calificaciones/<int:codigo>/crear_calificacion/', views.GestionCalificacionesView.as_view(), name='crear_calificacion'),
]
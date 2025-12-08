from django.urls import path
from . import views

urlpatterns = [
    path('', views.DashboardProfesoresView.as_view(), name='docentes'),
    path('asistencia/', views.GestionClasesView.as_view(), name='seleccionar_clase_asistencia'),
    path('asistencia/curso/<str:codigo>/', views.GestionAsistenciaView.as_view(), name='asistencia_curso'),
    path('calificaciones/<str:codigo>/', views.CalificacionesCursoView.as_view(), name='calificaciones_curso'),
    path('calificaciones/<str:codigo>/crear_calificacion/', views.GestionCalificacionesView.as_view(), name='crear_calificacion'),
    path('calificaciones/editar/<int:id>/', views.EditarCalificacionView.as_view(), name='editar_calificacion'),
    path('comisiones/<str:codigo>/cerrar/', views.CierreCursadaView.as_view(), name='cerrar_cursada'),
    path('mesas-examen/', views.MesasExamenDocenteView.as_view(), name='mesas_examen_docente'),
    path('mesas-examen/<int:mesa_id>/inscriptos/', views.DetalleInscriptosMesaView.as_view(), name='detalle_inscriptos_mesa'),
    path('mesas-examen/<int:mesa_id>/acta-pdf/', views.ActaExamenPDFView.as_view(), name='acta_examen_pdf'),
    path('alumno/<int:alumno_id>/historico-mesas/', views.HistoricoMesasAlumnoView.as_view(), name='historico_mesas_alumno'),
]
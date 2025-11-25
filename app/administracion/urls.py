from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_administracion, name='home_administracion'),
    path('reportes/academico/', views.reporte_academico, name='reporte_academico'),
    path('reportes/academico/pdf/', views.exportar_reporte_pdf, name='exportar_reporte_pdf'),
    path('reportes/academico/excel/', views.exportar_reporte_excel, name='exportar_reporte_excel'),
]
from django.contrib import admin

from administracion.models import Certificacion, PlanEstudio, Reporte

@admin.register(PlanEstudio)
class PlanEstudioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'codigo')
    search_fields = ('nombre', 'codigo')

@admin.register(Reporte)
class ReporteAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'fecha_generacion', 'archivo')
    search_fields = ('titulo',)

@admin.register(Certificacion)
class CertificacionAdmin(admin.ModelAdmin):
    list_display = ('persona', 'tipo', 'fecha_emision', 'generado_por')
    search_fields = ('persona__nombre', 'persona__apellido', 'tipo')
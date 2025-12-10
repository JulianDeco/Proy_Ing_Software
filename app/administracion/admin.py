from django.contrib import admin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils.html import format_html
from django.contrib import messages
from django.urls import path

from administracion.models import Certificado, PlanEstudio, TipoCertificado
from main.utils import crear_contexto_certificado, generar_certificado_pdf

@admin.register(PlanEstudio)
class PlanEstudioAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre')
    search_fields = ('nombre', 'codigo')
    ordering = ('codigo',)
    list_per_page = 50

@admin.register(Certificado)
class CertificadoAdmin(admin.ModelAdmin):
    list_display = ('codigo_verificacion', 'alumno', 'tipo_display', 'fecha_emision', 'generado_por', 'descargar_certificado')
    list_display_links = ('codigo_verificacion', 'alumno')
    list_filter = ('tipo', 'fecha_emision')
    search_fields = ('alumno__nombre', 'alumno__apellido', 'alumno__dni', 'codigo_verificacion')
    ordering = ('-fecha_emision',)
    readonly_fields = ('codigo_verificacion', 'fecha_emision')
    autocomplete_fields = ['alumno', 'generado_por']
    list_select_related = ('alumno', 'generado_por')
    date_hierarchy = 'fecha_emision'
    list_per_page = 50
    save_on_top = True
    empty_value_display = '—'

    fieldsets = (
        ('Información del Certificado', {
            'fields': ('codigo_verificacion', 'alumno', 'tipo')
        }),
        ('Generación', {
            'fields': ('generado_por', 'fecha_emision')
        }),
    )

    def tipo_display(self, obj):
        colors = {
            'ASISTENCIA': '#17a2b8',
            'APROBACION': '#28a745',
            'EXAMEN': '#ffc107',
            'ALUMNO_REGULAR': '#007bff',
            'BUEN_COMPORTAMIENTO': '#6f42c1'
        }
        color = colors.get(obj.tipo, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            color, obj.get_tipo_display()
        )
    tipo_display.short_description = 'Tipo'

    def descargar_certificado(self, obj):
        return format_html(
            '<a class="button" href="/admin/administracion/certificado/{}/download/">📄 Descargar PDF</a>',
            obj.id
        )
    descargar_certificado.short_description = 'Acción'

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('<path:object_id>/download/', self.admin_site.admin_view(self.download_certificado), name='certificado_download'),
        ]
        return custom_urls + urls

    def download_certificado(self, request, object_id):
        from institucional.models import Institucion
        certificado = get_object_or_404(Certificado, id=object_id)
        try:
            institucion = Institucion.objects.first()
            if not institucion:
                return HttpResponse('Error: No hay institución configurada en el sistema.', status=500)

            contexto = crear_contexto_certificado(
                certificado.alumno,
                certificado.get_tipo_display(),
                institucion
            )
            contexto['certificado'] = certificado

            pdf_content = generar_certificado_pdf(contexto)

            response = HttpResponse(pdf_content, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="certificado_{certificado.alumno.dni}_{certificado.tipo}.pdf"'
            return response
        except Exception as e:
            messages.error(request, f'Error al generar el certificado: {str(e)}')
            return HttpResponse(f'Error: {str(e)}', status=500)



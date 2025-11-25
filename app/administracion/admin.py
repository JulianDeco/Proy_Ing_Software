from django.contrib import admin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils.html import format_html
from django.contrib import messages
from django.urls import path

from administracion.models import Certificado, PlanEstudio, Reporte, TipoCertificado, BackupManager
from main.utils import crear_contexto_certificado, generar_certificado_pdf

@admin.register(PlanEstudio)
class PlanEstudioAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre')
    search_fields = ('nombre', 'codigo')
    ordering = ('codigo',)

@admin.register(Reporte)
class ReporteAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'fecha_generacion', 'archivo')
    list_filter = ('fecha_generacion',)
    search_fields = ('titulo',)
    ordering = ('-fecha_generacion',)

@admin.register(Certificado)
class CertificadoAdmin(admin.ModelAdmin):
    list_display = ('codigo_verificacion', 'alumno', 'tipo', 'fecha_emision', 'generado_por', 'descargar_certificado')
    list_filter = ('tipo', 'fecha_emision')
    search_fields = ('alumno__nombre', 'alumno__apellido', 'alumno__dni', 'codigo_verificacion')
    ordering = ('-fecha_emision',)
    readonly_fields = ('codigo_verificacion', 'fecha_emision')

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


@admin.register(BackupManager)
class BackupManagerAdmin(admin.ModelAdmin):
    """
    Administrador personalizado para gestionar backups del sistema
    """

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['title'] = 'Gestión de Backups del Sistema'
        extra_context['has_add_permission'] = False

        return render(request, 'admin/backup_manager.html', extra_context)

from django.http import HttpResponse
from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.utils.html import format_html
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from administracion.models import Certificado, TipoCertificado
from main.utils import crear_contexto_certificado, generar_certificado_pdf
from institucional.models import Institucion, Usuario, Persona, Empleado
from academico.models import Alumno

@admin.register(Institucion)
class InstitucionAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'direccion','nro_telefono','nro_celular','logo')

@admin.register(Usuario)
class UsuarioAdmin(BaseUserAdmin):
    list_display = ('email','empleado', 'habilitado', 'is_staff', 'is_superuser')
    search_fields = ('email',)
    ordering = ('email',)
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Permisos', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'habilitado', 'groups', 'is_staff', 'is_superuser'),
        }),
    )

@admin.register(Empleado)
class EmpleadoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'apellido', 'dni', 'usuario_asociado')
    search_fields = ('nombre', 'apellido', 'dni', 'usuario__email')

    def usuario_asociado(self, obj):
        return obj.usuario.email if obj.usuario else '—'
    usuario_asociado.short_description = 'Usuario'

@admin.register(Alumno)
class AlumnoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'apellido', 'dni', 'promedio', 'estado')
    search_fields = ('nombre', 'apellido', 'dni')
    actions = ['generar_certificado_asistencia', 'generar_certificado_aprobacion']
    
    def nombre_completo(self, obj):
        return f"{obj.nombre} {obj.apellido}"
    nombre_completo.short_description = 'Nombre Completo'
    
    def generar_certificado_asistencia(self, request, queryset):
        return self._generar_certificados(request, queryset, TipoCertificado.ASISTENCIA)
    
    generar_certificado_asistencia.short_description = "Generar certificado de asistencia"
    
    def generar_certificado_aprobacion(self, request, queryset):
        return self._generar_certificados(request, queryset, TipoCertificado.APROBACION)
    
    generar_certificado_aprobacion.short_description = "Generar certificado de aprobación"
    
    def _generar_certificados(self, request, queryset, tipo_certificado):
        try:
            # Para un solo alumno: descargar directamente
            if queryset.count() == 1:
                alumno = queryset.first()
                institucion = Institucion.objects.first()
                contexto = crear_contexto_certificado(alumno, tipo_certificado, institucion)
                
                # Crear registro en base de datos
                certificado = Certificado.objects.create(
                    alumno=alumno,
                    tipo=tipo_certificado,
                    generado_por=request.user
                )
                contexto['certificado'] = certificado
                
                # Generar PDF
                pdf_content = generar_certificado_pdf(contexto)
                
                # Crear respuesta HTTP
                response = HttpResponse(pdf_content, content_type='application/pdf')
                response['Content-Disposition'] = f'attachment; filename="certificado_{alumno.dni}_{tipo_certificado}.pdf"'
                return response
            
            # Para múltiples alumnos: procesar en lote
            else:
                certificados_generados = []
                for alumno in queryset:
                    certificado = Certificado.objects.create(
                        alumno=alumno,
                        tipo=tipo_certificado,
                        generado_por=request.user
                    )
                    certificados_generados.append(certificado)
                
                self.message_user(
                    request, 
                    f"Se generaron {len(certificados_generados)} certificados de {tipo_certificado}. "
                    f"Puede descargarlos individualmente desde los registros de certificados.",
                    messages.SUCCESS
                )
                
        except Exception as e:
            self.message_user(
                request, 
                f"Error al generar certificados: {str(e)}",
                messages.ERROR
            )
    
    def ver_certificados(self, obj):
        count = obj.certificado_set.count()
        url = f"/admin/academico/certificado/?alumno__id__exact={obj.id}"
        return format_html('<a href="{}">{} Certificados</a>', url, count)
    ver_certificados.short_description = 'Certificados'

@admin.register(Certificado)
class CertificadoAdmin(admin.ModelAdmin):
    list_display = ('alumno', 'tipo', 'fecha_emision', 'codigo_verificacion', 'descargar_certificado')
    list_filter = ('tipo', 'fecha_emision')
    search_fields = ('alumno__nombre', 'alumno__apellido', 'codigo_verificacion')
    
    def descargar_certificado(self, obj):
        return format_html(
            '<a href="/admin/academico/certificado/{}/download/">📄 Descargar</a>',
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
        
        certificado = get_object_or_404(Certificado, id=object_id)
        contexto = crear_contexto_certificado(certificado.alumno, certificado.tipo)
        contexto['certificado'] = certificado
        
        pdf_content = generar_certificado_pdf(contexto)
        
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="certificado_{certificado.alumno.dni}_{certificado.tipo}.pdf"'
        return response
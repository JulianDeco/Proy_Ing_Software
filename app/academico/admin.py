from django.contrib import admin
from django.http import HttpResponse
from django.contrib import messages
from django.utils.html import format_html

from academico.models import Alumno, AnioAcademico, Asistencia, CalendarioAcademico, Calificacion, Comision, EstadosAlumno, Materia, InscripcionAlumnoComision
from academico.forms import MateriaAdminForm
from administracion.models import Certificado, TipoCertificado
from institucional.models import Institucion
from main.utils import crear_contexto_certificado, generar_certificado_pdf

@admin.register(Materia)
class MateriaAdmin(admin.ModelAdmin):
    form = MateriaAdminForm
    list_display = ('nombre', 'codigo', 'plan_estudio')
    list_filter = ('plan_estudio',)
    search_fields = ('nombre', 'codigo', 'plan_estudio__nombre')
    filter_horizontal = ('correlativas',)
    

@admin.register(Comision)
class ComisionAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'materia', 'horario_inicio', 'horario_fin', 'turno')
    search_fields = ('codigo', 'materia__nombre')
    
@admin.register(EstadosAlumno)
class EstadosAlumnoAdmin(admin.ModelAdmin):
    list_display = ('descripcion',)
    search_fields = ('descripcion',)
    
@admin.register(InscripcionAlumnoComision)
class InscripcionesAlumnosComisionesAdmin(admin.ModelAdmin):
    list_display = ('alumno','comision',)
    search_fields = ('alumno','comision','creado',)

@admin.register(Calificacion)
class CalificacionAdmin(admin.ModelAdmin):
    list_display = ('alumno_comision', 'tipo' ,'nota',)
    search_fields = ('alumno_comision', 'tipo' ,'nota',)

@admin.register(Asistencia)
class AsistenciaAdmin(admin.ModelAdmin):
    list_display = ('alumno_comision', 'esta_presente', 'fecha_asistencia',)
    list_filter = ('esta_presente', 'fecha_asistencia', 'alumno_comision__comision',)
    search_fields = (
        'alumno_comision__alumno__nombre',
        'alumno_comision__alumno__apellido', 
        'alumno_comision__alumno__dni',
        'alumno_comision__comision__codigo'
    )
    date_hierarchy = 'fecha_asistencia'
    

@admin.register(AnioAcademico)
class AnioAcademicoAdmin(admin.ModelAdmin):
    list_display =('nombre','fecha_inicio', 'fecha_fin' ,'activo') 
    search_fields = ('nombre','fecha_inicio', 'fecha_fin' ,'activo') 

@admin.register(CalendarioAcademico)
class CalendarioAcademico(admin.ModelAdmin):
    list_display = ('anio_academico','fecha','es_dia_clase','descripcion',)
    search_fields= ('anio_academico','fecha','es_dia_clase','descripcion',)

@admin.register(Alumno)
class AlumnoAdmin(admin.ModelAdmin):
    list_display = ('legajo', 'nombre_completo', 'dni', 'email', 'promedio', 'estado')
    search_fields = ('nombre', 'apellido', 'dni', 'legajo', 'email')
    list_filter = ('estado',)
    actions = [
        'generar_certificado_asistencia',
        'generar_certificado_aprobacion',
        'generar_certificado_examen',
        'generar_certificado_alumno_regular',
        'generar_certificado_buen_comportamiento'
    ]

    def nombre_completo(self, obj):
        return f"{obj.nombre} {obj.apellido}"
    nombre_completo.short_description = 'Nombre Completo'

    def generar_certificado_asistencia(self, request, queryset):
        return self._generar_certificados(request, queryset, TipoCertificado.ASISTENCIA)
    generar_certificado_asistencia.short_description = "Generar certificado de asistencia"

    def generar_certificado_aprobacion(self, request, queryset):
        return self._generar_certificados(request, queryset, TipoCertificado.APROBACION)
    generar_certificado_aprobacion.short_description = "Generar certificado de aprobación"

    def generar_certificado_examen(self, request, queryset):
        return self._generar_certificados(request, queryset, TipoCertificado.EXAMEN)
    generar_certificado_examen.short_description = "Generar certificado de examen"

    def generar_certificado_alumno_regular(self, request, queryset):
        return self._generar_certificados(request, queryset, TipoCertificado.ALUMNO_REGULAR)
    generar_certificado_alumno_regular.short_description = "Generar certificado de alumno regular"

    def generar_certificado_buen_comportamiento(self, request, queryset):
        return self._generar_certificados(request, queryset, TipoCertificado.BUEN_COMPORTAMIENTO)
    generar_certificado_buen_comportamiento.short_description = "Generar certificado de buen comportamiento"

    def _generar_certificados(self, request, queryset, tipo_certificado):
        try:
            if queryset.count() == 1:
                alumno = queryset.first()
                institucion = Institucion.objects.first()
                contexto = crear_contexto_certificado(alumno, tipo_certificado, institucion)
                certificado = Certificado.objects.create(
                    alumno=alumno,
                    tipo=tipo_certificado,
                    generado_por=request.user
                )
                contexto['certificado'] = certificado
                pdf_content = generar_certificado_pdf(contexto)
                response = HttpResponse(pdf_content, content_type='application/pdf')
                response['Content-Disposition'] = f'attachment; filename="certificado_{alumno.dni}_{tipo_certificado}.pdf"'
                return response
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
                    f"Puede descargarlos desde el módulo Administración > Certificados.",
                    messages.SUCCESS
                )

        except Exception as e:
            self.message_user(
                request,
                f"Error al generar certificados: {str(e)}",
                messages.ERROR
            )
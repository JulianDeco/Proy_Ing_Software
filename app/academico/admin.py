from django.contrib import admin
from django.http import HttpResponse
from django.contrib import messages
from django.utils.html import format_html

from academico.models import (
    Alumno, AnioAcademico, Asistencia, CalendarioAcademico, Calificacion, Comision,
    EstadosAlumno, Materia, InscripcionAlumnoComision, MesaExamen, InscripcionMesaExamen
)
from academico.forms import (
    MateriaAdminForm, CalificacionAdminForm, InscripcionAlumnoComisionAdminForm,
    InscripcionMesaExamenAdminForm, MesaExamenAdminForm
)
from administracion.models import Certificado, TipoCertificado
from institucional.models import Institucion
from institucional.auditoria import AuditoriaMixin
from main.utils import crear_contexto_certificado, generar_certificado_pdf

@admin.register(Materia)
class MateriaAdmin(admin.ModelAdmin):
    form = MateriaAdminForm
    list_display = ('nombre', 'codigo', 'plan_estudio')
    list_filter = ('plan_estudio',)
    search_fields = ('nombre', 'codigo', 'plan_estudio__nombre')
    autocomplete_fields = ['correlativas']
    list_select_related = ('plan_estudio',)
    list_per_page = 50
    

@admin.register(Comision)
class ComisionAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'materia', 'horario_inicio', 'horario_fin', 'turno', 'estado')
    search_fields = ('codigo', 'materia__nombre', 'materia__codigo')
    list_filter = ('estado', 'turno')
    autocomplete_fields = ['materia']
    list_select_related = ('materia', 'materia__plan_estudio')
    list_per_page = 50
    actions = ['cerrar_comision_action']

    def cerrar_comision_action(self, request, queryset):
        """Acción para cerrar comisiones seleccionadas"""
        from academico.services import ServiciosAcademico

        if queryset.count() > 1:
            self.message_user(request, 'Solo puede cerrar una comisión a la vez.', level='warning')
            return

        comision = queryset.first()

        if comision.estado == 'FINALIZADA':
            self.message_user(request, f'La comisión {comision.codigo} ya está finalizada.', level='warning')
            return

        # Cerrar la comisión
        resultado = ServiciosAcademico.cerrar_comision(comision, request.user)

        if resultado['success']:
            self.message_user(request, resultado['mensaje'], level='success')
        else:
            self.message_user(request, resultado['mensaje'], level='error')

    cerrar_comision_action.short_description = "Cerrar comisión y calcular notas finales"
    
@admin.register(EstadosAlumno)
class EstadosAlumnoAdmin(admin.ModelAdmin):
    list_display = ('descripcion',)
    search_fields = ('descripcion',)
    
@admin.register(InscripcionAlumnoComision)
class InscripcionesAlumnosComisionesAdmin(AuditoriaMixin, admin.ModelAdmin):
    form = InscripcionAlumnoComisionAdminForm
    list_display = ('alumno', 'comision', 'estado_inscripcion', 'nota_final', 'fecha_cierre')
    search_fields = ('alumno__nombre', 'alumno__apellido', 'alumno__dni', 'comision__codigo', 'comision__materia__nombre')
    list_filter = ('estado_inscripcion',)
    readonly_fields = ('nota_final', 'fecha_cierre', 'cerrada_por')
    autocomplete_fields = ['alumno', 'comision']
    list_select_related = ('alumno', 'comision', 'comision__materia', 'cerrada_por')
    list_per_page = 50

@admin.register(Calificacion)
class CalificacionAdmin(AuditoriaMixin, admin.ModelAdmin):
    form = CalificacionAdminForm
    list_display = ('alumno_comision', 'tipo', 'nota', 'fecha_creacion')
    search_fields = ('alumno_comision__alumno__nombre', 'alumno_comision__alumno__apellido', 'alumno_comision__alumno__dni', 'tipo')
    list_filter = ('tipo',)
    autocomplete_fields = ['alumno_comision']
    list_select_related = ('alumno_comision', 'alumno_comision__alumno', 'alumno_comision__comision')
    list_per_page = 50

@admin.register(Asistencia)
class AsistenciaAdmin(admin.ModelAdmin):
    list_display = ('alumno_comision', 'esta_presente', 'fecha_asistencia',)
    list_filter = ('esta_presente', 'fecha_asistencia')
    search_fields = (
        'alumno_comision__alumno__nombre',
        'alumno_comision__alumno__apellido',
        'alumno_comision__alumno__dni',
        'alumno_comision__comision__codigo'
    )
    date_hierarchy = 'fecha_asistencia'
    autocomplete_fields = ['alumno_comision']
    list_select_related = ('alumno_comision', 'alumno_comision__alumno', 'alumno_comision__comision')
    list_per_page = 50
    

@admin.register(AnioAcademico)
class AnioAcademicoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'fecha_inicio', 'fecha_fin', 'activo')
    search_fields = ('nombre',)
    list_filter = ('activo',)
    list_per_page = 25 

@admin.register(CalendarioAcademico)
class CalendarioAcademicoAdmin(admin.ModelAdmin):
    list_display = ('anio_academico', 'fecha', 'es_dia_clase', 'descripcion')
    search_fields = ('descripcion',)
    list_filter = ('es_dia_clase', 'anio_academico')
    autocomplete_fields = ['anio_academico']
    list_select_related = ('anio_academico',)
    date_hierarchy = 'fecha'
    list_per_page = 50

@admin.register(Alumno)
class AlumnoAdmin(AuditoriaMixin, admin.ModelAdmin):
    list_display = ('legajo', 'nombre_completo', 'dni', 'email', 'promedio', 'estado')
    search_fields = ('nombre', 'apellido', 'dni', 'legajo', 'email')
    list_filter = ('estado', 'plan_estudio')
    autocomplete_fields = ['plan_estudio']
    list_select_related = ('plan_estudio', 'estado')
    list_per_page = 50
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


@admin.register(MesaExamen)
class MesaExamenAdmin(AuditoriaMixin, admin.ModelAdmin):
    form = MesaExamenAdminForm
    list_display = ('materia', 'fecha_examen', 'fecha_limite_inscripcion', 'estado', 'inscripciones_count', 'cupos_disponibles')
    list_filter = ('estado', 'anio_academico')
    search_fields = ('materia__nombre', 'materia__codigo', 'fecha_examen', 'anio_academico__nombre')
    autocomplete_fields = ['materia', 'tribunal']
    readonly_fields = ('inscripciones_count', 'cupos_disponibles', 'creado_por', 'fecha_creacion')
    list_select_related = ('materia', 'anio_academico', 'creado_por')
    list_per_page = 50
    actions = ['cerrar_inscripciones', 'finalizar_mesa']

    fieldsets = (
        ('Información Básica', {
            'fields': ('materia', 'anio_academico', 'aula')
        }),
        ('Fechas', {
            'fields': ('fecha_examen', 'fecha_limite_inscripcion')
        }),
        ('Tribunal y Configuración', {
            'fields': ('tribunal', 'cupo_maximo', 'estado')
        }),
        ('Información de Inscripciones', {
            'fields': ('inscripciones_count', 'cupos_disponibles')
        }),
        ('Auditoría', {
            'fields': ('creado_por', 'fecha_creacion'),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        if not change:  # Solo al crear
            obj.creado_por = request.user
        # Llama al mixin de auditoría que a su vez llama a super()
        super().save_model(request, obj, form, change)

    def cerrar_inscripciones(self, request, queryset):
        """Cierra las inscripciones de las mesas seleccionadas"""
        contador = 0
        for mesa in queryset:
            if mesa.estado == 'ABIERTA':
                mesa.estado = 'CERRADA'
                mesa.save()
                contador += 1

        self.message_user(
            request,
            f'Se cerraron las inscripciones de {contador} mesa(s).',
            messages.SUCCESS
        )

    cerrar_inscripciones.short_description = "Cerrar inscripciones"

    def finalizar_mesa(self, request, queryset):
        """Finaliza las mesas de examen seleccionadas"""
        from academico.services import ServiciosAcademico

        if queryset.count() > 1:
            self.message_user(request, 'Solo puede finalizar una mesa a la vez.', messages.WARNING)
            return

        mesa = queryset.first()

        resultado = ServiciosAcademico.finalizar_mesa_examen(mesa, request.user)

        mensaje = (
            f"Mesa finalizada. "
            f"Inscriptos: {resultado['total_inscriptos']} | "
            f"Aprobados: {resultado['aprobados']} | "
            f"Desaprobados: {resultado['desaprobados']} | "
            f"Ausentes: {resultado['ausentes']}"
        )

        self.message_user(request, mensaje, messages.SUCCESS)

    finalizar_mesa.short_description = "Finalizar mesa de examen"


@admin.register(InscripcionMesaExamen)
class InscripcionMesaExamenAdmin(AuditoriaMixin, admin.ModelAdmin):
    form = InscripcionMesaExamenAdminForm
    list_display = ('alumno', 'mesa_examen', 'condicion', 'estado_inscripcion', 'nota_examen', 'fecha_inscripcion')
    list_filter = ('condicion', 'estado_inscripcion')
    search_fields = ('alumno__nombre', 'alumno__apellido', 'alumno__dni', 'mesa_examen__materia__nombre')
    readonly_fields = ('condicion', 'fecha_inscripcion')
    autocomplete_fields = ['alumno', 'mesa_examen']
    list_select_related = ('alumno', 'mesa_examen', 'mesa_examen__materia', 'mesa_examen__anio_academico')
    list_per_page = 50

    fieldsets = (
        ('Información de Inscripción', {
            'fields': ('mesa_examen', 'alumno', 'condicion', 'fecha_inscripcion')
        }),
        ('Resultado del Examen', {
            'fields': ('estado_inscripcion', 'nota_examen', 'observaciones')
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        """Si ya está inscripto, no permitir cambiar mesa ni alumno"""
        if obj:  # Editando
            return self.readonly_fields + ('mesa_examen', 'alumno')
        return self.readonly_fields
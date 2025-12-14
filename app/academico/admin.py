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
    save_on_top = True

    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre', 'codigo', 'plan_estudio')
        }),
        ('Correlativas', {
            'fields': ('correlativas',),
            'description': 'Materias que deben cursarse antes de esta materia'
        }),
    )
    

@admin.register(Comision)
class ComisionAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'materia', 'docente', 'anio_academico', 'horario_inicio', 'turno', 'ocupacion_display', 'estado_display')
    list_display_links = ('codigo', 'materia')
    search_fields = ('codigo', 'materia__nombre', 'materia__codigo', 'docente__apellido', 'docente__nombre')
    list_filter = ('estado', 'turno', 'anio_academico', 'dia_cursado')
    autocomplete_fields = ['materia', 'docente', 'anio_academico']
    list_select_related = ('materia', 'materia__plan_estudio', 'docente', 'anio_academico')
    list_per_page = 50
    save_on_top = True
    actions = ['cerrar_comision_action']

    fieldsets = (
        ('Información Básica', {
            'fields': ('codigo', 'materia', 'docente', 'anio_academico')
        }),
        ('Ubicación y Cupos', {
            'fields': ('aula', 'cupo_maximo')
        }),
        ('Horarios', {
            'fields': ('dia_cursado', 'horario_inicio', 'horario_fin', 'turno')
        }),
        ('Estado', {
            'fields': ('estado',)
        }),
    )

    def ocupacion_display(self, obj):
        # Nota: Esto puede generar N+1 queries si no se optimiza, pero para admin básico está bien.
        # Una optimización sería usar annotate en get_queryset.
        inscriptos = InscripcionAlumnoComision.objects.filter(comision=obj).count()
        return f"{inscriptos} / {obj.cupo_maximo}"
    ocupacion_display.short_description = 'Cupo (Ins/Max)'

    def estado_display(self, obj):
        colors = {
            'ABIERTA': '#28a745',
            'FINALIZADA': '#6c757d',
            'CERRADA': '#dc3545'
        }
        color = colors.get(obj.estado, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            color, obj.get_estado_display()
        )
    estado_display.short_description = 'Estado'

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
    list_display = ('alumno', 'comision', 'condicion_display', 'nota_cursada', 'estado_inscripcion_display', 'nota_final')
    list_display_links = ('alumno', 'comision')
    search_fields = ('alumno__nombre', 'alumno__apellido', 'alumno__dni', 'comision__codigo', 'comision__materia__nombre')
    list_filter = ('estado_inscripcion', 'condicion', 'comision__anio_academico')
    readonly_fields = ('nota_final', 'fecha_cierre', 'cerrada_por', 'fecha_regularizacion')
    autocomplete_fields = ['alumno', 'comision']
    list_select_related = ('alumno', 'comision', 'comision__materia', 'cerrada_por')
    list_per_page = 50
    save_on_top = True
    empty_value_display = '—'

    def condicion_display(self, obj):
        colors = {
            'REGULAR': '#007bff', # Azul
            'LIBRE': '#ffc107',   # Amarillo
            'CURSANDO': '#17a2b8' # Cyan
        }
        color = colors.get(obj.condicion, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            color, obj.get_condicion_display()
        )
    condicion_display.short_description = 'Condición Cursada'

    def estado_inscripcion_display(self, obj):
        colors = {
            'ACTIVA': '#28a745',
            'CERRADA': '#6c757d',
            'APROBADA': '#007bff',
            'DESAPROBADA': '#dc3545'
        }
        color = colors.get(obj.estado_inscripcion, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            color, obj.get_estado_inscripcion_display()
        )
    estado_inscripcion_display.short_description = 'Estado'

@admin.register(Calificacion)
class CalificacionAdmin(AuditoriaMixin, admin.ModelAdmin):
    form = CalificacionAdminForm
    list_display = ('alumno_comision', 'tipo', 'numero', 'nota', 'fecha_creacion')
    search_fields = ('alumno_comision__alumno__nombre', 'alumno_comision__alumno__apellido', 'alumno_comision__alumno__dni', 'tipo')
    list_filter = ('tipo', 'fecha_creacion')
    autocomplete_fields = ['alumno_comision']
    list_select_related = ('alumno_comision', 'alumno_comision__alumno', 'alumno_comision__comision')
    list_per_page = 50

@admin.register(Asistencia)
class AsistenciaAdmin(admin.ModelAdmin):
    list_display = ('alumno_comision', 'fecha_asistencia', 'esta_presente_display')
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

    def esta_presente_display(self, obj):
        if obj.esta_presente:
            return format_html('<span style="color: green; font-size: 18px;">✓</span> Presente')
        return format_html('<span style="color: red; font-size: 18px;">✗</span> Ausente')
    esta_presente_display.short_description = 'Asistencia'
    

@admin.register(AnioAcademico)
class AnioAcademicoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'fecha_inicio', 'fecha_fin', 'cierre_cursada_habilitado', 'activo_display')
    search_fields = ('nombre',)
    list_filter = ('activo', 'cierre_cursada_habilitado')
    list_per_page = 25

    def activo_display(self, obj):
        if obj.activo:
            return format_html('<span style="color: green; font-size: 16px;">✓</span> Activo')
        return format_html('<span style="color: gray; font-size: 16px;">✗</span> Inactivo')
    activo_display.short_description = 'Estado' 

@admin.register(CalendarioAcademico)
class CalendarioAcademicoAdmin(admin.ModelAdmin):
    list_display = ('anio_academico', 'fecha', 'es_dia_clase_display', 'descripcion')
    search_fields = ('descripcion',)
    list_filter = ('es_dia_clase', 'anio_academico')
    autocomplete_fields = ['anio_academico']
    list_select_related = ('anio_academico',)
    date_hierarchy = 'fecha'
    list_per_page = 50
    empty_value_display = '—'

    def es_dia_clase_display(self, obj):
        if obj.es_dia_clase:
            return format_html('<span style="color: green; font-size: 16px;">✓</span> Día de clase')
        return format_html('<span style="color: #dc3545; font-size: 16px;">✗</span> No hay clase')
    es_dia_clase_display.short_description = 'Tipo de día'

@admin.register(Alumno)
class AlumnoAdmin(AuditoriaMixin, admin.ModelAdmin):
    list_display = ('legajo', 'nombre_completo', 'dni', 'email', 'promedio', 'estado')
    list_display_links = ('legajo', 'nombre_completo')
    search_fields = ('nombre', 'apellido', 'dni', 'legajo', 'email')
    list_filter = ('estado', 'plan_estudio')
    autocomplete_fields = ['plan_estudio']
    list_select_related = ('plan_estudio', 'estado')
    list_per_page = 50
    save_on_top = True
    empty_value_display = '—'
    actions = [
        'generar_certificado_asistencia',
        'generar_certificado_aprobacion',
        'generar_certificado_examen',
        'generar_certificado_alumno_regular',
        'generar_certificado_buen_comportamiento'
    ]

    fieldsets = (
        ('Datos Personales', {
            'fields': ('nombre', 'apellido', 'dni', 'fecha_nacimiento')
        }),
        ('Datos Académicos', {
            'fields': ('legajo', 'plan_estudio', 'estado', 'promedio')
        }),
        ('Contacto', {
            'fields': ('email', 'telefono', 'domicilio')
        }),
    )

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


from django.urls import path, reverse
from django.utils.safestring import mark_safe
from academico.views import CargarNotasMesaAdminView

@admin.register(MesaExamen)
class MesaExamenAdmin(AuditoriaMixin, admin.ModelAdmin):
    form = MesaExamenAdminForm
    list_display = ('materia', 'fecha_examen', 'fecha_limite_inscripcion', 'estado_display', 'inscripciones_count', 'cupos_disponibles', 'acciones_custom')
    list_display_links = ('materia', 'fecha_examen')
    list_filter = ('estado', 'anio_academico')
    search_fields = ('materia__nombre', 'materia__codigo', 'fecha_examen', 'anio_academico__nombre')
    autocomplete_fields = ['materia', 'tribunal']
    readonly_fields = ('inscripciones_count', 'cupos_disponibles', 'creado_por', 'fecha_creacion')
    list_select_related = ('materia', 'anio_academico', 'creado_por')
    list_per_page = 50
    save_on_top = True
    empty_value_display = '—'
    actions = ['cerrar_inscripciones', 'finalizar_mesa']

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:mesa_id>/cargar-notas/',
                self.admin_site.admin_view(CargarNotasMesaAdminView.as_view()),
                name='admin_cargar_notas_mesa',
            ),
        ]
        return custom_urls + urls

    def acciones_custom(self, obj):
        if obj.estado != 'FINALIZADA':
            url = reverse('admin:admin_cargar_notas_mesa', args=[obj.id])
            return mark_safe(f'<a class="button" href="{url}" style="background-color: #28a745; color: white;">Cargar Notas</a>')
        return "—"
    acciones_custom.short_description = 'Acciones'
    acciones_custom.allow_tags = True

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

    def estado_display(self, obj):
        colors = {
            'ABIERTA': '#28a745',
            'CERRADA': '#ffc107',
            'FINALIZADA': '#6c757d'
        }
        color = colors.get(obj.estado, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            color, obj.get_estado_display()
        )
    estado_display.short_description = 'Estado'

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
    list_display = ('alumno', 'mesa_examen', 'condicion_display', 'estado_inscripcion_mesa_display', 'nota_examen', 'fecha_inscripcion')
    list_display_links = ('alumno', 'mesa_examen')
    list_filter = ('condicion', 'estado_inscripcion')
    search_fields = ('alumno__nombre', 'alumno__apellido', 'alumno__dni', 'mesa_examen__materia__nombre')
    readonly_fields = ('condicion', 'fecha_inscripcion')
    autocomplete_fields = ['alumno', 'mesa_examen']
    list_select_related = ('alumno', 'mesa_examen', 'mesa_examen__materia', 'mesa_examen__anio_academico')
    list_per_page = 50
    save_on_top = True
    empty_value_display = '—'

    fieldsets = (
        ('Información de Inscripción', {
            'fields': ('mesa_examen', 'alumno', 'condicion', 'fecha_inscripcion')
        }),
        ('Resultado del Examen', {
            'fields': ('estado_inscripcion', 'nota_examen', 'observaciones')
        }),
    )

    def condicion_display(self, obj):
        colors = {
            'REGULAR': '#007bff',
            'LIBRE': '#ffc107'
        }
        color = colors.get(obj.condicion, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            color, obj.get_condicion_display()
        )
    condicion_display.short_description = 'Condición'

    def estado_inscripcion_mesa_display(self, obj):
        colors = {
            'INSCRIPTO': '#28a745',
            'APROBADO': '#007bff',
            'DESAPROBADO': '#dc3545',
            'AUSENTE': '#6c757d'
        }
        color = colors.get(obj.estado_inscripcion, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            color, obj.get_estado_inscripcion_display()
        )
    estado_inscripcion_mesa_display.short_description = 'Estado'

    def get_readonly_fields(self, request, obj=None):
        """Si ya está inscripto, no permitir cambiar mesa ni alumno"""
        if obj:  # Editando
            return self.readonly_fields + ('mesa_examen', 'alumno')
        return self.readonly_fields
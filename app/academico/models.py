import datetime
from django.db import models, transaction
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings

from administracion.models import PlanEstudio
from institucional.models import Persona

class Materia(models.Model):
    nombre = models.CharField(max_length=100)
    codigo = models.CharField(max_length=20)
    plan_estudio = models.ForeignKey(PlanEstudio, on_delete=models.CASCADE)
    descripcion = models.TextField(blank=True, null=True)
    correlativas = models.ManyToManyField('self', blank=True, symmetrical=False,)

    class Meta:
        db_table = 'academico_materias'
        verbose_name = 'Materia'
        verbose_name_plural = 'Materias'
        unique_together = ('codigo', 'plan_estudio')

    def __str__(self):
        return f"{self.nombre} ({self.codigo})"

class Turno(models.TextChoices):
    MANANA = 'mañana', 'Mañana'
    TARDE = 'tarde', 'Tarde'
    NOCHE = 'noche', 'Noche'


class Dia(models.IntegerChoices):
    LUNES = 1, 'Lunes'
    MARTES = 2, 'Martes'
    MIERCOLES = 3, 'Miércoles'
    JUEVES = 4, 'Jueves'
    VIERNES = 5, 'Viernes'
    SABADO = 6, 'Sábado'
class EstadoComision(models.TextChoices):
    EN_CURSO = 'EN_CURSO', 'En curso'
    FINALIZADA = 'FINALIZADA', 'Finalizada'

class AnioAcademico(models.Model):
    nombre = models.CharField(max_length=50)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    activo = models.BooleanField(default=False)
    
    # Configuración de Cierre de Cursada
    nota_aprobacion = models.DecimalField(max_digits=4, decimal_places=2, default=6.0)
    porcentaje_asistencia_req = models.PositiveIntegerField(default=75, help_text="Porcentaje mínimo de asistencia para regularizar")
    cierre_cursada_habilitado = models.BooleanField(default=False, help_text="Habilita a los docentes para cerrar notas de cursada")
    fecha_limite_cierre = models.DateField(null=True, blank=True, help_text="Fecha límite para cierre de notas")
    
    class Meta:
        verbose_name = 'Año Académico'
        verbose_name_plural = 'Años Académicos'
    
    def __str__(self):
        return f"{self.nombre} ({self.fecha_inicio} - {self.fecha_fin})"
    
    def clean(self):
        if self.fecha_fin <= self.fecha_inicio:
            raise ValidationError("La fecha de fin debe ser mayor a la fecha de inicio.")

class Comision(models.Model):
    codigo = models.CharField(max_length=20, db_index=True)  # Índice para búsquedas por código
    horario_inicio = models.TimeField()
    horario_fin = models.TimeField()
    dia_cursado = models.IntegerField(choices=Dia.choices, db_index=True)  # Índice para filtrar clases de hoy
    turno = models.CharField(max_length=50, choices=Turno.choices)
    docente = models.ForeignKey('institucional.Persona', on_delete=models.SET_NULL, null=True)
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE)
    aula = models.CharField(max_length=50, blank=True, null=True)
    cupo_maximo = models.PositiveIntegerField(default=30)
    estado = models.CharField(max_length=20, choices=EstadoComision.choices, db_index=True)  # Índice para filtrar por estado
    anio_academico = models.ForeignKey(AnioAcademico, on_delete=models.CASCADE, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['docente', 'estado'], name='comision_docente_estado_idx'),
            models.Index(fields=['dia_cursado', 'estado'], name='comision_dia_estado_idx'),
        ]

    def __str__(self):
        return f'{self.codigo} - {self.materia} - {self.turno}'

class EstadosAlumno(models.Model):
    descripcion = models.CharField(max_length=100)

    class Meta:
        verbose_name = 'Estado del Alumno'
        verbose_name_plural = 'Estados de Alumnos'

    def __str__(self):
        return self.descripcion

class Alumno(Persona):
    promedio = models.DecimalField(decimal_places=2, max_digits=4, null=True, blank=True)
    estado = models.ForeignKey(EstadosAlumno, on_delete=models.SET_NULL, null=True, blank=True)
    legajo = models.CharField(max_length=20, unique=True, null=True, blank=True)
    plan_estudio = models.ForeignKey('administracion.PlanEstudio', on_delete=models.SET_NULL, null=True, blank=True, related_name='alumnos')
    fecha_nacimiento = models.DateField(null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    telefono = models.CharField(max_length=20, null=True, blank=True)
    domicilio = models.CharField(max_length=200, null=True, blank=True)

    class Meta:
        db_table = 'institucional_alumnos'
        verbose_name = 'Alumno'
        verbose_name_plural = 'Alumnos'

    @property
    def get_full_name(self):
        return f"{self.nombre} {self.apellido}"

    def __str__(self):
        return f"{self.dni} - {self.nombre} {self.apellido}"

    def save(self, *args, **kwargs):
        # Generar legajo automáticamente si no tiene
        if not self.legajo:
            self.legajo = self._generar_legajo()
        super().save(*args, **kwargs)

    def _generar_legajo(self):
        """
        Genera un legajo único con formato: AÑO + NÚMERO SECUENCIAL
        Ejemplo: 2025-00001, 2025-00002, etc.
        """
        anio_actual = datetime.datetime.now().year
        prefijo = str(anio_actual)

        # Buscar el último legajo del año actual
        ultimo_alumno = Alumno.objects.filter(
            legajo__startswith=prefijo
        ).order_by('-legajo').first()

        if ultimo_alumno and ultimo_alumno.legajo:
            try:
                # Extraer el número secuencial del último legajo
                ultimo_numero = int(ultimo_alumno.legajo.split('-')[1])
                nuevo_numero = ultimo_numero + 1
            except (ValueError, IndexError):
                nuevo_numero = 1
        else:
            nuevo_numero = 1

        return f"{prefijo}-{nuevo_numero:05d}"

class EstadoMateria(models.TextChoices):
    CURSANDO = 'CURSANDO', 'Cursando'
    REGULAR = 'REGULAR', 'Regular'
    LIBRE = 'LIBRE', 'Libre'
    APROBADA = 'APROBADA', 'Aprobada'
    DESAPROBADA = 'DESAPROBADA', 'Desaprobada'

class CondicionInscripcion(models.TextChoices):
    CURSANDO = 'CURSANDO', 'Cursando'
    REGULAR = 'REGULAR', 'Regular'
    LIBRE = 'LIBRE', 'Libre'

class InscripcionAlumnoComision(models.Model):
    alumno = models.ForeignKey(Alumno, on_delete=models.CASCADE)
    comision = models.ForeignKey(Comision, on_delete=models.CASCADE)
    creado = models.DateTimeField(auto_now_add=True)
    
    # Nuevo campo para el estado de la cursada
    condicion = models.CharField(
        max_length=20,
        choices=CondicionInscripcion.choices,
        default=CondicionInscripcion.CURSANDO
    )
    nota_cursada = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Promedio obtenido en la cursada (parciales)'
    )
    fecha_regularizacion = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Fecha en que se determinó la condición (Regular/Libre)'
    )

    estado_inscripcion = models.CharField(
        max_length=20,
        choices=EstadoMateria.choices,
        default='CURSANDO'
    )

    # Campos para cierre de materia
    nota_final = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Nota final calculada al cerrar la materia'
    )
    fecha_cierre = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Fecha en que se cerró la materia'
    )
    cerrada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cierres_realizados',
        help_text='Usuario que realizó el cierre'
    )

    class Meta:
        db_table = 'institucional_inscripciones_alumnos_comisiones'
        verbose_name = 'Inscripción del alumno en comisiones'
        verbose_name_plural = 'Inscripciones de alumnos en comisiones'
        unique_together = ('alumno', 'comision')

    def __str__(self):
        return f"{self.alumno.nombre} {self.alumno.apellido} - {self.comision.codigo}"

    def clean(self):
        """Validar reglas de negocio antes de guardar"""
        super().clean()

        # Verificar si la comisión está asignada antes de acceder a ella
        try:
            comision = self.comision
        except ObjectDoesNotExist:
            return  # No se puede validar si falta la comisión

        # Validar capacidad máxima de la comisión
        if comision.cupo_maximo:
            inscriptos_actuales = InscripcionAlumnoComision.objects.filter(
                comision=comision
            ).count()

            # Si es una nueva inscripción (no tiene pk)
            if not self.pk and inscriptos_actuales >= comision.cupo_maximo:
                raise ValidationError(
                    f'La comisión {comision.codigo} ha alcanzado su capacidad máxima '
                    f'de {comision.cupo_maximo} estudiantes.'
                )

        # Validar que el alumno haya aprobado las materias correlativas
        materia = comision.materia
        correlativas = materia.correlativas.all()

        if correlativas.exists():
            for correlativa in correlativas:
                # Buscar si el alumno tiene aprobada la correlativa
                aprobada = InscripcionAlumnoComision.objects.filter(
                    alumno=self.alumno,
                    comision__materia=correlativa,
                    estado_inscripcion='APROBADA'
                ).exists()

                if not aprobada:
                    raise ValidationError(
                        f'El alumno debe aprobar la materia correlativa "{correlativa.nombre}" '
                        f'antes de inscribirse en "{materia.nombre}".'
                    )
    
    def crear_asistencias_automaticas(self):
        comision = self.comision
        dias_clase = CalendarioAcademico.objects.filter(
            anio_academico=comision.anio_academico,
            fecha__week_day=comision.dia_cursado + 1,
            es_dia_clase=True,
            fecha__gte=comision.anio_academico.fecha_inicio,
            fecha__lte=comision.anio_academico.fecha_fin
        )
        
        for dia_clase in dias_clase:
            Asistencia.objects.get_or_create(
                alumno_comision=self,
                fecha_asistencia=dia_clase.fecha,
                defaults={'esta_presente': False}
            )
        
        return dias_clase.count()

@receiver(post_save, sender=InscripcionAlumnoComision)
@transaction.atomic
def crear_asistencias_al_inscribir(sender, instance, created, **kwargs):
    if created:
        cantidad_creada = instance.crear_asistencias_automaticas()

class TipoCalificacion(models.TextChoices):
    PARCIAL = 'PARCIAL', 'Parcial'
    TRABAJO_PRACTICO = 'TP', 'Trabajo Práctico'
    FINAL = 'FINAL', 'Final'
    CONCEPTO = 'CONCEPTO', 'Concepto'
    
class Calificacion(models.Model):
    alumno_comision = models.ForeignKey(InscripcionAlumnoComision, on_delete=models.CASCADE, related_name='calificaciones')
    tipo = models.CharField(max_length=20, choices=TipoCalificacion.choices, db_index=True)
    numero = models.PositiveIntegerField(default=1, verbose_name="Número")
    nota = models.DecimalField(max_digits=4, decimal_places=2)
    fecha_creacion = models.DateTimeField(db_index=True)
    dvh = models.CharField(max_length=255, blank=True, null=True, editable=False)

    class Meta:
        unique_together = ('alumno_comision', 'tipo', 'numero')
        verbose_name = 'Calificación'
        verbose_name_plural = 'Calificaciones'
        indexes = [
            models.Index(fields=['alumno_comision', 'tipo'], name='calif_alumno_tipo_idx'),
            models.Index(fields=['fecha_creacion'], name='calif_fecha_idx'),
        ]

    def __str__(self):
        return f"{self.alumno_comision.alumno} - {self.tipo}: {self.nota}"

    def clean(self):
        """Validaciones de calificación"""
        super().clean()

        # Validar rango de nota (0-10)
        if self.nota is not None:
            if self.nota < 0 or self.nota > 10:
                raise ValidationError({
                    'nota': 'La nota debe estar entre 0 y 10.'
                })

        # Validar que la comisión no esté finalizada (excepto para notas finales)
        if self.alumno_comision and self.alumno_comision.comision:
            if self.alumno_comision.comision.estado == EstadoComision.FINALIZADA:
                if self.tipo != TipoCalificacion.FINAL:
                    raise ValidationError(
                        'No se pueden agregar calificaciones a una comisión finalizada.'
                    )

@receiver(models.signals.pre_save, sender=Calificacion)
def calcular_dvh_calificacion(sender, instance, **kwargs):
    """Calcula el DVH antes de guardar"""
    from institucional.digitos_verificadores import GestorDigitosVerificadores
    campos_criticos = ['nota', 'tipo', 'numero', 'fecha_creacion']
    instance.dvh = GestorDigitosVerificadores.calcular_dvh(instance, campos_criticos)

@receiver(models.signals.post_save, sender=Calificacion)
def actualizar_dvv_calificacion(sender, instance, **kwargs):
    """Actualiza el DVV de la tabla después de guardar"""
    from institucional.digitos_verificadores import GestorDigitosVerificadores
    GestorDigitosVerificadores.actualizar_dvv('Calificacion', 'academico')
    
class Asistencia(models.Model):
    alumno_comision = models.ForeignKey(InscripcionAlumnoComision, on_delete=models.CASCADE, related_name='asistencias')
    esta_presente = models.BooleanField(default=False)
    fecha_asistencia = models.DateField(db_index=True)

    class Meta:
        verbose_name = 'Asistencia'
        verbose_name_plural = 'Asistencias'
        unique_together = ('alumno_comision', 'fecha_asistencia')
        indexes = [
            models.Index(fields=['alumno_comision', 'fecha_asistencia'], name='asist_alumno_fecha_idx'),
            models.Index(fields=['fecha_asistencia', 'esta_presente'], name='asist_fecha_presente_idx'),
        ]

    def __str__(self):
        if self.esta_presente:
            return f"{self.alumno_comision.alumno} - Presente - {self.fecha_asistencia}"
        else:
            return f"{self.alumno_comision.alumno} - Ausente - {self.fecha_asistencia}"


class EstadoMesaExamen(models.TextChoices):
    ABIERTA = 'ABIERTA', 'Abierta para inscripciones'
    CERRADA = 'CERRADA', 'Cerrada (no acepta más inscripciones)'
    FINALIZADA = 'FINALIZADA', 'Finalizada (examen tomado)'


class MesaExamen(models.Model):
    """
    Representa una mesa de examen para una materia específica.
    Los administrativos crean las mesas y los alumnos se inscriben según su condición.
    """
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE, related_name='mesas_examen')
    anio_academico = models.ForeignKey(AnioAcademico, on_delete=models.CASCADE)
    fecha_examen = models.DateTimeField(
        help_text='Fecha y hora del examen'
    )
    fecha_limite_inscripcion = models.DateTimeField(
        help_text='Fecha límite para inscribirse a la mesa'
    )
    tribunal = models.ManyToManyField(
        'institucional.Persona',
        related_name='tribunales_examen',
        help_text='Docentes que conforman el tribunal',
        limit_choices_to={'empleado__usuario__groups__name': 'Docente'}
    )
    aula = models.CharField(max_length=50, blank=True, null=True)
    estado = models.CharField(
        max_length=20,
        choices=EstadoMesaExamen.choices,
        default=EstadoMesaExamen.ABIERTA
    )
    cupo_maximo = models.PositiveIntegerField(
        default=50,
        help_text='Cantidad máxima de alumnos que pueden rendir'
    )
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='mesas_creadas'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'academico_mesas_examen'
        verbose_name = 'Mesa de Examen'
        verbose_name_plural = 'Mesas de Examen'
        ordering = ['-fecha_examen']
        indexes = [
            models.Index(fields=['materia', 'fecha_examen'], name='mesa_materia_fecha_idx'),
            models.Index(fields=['estado', 'fecha_examen'], name='mesa_estado_fecha_idx'),
        ]

    def __str__(self):
        return f"{self.materia.nombre} - {self.fecha_examen.strftime('%d/%m/%Y %H:%M')}"

    def clean(self):
        """Validaciones de negocio"""
        from django.utils import timezone

        if self.fecha_limite_inscripcion >= self.fecha_examen:
            raise ValidationError(
                'La fecha límite de inscripción debe ser anterior a la fecha del examen.'
            )

        if self.fecha_examen < timezone.now():
            raise ValidationError(
                'No se puede crear una mesa de examen con fecha pasada.'
            )

    @property
    def inscripciones_count(self):
        """Cantidad de alumnos inscriptos"""
        return self.inscripciones_mesa.filter(estado_inscripcion='INSCRIPTO').count()

    @property
    def cupos_disponibles(self):
        """Cupos disponibles"""
        return self.cupo_maximo - self.inscripciones_count

    @property
    def puede_inscribirse(self):
        """Verifica si la mesa acepta inscripciones"""
        from django.utils import timezone
        return (
            self.estado == EstadoMesaExamen.ABIERTA and
            timezone.now() < self.fecha_limite_inscripcion and
            self.cupos_disponibles > 0
        )


class CondicionAlumnoMesa(models.TextChoices):
    """
    Condición con la que el alumno se presenta al examen
    """
    REGULAR = 'REGULAR', 'Regular (aprobó cursada)'
    LIBRE = 'LIBRE', 'Libre (no aprobó cursada o perdió regularidad)'


class EstadoInscripcionMesa(models.TextChoices):
    INSCRIPTO = 'INSCRIPTO', 'Inscripto'
    AUSENTE = 'AUSENTE', 'Ausente'
    APROBADO = 'APROBADO', 'Aprobado'
    DESAPROBADO = 'DESAPROBADO', 'Desaprobado'


class InscripcionMesaExamen(models.Model):
    """
    Inscripción de un alumno a una mesa de examen.
    """
    mesa_examen = models.ForeignKey(
        MesaExamen,
        on_delete=models.CASCADE,
        related_name='inscripciones_mesa'
    )
    alumno = models.ForeignKey(Alumno, on_delete=models.CASCADE)
    condicion = models.CharField(
        max_length=20,
        choices=CondicionAlumnoMesa.choices,
        help_text='Condición con la que rinde (Regular o Libre)'
    )
    estado_inscripcion = models.CharField(
        max_length=20,
        choices=EstadoInscripcionMesa.choices,
        default=EstadoInscripcionMesa.INSCRIPTO
    )
    nota_examen = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Nota del examen final'
    )
    fecha_inscripcion = models.DateTimeField(auto_now_add=True)
    observaciones = models.TextField(blank=True, null=True)
    dvh = models.CharField(max_length=255, blank=True, null=True, editable=False)

    class Meta:
        db_table = 'academico_inscripciones_mesa_examen'
        verbose_name = 'Inscripción a Mesa de Examen'
        verbose_name_plural = 'Inscripciones a Mesas de Examen'
        unique_together = ('mesa_examen', 'alumno')
        ordering = ['-fecha_inscripcion']
        indexes = [
            models.Index(fields=['mesa_examen', 'alumno'], name='insc_mesa_alumno_idx'),
            models.Index(fields=['estado_inscripcion'], name='insc_mesa_estado_idx'),
        ]

    def __str__(self):
        return f"{self.alumno} - {self.mesa_examen.materia.nombre} ({self.condicion})"

    def clean(self):
        """Validaciones de inscripción"""
        from django.utils import timezone
        from academico.models import CondicionInscripcion # Importar la nueva CondicionInscripcion

        # Validar nota de examen si se proporciona
        if self.nota_examen is not None:
            if self.nota_examen < 0 or self.nota_examen > 10:
                raise ValidationError({
                    'nota_examen': 'La nota debe estar entre 0 y 10.'
                })

        # Solo validar inscripción si es nueva (no tiene pk) o si no está siendo editada para cargar nota
        if not self.pk:
            # Validar que la mesa esté abierta
            if not self.mesa_examen.puede_inscribirse:
                raise ValidationError('Esta mesa no acepta inscripciones.')

            # Validar cupo
            if self.mesa_examen.cupos_disponibles <= 0:
                raise ValidationError('No hay cupos disponibles en esta mesa.')

            # Validar que el alumno tenga cursada para esta materia
            cursada = InscripcionAlumnoComision.objects.filter(
                alumno=self.alumno,
                comision__materia=self.mesa_examen.materia
            ).first()

            if not cursada:
                raise ValidationError(
                    f'El alumno no tiene cursada registrada para {self.mesa_examen.materia.nombre}.'
                )

            # Determinar automáticamente la condición según el estado de la cursada
            if cursada.estado_inscripcion == EstadoMateria.APROBADA: # Estado final de la MATERIA
                raise ValidationError(
                    'El alumno ya aprobó esta materia y no puede inscribirse al examen.'
                )
            elif cursada.condicion == CondicionInscripcion.REGULAR: # Estado de la CURSADA
                self.condicion = CondicionAlumnoMesa.REGULAR
            else: # Condicion CURSANDO o LIBRE para la cursada
                self.condicion = CondicionAlumnoMesa.LIBRE

@receiver(models.signals.pre_save, sender=InscripcionMesaExamen)
def calcular_dvh_inscripcion_mesa(sender, instance, **kwargs):
    """Calcula el DVH antes de guardar"""
    from institucional.digitos_verificadores import GestorDigitosVerificadores
    campos_criticos = ['nota_examen', 'condicion', 'estado_inscripcion']
    instance.dvh = GestorDigitosVerificadores.calcular_dvh(instance, campos_criticos)

@receiver(models.signals.post_save, sender=InscripcionMesaExamen)
def actualizar_dvv_inscripcion_mesa(sender, instance, **kwargs):
    """Actualiza el DVV de la tabla después de guardar"""
    from institucional.digitos_verificadores import GestorDigitosVerificadores
    GestorDigitosVerificadores.actualizar_dvv('InscripcionMesaExamen', 'academico')


@receiver(models.signals.post_save, sender=InscripcionMesaExamen)
def sincronizar_nota_examen(sender, instance, **kwargs):
    """
    Sincroniza la nota del examen con el historial de Calificaciones 
    y el estado de la materia (InscripcionAlumnoComision).
    Se ejecuta siempre que se guarda una InscripcionMesaExamen.
    """
    from django.utils import timezone
    
    # Si no hay nota, no hay nada que sincronizar
    if instance.nota_examen is None:
        return

    # 1. Buscar la cursada asociada
    cursada = InscripcionAlumnoComision.objects.filter(
        alumno=instance.alumno,
        comision__materia=instance.mesa_examen.materia
    ).first()

    if not cursada:
        return

    # 2. Sincronizar (Crear o Actualizar) Calificación
    Calificacion.objects.update_or_create(
        alumno_comision=cursada,
        tipo=TipoCalificacion.FINAL,
        numero=1, # Asumimos 1 por ahora para finales
        defaults={
            'nota': instance.nota_examen,
            'fecha_creacion': instance.mesa_examen.fecha_examen
        }
    )

    # 3. Actualizar Estado de la Materia
    nota_aprobacion = instance.mesa_examen.anio_academico.nota_aprobacion
    aprobado = instance.nota_examen >= nota_aprobacion

    if aprobado:
        cursada.nota_final = instance.nota_examen
        cursada.estado_inscripcion = EstadoMateria.APROBADA
        cursada.fecha_cierre = timezone.now()
        # Si se guarda desde admin, no tenemos el usuario fácil, 
        # pero es mejor actualizar el estado que dejarlo inconsistente.
        cursada.save()
    else:
        # Si la nota cambió a desaprobado, y antes estaba aprobada, deberíamos revertir?
        # Por seguridad, si desaprueba, nos aseguramos que NO figure aprobada
        # (pero mantenemos su condición de REGULAR/LIBRE original).
        if cursada.estado_inscripcion == EstadoMateria.APROBADA:
            # Revertir a la condición de cursada (Regular o Libre)
            if cursada.condicion == CondicionInscripcion.REGULAR:
                cursada.estado_inscripcion = EstadoMateria.REGULAR
            else:
                cursada.estado_inscripcion = EstadoMateria.LIBRE
            
            cursada.nota_final = None
            cursada.fecha_cierre = None
            cursada.save()



class CalendarioAcademico(models.Model):
    anio_academico = models.ForeignKey(AnioAcademico, on_delete=models.CASCADE)
    fecha = models.DateField(db_index=True)
    es_dia_clase = models.BooleanField(default=True, db_index=True)
    descripcion = models.CharField(max_length=200, blank=True, null=True)

    class Meta:
        verbose_name = 'Calendario Académico'
        verbose_name_plural = 'Calendario Académico'
        unique_together = ('anio_academico', 'fecha')
        indexes = [
            models.Index(fields=['anio_academico', 'fecha', 'es_dia_clase'], name='cal_anio_fecha_clase_idx'),
        ]

    def __str__(self):
        return f"{self.fecha} - {'Clase' if self.es_dia_clase else 'No Clase'}"

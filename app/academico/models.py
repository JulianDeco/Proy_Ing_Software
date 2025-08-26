import datetime
from django.db import models
from django.core.exceptions import ValidationError
from django.db.models.signals import post_save
from django.dispatch import receiver

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
    
    class Meta:
        verbose_name = 'Año Académico'
        verbose_name_plural = 'Años Académicos'
    
    def __str__(self):
        return f"{self.nombre} ({self.fecha_inicio} - {self.fecha_fin})"
    
    def clean(self):
        if self.fecha_fin <= self.fecha_inicio:
            raise ValidationError("La fecha de fin debe ser mayor a la fecha de inicio.")

class Comision(models.Model):
    codigo = models.CharField(max_length=20)
    horario_inicio = models.TimeField()
    horario_fin = models.TimeField()
    dia_cursado = models.IntegerField(choices=Dia.choices)
    turno = models.CharField(max_length=50, choices=Turno.choices)
    docente = models.ForeignKey('institucional.Persona', on_delete=models.SET_NULL, null=True)
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE)
    aula = models.CharField(max_length=50, blank=True, null=True)
    cupo_maximo = models.PositiveIntegerField(default=30)
    estado = models.CharField(max_length=20, choices=EstadoComision.choices)
    anio_academico = models.ForeignKey(AnioAcademico, on_delete=models.CASCADE, blank=True)

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

class EstadoMateria(models.TextChoices):
    REGULAR = 'REGULAR', 'Regular'
    LIBRE = 'LIBRE', 'Libre'

class InscripcionesAlumnosComisiones(models.Model):
    alumno = models.ForeignKey(Alumno, on_delete=models.CASCADE)
    comision = models.ForeignKey(Comision, on_delete=models.CASCADE)
    creado = models.DateTimeField(auto_now_add=True)
    estado_inscripcion = models.CharField(
        max_length=20,
        choices=EstadoMateria.choices,
        default='REGULAR'
    )

    class Meta:
        db_table = 'institucional_inscripciones_alumnos_comisiones'
        verbose_name = 'Inscripción del alumno en comisiones'
        verbose_name_plural = 'Inscripciones de alumnos en comisiones'
        unique_together = ('alumno', 'comision')
    
    def __str__(self):
        return f"{self.alumno.nombre} {self.alumno.apellido} - {self.comision.codigo}"
    
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

@receiver(post_save, sender=InscripcionesAlumnosComisiones)
def crear_asistencias_al_inscribir(sender, instance, created, **kwargs):
    if created:
        cantidad_creada = instance.crear_asistencias_automaticas()

class TipoCalificacion(models.TextChoices):
    PARCIAL = 'PARCIAL', 'Parcial'
    TRABAJO_PRACTICO = 'TP', 'Trabajo Práctico'
    FINAL = 'FINAL', 'Final'
    CONCEPTO = 'CONCEPTO', 'Concepto'
    
class Calificacion(models.Model):
    alumno_comision = models.ForeignKey(InscripcionesAlumnosComisiones, on_delete=models.CASCADE, related_name='calificaciones')
    tipo = models.CharField(max_length=20, choices=TipoCalificacion.choices)
    nota = models.DecimalField(max_digits=4, decimal_places=2)

    class Meta:
        unique_together = ('alumno_comision', 'tipo')
        verbose_name = 'Calificación'
        verbose_name_plural = 'Calificaciones'

    def __str__(self):
        return f"{self.alumno_comision.alumno} - {self.tipo}: {self.nota}"
    
class Asistencia(models.Model):
    alumno_comision = models.ForeignKey(InscripcionesAlumnosComisiones, on_delete=models.CASCADE, related_name='asistencias')
    esta_presente = models.BooleanField(default=False)
    fecha_asistencia = models.DateField()

    class Meta:
        verbose_name = 'Asistencia'
        verbose_name_plural = 'Asistencias'

    def __str__(self):
        if self.esta_presente:
            return f"{self.alumno_comision.alumno} - Presente - {self.fecha_asistencia}"
        else:
            return f"{self.alumno_comision.alumno} - Ausente - {self.fecha_asistencia}"



class CalendarioAcademico(models.Model):
    anio_academico = models.ForeignKey(AnioAcademico, on_delete=models.CASCADE)
    fecha = models.DateField()
    es_dia_clase = models.BooleanField(default=True)
    descripcion = models.CharField(max_length=200, blank=True, null=True)
    
    class Meta:
        verbose_name = 'Calendario Académico'
        verbose_name_plural = 'Calendario Académico'
        unique_together = ('anio_academico', 'fecha')
    
    def __str__(self):
        return f"{self.fecha} - {'Clase' if self.es_dia_clase else 'No Clase'}"

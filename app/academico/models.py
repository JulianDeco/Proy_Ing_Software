import datetime
from django.db import models
from django.core.exceptions import ValidationError

from administracion.models import PlanEstudio
from institucional.models import Persona

# ------------------- MATERIA -------------------
class Materia(models.Model):
    nombre = models.CharField(max_length=100)
    codigo = models.CharField(max_length=20)
    plan_estudio = models.ForeignKey(PlanEstudio, on_delete=models.CASCADE)
    descripcion = models.TextField(blank=True, null=True)
    creditos = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'academico_materias'
        verbose_name = 'Materia'
        verbose_name_plural = 'Materias'
        unique_together = ('codigo', 'plan_estudio')

    def __str__(self):
        return f"{self.nombre} ({self.codigo})"

OPCIONES_TURNO = [
    ('mañana', 'Mañana'),
    ('tarde', 'Tarde'),
    ('noche', 'Noche'),
]

OPCIONES_DIAS = [
    (1, 'Lunes'),
    (2, 'Martes'),
    (3, 'Miércoles'),
    (4, 'Jueves'),
    (5, 'Viernes'),
    (6, 'Sábado'),
]

class Comision(models.Model):
    codigo = models.CharField(max_length=20)
    horario_inicio = models.TimeField()
    horario_fin = models.TimeField()
    dia_cursado = models.IntegerField(choices=OPCIONES_DIAS)
    turno = models.CharField(max_length=50, choices=OPCIONES_TURNO)
    docente = models.ForeignKey('institucional.Persona', on_delete=models.SET_NULL, null=True)
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE)
    aula = models.CharField(max_length=50, blank=True, null=True)
    cupo_maximo = models.PositiveIntegerField(default=30)

    class Meta:
        db_table = 'academico_comisiones'
        verbose_name = 'Comision'
        verbose_name_plural = 'Comisiones'
        unique_together = ('codigo', 'materia', 'turno', 'dia_cursado')

    def __str__(self):
        return f"{self.materia} - ({self.codigo}) - {self.turno}"

    def clean(self):
        if self.horario_fin <= self.horario_inicio:
            raise ValidationError("El horario de fin debe ser mayor al horario de inicio.")

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

    def __str__(self):
        return f"{self.dni} - {self.nombre} {self.apellido}"



class InscripcionesAlumnosComisiones(models.Model):
    alumno = models.ForeignKey(Alumno, on_delete=models.CASCADE)
    comision = models.ForeignKey(Comision, on_delete=models.CASCADE)
    creado = models.DateTimeField(auto_now_add=True)
    estado_inscripcion = models.CharField(
        max_length=20,
        choices=[('INSCRIPTO', 'Inscripto'), ('RETIRADO', 'Retirado'), ('FINALIZADO', 'Finalizado')],
        default='INSCRIPTO'
    )

    class Meta:
        db_table = 'institucional_inscripciones_alumnos_comisiones'
        verbose_name = 'Inscripción del alumno en comisiones'
        verbose_name_plural = 'Inscripciones de alumnos en comisiones'
        unique_together = ('alumno', 'comision')

    def __str__(self):
        return f"Alumno {self.alumno.dni} inscripto en {self.comision.codigo}"



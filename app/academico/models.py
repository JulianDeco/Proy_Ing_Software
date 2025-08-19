from django.db import models

from administracion.models import PlanEstudio

class Materia(models.Model):
    nombre = models.CharField(max_length=100)
    codigo = models.CharField(max_length=20, unique=True)
    plan_estudio = models.ForeignKey(PlanEstudio, on_delete=models.CASCADE)
    
    class Meta:
        db_table = 'academico_materias'
        verbose_name = 'Materia'
        verbose_name_plural = 'Materias'
        
            
    def __str__(self):
        return f"{self.nombre} ({self.codigo})"

OPCIONES_TURNO = [
    ('mañana', 'Mañana'),
    ('tarde', 'Tarde'),
    ('noche', 'Noche'),
    ]

OPCIONES_DIAS = [
    ('1', 'Lunes'),
    ('2', 'Martes'),
    ('3', 'Miércoles'),
    ('4', 'Jueves'),
    ('5', 'Viernes'),
    ('6', 'Sábado'),
    ]
class Comision(models.Model):
    codigo = models.CharField(max_length=20)
    horario_inicio = models.TimeField()
    horario_fin = models.TimeField()
    dia_cursado = models.CharField(max_length=50, choices=OPCIONES_DIAS, default=0)
    turno = models.CharField(max_length=50, choices=OPCIONES_TURNO)
    
    docente = models.ForeignKey('institucional.Persona', on_delete=models.SET_NULL, null=True, blank=True)
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE)
    
    
    class Meta:
        db_table = 'academico_comisiones'
        verbose_name = 'Comision'
        verbose_name_plural = 'Comisiones'
        
    def __str__(self):
        return f"{self.materia} - ({self.codigo}) - {self.turno}"
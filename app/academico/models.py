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

class Comision(models.Model):
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE)
    codigo = models.CharField(max_length=20)
    horario = models.TimeField()
    turno = models.CharField(max_length=50)
    
    class Meta:
        db_table = 'academico_comisiones'
        verbose_name = 'Comision'
        verbose_name_plural = 'Comisiones'
from django.db import models

from institucional.models import PlanEstudio

class Materia(models.Model):
    nombre = models.CharField(max_length=100)
    codigo = models.CharField(max_length=20, unique=True)
    plan_estudio = models.ForeignKey(PlanEstudio)
class Comision(models.Model):
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE)
    codigo = models.CharField(max_length=20)
    horario = models.TimeField()
    turno = models.CharField(max_length=50)
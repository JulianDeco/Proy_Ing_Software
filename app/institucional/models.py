from django.db import models
from django.contrib.auth.models import AbstractUser

from academico.models import Materia

class Usuario(AbstractUser):
    # Extiende el modelo de Django para login
    persona = models.OneToOneField('Persona', on_delete=models.CASCADE, null=True, blank=True)
    habilitado = models.BooleanField(default=True)

class Persona(models.Model):
    dni = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    roles = models.ManyToManyField('Rol', related_name='personas')

    def __str__(self):
        return f"{self.nombre} {self.apellido} ({self.dni})"

class Rol(models.Model):
    nombre = models.CharField(max_length=50)  # Docente, Administrativo, Alumno
    descripcion = models.TextField(blank=True)

    def __str__(self):
        return self.nombre
    
class PlanEstudio(models.Model):
    nombre = models.CharField(max_length=100)
    codigo = models.CharField(max_length=20, unique=True)
from django.db import models
from django.contrib.auth.models import AbstractUser

from academico.models import Materia

class Usuario(AbstractUser):
    persona = models.OneToOneField('Persona', on_delete=models.CASCADE, null=True, blank=True)
    habilitado = models.BooleanField(default=True)

    class Meta:
        db_table = 'institucional_usuarios'
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

class Persona(models.Model):
    dni = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    roles = models.ManyToManyField('Rol', related_name='personas')

    class Meta:
        db_table = 'institucional_personas'
        verbose_name = 'Persona'
        verbose_name_plural = 'Personas'

    def __str__(self):
        return f"{self.nombre} {self.apellido} ({self.dni})"


class Rol(models.Model):
    nombre = models.CharField(max_length=50)  # Docente, Administrativo, Alumno
    descripcion = models.TextField(blank=True)

    class Meta:
        db_table = 'institucional_roles'
        verbose_name = 'Rol'
        verbose_name_plural = 'Roles'

    def __str__(self):
        return self.nombre
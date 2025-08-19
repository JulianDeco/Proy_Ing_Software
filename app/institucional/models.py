from django.db import models
from django.contrib.auth.models import AbstractUser

class Usuario(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    habilitado = models.BooleanField(default=True)


    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    class Meta:
        db_table = 'institucional_usuarios'
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
        
    def __str__(self):
        return self.email


class Persona(models.Model):
    dni = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    usuario = models.OneToOneField(
        'Usuario', on_delete=models.SET_NULL, 
        null=True, blank=True,
        related_name='persona'
    )
    es_alumno = models.BooleanField(default=False)

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
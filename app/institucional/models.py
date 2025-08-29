from django.db import models
from django.contrib.auth.models import AbstractUser

class Institucion(models.Model):
    nombre = models.CharField(max_length=200)
    direccion = models.CharField(max_length=200)
    nro_telefono = models.CharField(max_length=200)
    nro_celular = models.CharField(max_length=200)
    logo = models.FileField(upload_to='app/static/img/')

class Usuario(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    habilitado = models.BooleanField(default=True)


    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    # objects = UsuarioManager()
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

    class Meta:
        db_table = 'institucional_personas'
        verbose_name = 'Persona'
        verbose_name_plural = 'Personas'

    @property
    def get_full_name(self):
        return f'{self.nombre} {self.apellido}'

    def __str__(self):
        return f"{self.get_full_name} ({self.dni})"
    
class Empleado(Persona):
    usuario = models.OneToOneField(
        'Usuario', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='empleado'
    )

    class Meta:
        db_table = 'institucional_empleados'
        verbose_name = 'Empleado'
        verbose_name_plural = 'Empleados'


class Rol(models.Model):
    nombre = models.CharField(max_length=50) 
    descripcion = models.TextField(blank=True)

    class Meta:
        db_table = 'institucional_roles'
        verbose_name = 'Rol'
        verbose_name_plural = 'Roles'

    def __str__(self):
        return self.nombre
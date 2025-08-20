from django.db import models
from django.contrib.auth.models import AbstractUser

from django.contrib.auth.models import BaseUserManager

# class UsuarioManager(BaseUserManager):
#     def create_user(self, email, password=None, **extra_fields):
#         if not email:
#             raise ValueError('El email debe estar configurado.')
#         email = self.normalize_email(email)
#         user = self.model(email=email, **extra_fields)
#         user.set_password(password)
#         user.save(using=self._db)
#         return user

#     def create_superuser(self, email, password=None, **extra_fields):
#         extra_fields.setdefault('is_staff', True)
#         extra_fields.setdefault('is_superuser', True)
#         extra_fields.setdefault('is_active', True)

#         if extra_fields.get('is_staff') is not True:
#             raise ValueError('Superuser must have is_staff=True.')
#         if extra_fields.get('is_superuser') is not True:
#             raise ValueError('Superuser must have is_superuser=True.')
        
#         return self.create_user(email, password, **extra_fields)

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

    def __str__(self):
        return f"{self.nombre} {self.apellido} ({self.dni})"
    
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
    nombre = models.CharField(max_length=50)  # Docente, Administrativo, Alumno
    descripcion = models.TextField(blank=True)

    class Meta:
        db_table = 'institucional_roles'
        verbose_name = 'Rol'
        verbose_name_plural = 'Roles'

    def __str__(self):
        return self.nombre
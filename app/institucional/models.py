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


class TipoAccion(models.TextChoices):
    LOGIN = 'LOGIN', 'Inicio de Sesión'
    LOGOUT = 'LOGOUT', 'Cierre de Sesión'
    LOGIN_FALLIDO = 'LOGIN_FALLIDO', 'Intento de Login Fallido'


class AuditoriaAcceso(models.Model):
    usuario = models.ForeignKey('Usuario', on_delete=models.SET_NULL, null=True, blank=True)
    email = models.EmailField()
    tipo_accion = models.CharField(max_length=20, choices=TipoAccion.choices)
    fecha_hora = models.DateTimeField(auto_now_add=True, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)
    exitoso = models.BooleanField(default=True)
    detalles = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'institucional_auditoria_accesos'
        verbose_name = 'Auditoría de Acceso'
        verbose_name_plural = 'Auditoría de Accesos'
        ordering = ['-fecha_hora']
        indexes = [
            models.Index(fields=['-fecha_hora'], name='audit_fecha_idx'),
            models.Index(fields=['usuario', '-fecha_hora'], name='audit_usuario_fecha_idx'),
            models.Index(fields=['tipo_accion', '-fecha_hora'], name='audit_tipo_fecha_idx'),
        ]

    def __str__(self):
        return f"{self.email} - {self.get_tipo_accion_display()} - {self.fecha_hora.strftime('%d/%m/%Y %H:%M:%S')}"
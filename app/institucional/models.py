from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager

class CustomUserManager(BaseUserManager):
    """Define a model manager for User model with no username field."""

    def _create_user(self, email, password=None, **extra_fields):
        """Create and save a User with the given email and password."""
        if not email:
            raise ValueError('The given email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and save a SuperUser with the given email and password."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email, password, **extra_fields)

class Institucion(models.Model):
    nombre = models.CharField(max_length=200)
    direccion = models.CharField(max_length=200)
    nro_telefono = models.CharField(max_length=200, verbose_name="Número de Teléfono")
    nro_celular = models.CharField(max_length=200, blank=True, null=True, verbose_name="Número de Celular")
    email_contacto = models.EmailField(verbose_name="Email de Contacto", blank=True, null=True)
    logo = models.FileField(upload_to='app/static/img/', blank=True, null=True)
    archivo_manual = models.FileField(
        upload_to='docs/',
        blank=True,
        null=True,
        verbose_name="Manual de Usuario (PDF)"
    )
    
    class Meta:
        verbose_name = "Institución"
        verbose_name_plural = "Institución" # Singleton conceptual

    def __str__(self):
        return self.nombre

class PreguntaFrecuente(models.Model):
    pregunta = models.CharField(max_length=255)
    respuesta = models.TextField()
    orden = models.PositiveIntegerField(default=0)
    publicada = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Pregunta Frecuente"
        verbose_name_plural = "Preguntas Frecuentes"
        ordering = ['orden']

    def __str__(self):
        return self.pregunta

class Usuario(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    habilitado = models.BooleanField(default=True)


    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    
    objects = CustomUserManager()

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


class TipoAccionDatos(models.TextChoices):
    CREAR = 'CREAR', 'Creación'
    MODIFICAR = 'MODIFICAR', 'Modificación'
    ELIMINAR = 'ELIMINAR', 'Eliminación'


class AuditoriaDatos(models.Model):
    """
    Modelo para auditar cambios en los datos del sistema.
    Registra quién hizo qué cambio, cuándo y qué valores cambiaron.
    """
    usuario = models.ForeignKey(
        'Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cambios_realizados'
    )
    tipo_accion = models.CharField(max_length=20, choices=TipoAccionDatos.choices)
    fecha_hora = models.DateTimeField(auto_now_add=True, db_index=True)

    # Información del modelo afectado
    modelo = models.CharField(max_length=100, db_index=True)
    objeto_id = models.CharField(max_length=100)
    objeto_repr = models.CharField(max_length=255)

    # Valores antes y después del cambio (JSON)
    valores_anteriores = models.JSONField(null=True, blank=True)
    valores_nuevos = models.JSONField(null=True, blank=True)

    # Información adicional
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    detalles = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'institucional_auditoria_datos'
        verbose_name = 'Auditoría de Datos'
        verbose_name_plural = 'Auditoría de Datos'
        ordering = ['-fecha_hora']
        indexes = [
            models.Index(fields=['-fecha_hora'], name='audit_datos_fecha_idx'),
            models.Index(fields=['usuario', '-fecha_hora'], name='audit_datos_usuario_idx'),
            models.Index(fields=['modelo', '-fecha_hora'], name='audit_datos_modelo_idx'),
            models.Index(fields=['tipo_accion', '-fecha_hora'], name='audit_datos_tipo_idx'),
        ]

    def __str__(self):
        return f"{self.modelo} - {self.get_tipo_accion_display()} - {self.fecha_hora.strftime('%d/%m/%Y %H:%M:%S')}"

    @property
    def cambios_resumidos(self):
        """Retorna un resumen de los campos que cambiaron"""
        if self.tipo_accion == TipoAccionDatos.CREAR:
            return "Registro creado"
        elif self.tipo_accion == TipoAccionDatos.ELIMINAR:
            return "Registro eliminado"
        elif self.valores_anteriores and self.valores_nuevos:
            cambios = []
            for key in self.valores_nuevos:
                if key in self.valores_anteriores:
                    if self.valores_anteriores[key] != self.valores_nuevos[key]:
                        cambios.append(f"{key}: '{self.valores_anteriores[key]}' → '{self.valores_nuevos[key]}'")
            return "; ".join(cambios) if cambios else "Sin cambios detectados"
        return "Sin detalles"


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


class DigitoVerificadorVertical(models.Model):
    """
    Almacena el Dígito Verificador Vertical (DVV) para cada tabla crítica.
    El DVV es la suma (o combinación) de los DVH de todos los registros activos.
    """
    tabla = models.CharField(max_length=100, unique=True)
    dvv = models.CharField(max_length=255)  # Hash resultante
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'institucional_dvv'
        verbose_name = 'Dígito Verificador Vertical'
        verbose_name_plural = 'Dígitos Verificadores Verticales'

    def __str__(self):
        return f"{self.tabla}: {self.dvv}"
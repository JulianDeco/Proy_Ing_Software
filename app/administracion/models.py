from django.db import models
from django.db import models
from django.conf import settings

class PlanEstudio(models.Model):
    nombre = models.CharField(max_length=100)
    codigo = models.CharField(max_length=20, unique=True)

    class Meta:
        db_table = 'administracion_planes_estudio'
        verbose_name = 'Plan de Estudio'
        verbose_name_plural = 'Planes de Estudio'
        
    def __str__(self):
        return f"{self.nombre} ({self.codigo})"


class Reporte(models.Model):
    titulo = models.CharField(max_length=100)
    fecha_generacion = models.DateTimeField(auto_now_add=True)
    filtro = models.JSONField()
    archivo = models.FileField(upload_to='reportes/')

    class Meta:
        db_table = 'administracion_reportes'
        verbose_name = 'Reporte'
        verbose_name_plural = 'Reportes'
    

class TipoCertificado(models.TextChoices):
    ASISTENCIA = 'asistencia', 'Certificado de Asistencia'
    APROBACION = 'aprobacion', 'Certificado de Aprobación'
    EXAMEN = 'examen', 'Certificado de Examen'
    ALUMNO_REGULAR = 'alumno_regular', 'Certificado de Alumno Regular'
    BUEN_COMPORTAMIENTO = 'buen_comportamiento', 'Certificado de Buen Comportamiento'
    OTRO = 'otro', 'Otro Certificado'

class Certificado(models.Model):
    alumno = models.ForeignKey('academico.Alumno', on_delete=models.CASCADE)
    tipo = models.CharField(max_length=30, choices=TipoCertificado.choices)
    fecha_emision = models.DateField(auto_now_add=True)
    codigo_verificacion = models.CharField(max_length=50, unique=True)
    contenido = models.TextField(blank=True)
    generado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    class Meta:
        db_table = 'administracion_certificados'
        verbose_name = 'Certificado'
        verbose_name_plural = 'Certificados'
        ordering = ['-fecha_emision']

    def __str__(self):
        return f"Certificado {self.get_tipo_display()} - {self.alumno}"

    def save(self, *args, **kwargs):
        if not self.codigo_verificacion:
            import uuid
            self.codigo_verificacion = str(uuid.uuid4())[:8].upper()
        super().save(*args, **kwargs)


class BackupManager(models.Model):
    """
    Modelo proxy para gestionar backups en el admin.
    No representa una tabla real en la base de datos.
    """
    class Meta:
        managed = False
        verbose_name = 'Gestión de Backup'
        verbose_name_plural = 'Gestión de Backups'
from django.db import models

from institucional.models import Persona, Usuario

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
    

class Certificacion(models.Model):
    persona = models.ForeignKey(Persona, on_delete=models.CASCADE, related_name='certificaciones')
    tipo = models.CharField(max_length=100)  # regularidad, analítico, etc.
    fecha_emision = models.DateField(auto_now_add=True)
    generado_por = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True)

    class Meta:
        db_table = 'institucional_certificaciones'
        verbose_name = 'Certificación'
        verbose_name_plural = 'Certificaciones'

    def __str__(self):
        return f"{self.tipo} - {self.persona.nombre} {self.persona.apellido}"
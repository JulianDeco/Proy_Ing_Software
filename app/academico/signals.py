from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.db import transaction
from datetime import timedelta, date
import holidays

from .models import AnioAcademico, CalendarioAcademico, Calificacion, Asistencia, InscripcionAlumnoComision
from institucional.models import TipoAccionDatos
from institucional.auditoria import registrar_cambio, obtener_valores_modelo

# Modelos a auditar
MODELOS_AUDITABLES = [Calificacion, Asistencia, InscripcionAlumnoComision]

@receiver(pre_save)
def auditoria_pre_save(sender, instance, **kwargs):
    if sender in MODELOS_AUDITABLES and instance.pk:
        try:
            old_instance = sender.objects.get(pk=instance.pk)
            instance._valores_anteriores = obtener_valores_modelo(old_instance)
        except sender.DoesNotExist:
            instance._valores_anteriores = None

@receiver(post_save)
def auditoria_post_save(sender, instance, created, **kwargs):
    if sender in MODELOS_AUDITABLES:
        if created:
            valores_nuevos = obtener_valores_modelo(instance)
            registrar_cambio(instance, TipoAccionDatos.CREAR, valores_nuevos=valores_nuevos)
        else:
            valores_anteriores = getattr(instance, '_valores_anteriores', None)
            valores_nuevos = obtener_valores_modelo(instance)
            if valores_anteriores != valores_nuevos:
                registrar_cambio(
                    instance, 
                    TipoAccionDatos.MODIFICAR, 
                    valores_anteriores=valores_anteriores, 
                    valores_nuevos=valores_nuevos
                )

@receiver(post_delete)
def auditoria_post_delete(sender, instance, **kwargs):
    if sender in MODELOS_AUDITABLES:
        valores_anteriores = obtener_valores_modelo(instance)
        registrar_cambio(instance, TipoAccionDatos.ELIMINAR, valores_anteriores=valores_anteriores)

@receiver(post_save, sender=AnioAcademico)
@transaction.atomic
def crear_calendario_academico(sender, instance, created, **kwargs):
    if not created:
        return

    fecha = instance.fecha_inicio
    feriados_arg = holidays.AR(years=range(instance.fecha_inicio.year, instance.fecha_fin.year + 1))


    while fecha <= instance.fecha_fin:
        es_fin_de_semana = fecha.weekday() >= 5
        es_feriado = fecha in feriados_arg

        descripcion = ''
        if es_feriado:
            descripcion = feriados_arg.get(fecha)
        elif es_fin_de_semana:
            descripcion = 'Fin de semana'

        es_dia_clase = not (es_feriado or es_fin_de_semana)

        CalendarioAcademico.objects.get_or_create(
            anio_academico=instance,
            fecha=fecha,
            defaults={
                'es_dia_clase': es_dia_clase,
                'descripcion': descripcion
            }
        )

        fecha += timedelta(days=1)

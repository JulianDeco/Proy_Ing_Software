from django.db.models.signals import post_save
from django.dispatch import receiver
from datetime import timedelta, date
import holidays

from .models import AnioAcademico, CalendarioAcademico

@receiver(post_save, sender=AnioAcademico)
def crear_calendario_academico(sender, instance, created, **kwargs):
    if not created:
        return

    fecha = instance.fecha_inicio
    feriados_arg = holidays.AR(years=range(instance.fecha_inicio.year, instance.fecha_fin.year + 1))

    vacaciones_invierno = (
        date(instance.fecha_inicio.year, 7, 15),  
        date(instance.fecha_inicio.year, 7, 26),  
    )

    while fecha <= instance.fecha_fin:
        es_fin_de_semana = fecha.weekday() >= 5
        es_feriado = fecha in feriados_arg
        es_receso = vacaciones_invierno[0] <= fecha <= vacaciones_invierno[1]

        descripcion = ''
        if es_feriado:
            descripcion = feriados_arg.get(fecha)
        elif es_receso:
            descripcion = 'Receso de invierno'
        elif es_fin_de_semana:
            descripcion = 'Fin de semana'

        es_dia_clase = not (es_feriado or es_receso or es_fin_de_semana)

        CalendarioAcademico.objects.get_or_create(
            anio_academico=instance,
            fecha=fecha,
            defaults={
                'es_dia_clase': es_dia_clase,
                'descripcion': descripcion
            }
        )

        fecha += timedelta(days=1)

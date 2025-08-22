from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
from academico.models import AnioAcademico, CalendarioAcademico

class Command(BaseCommand):
    help = 'Pobla el calendario académico con días lectivos, feriados y recesos'

    def add_arguments(self, parser):
        parser.add_argument(
            '--anio',
            type=int,
            help='ID del año académico a poblar (opcional)',
        )

    def handle(self, *args, **options):
        # Obtener el año académico
        anio_id = options.get('anio')
        if anio_id:
            anio_academico = AnioAcademico.objects.get(id=anio_id)
        else:
            anio_academico = AnioAcademico.objects.filter(activo=True).first()
        
        if not anio_academico:
            self.stdout.write(self.style.ERROR('No hay año académico activo'))
            return

        self.stdout.write(f"Poblando calendario para: {anio_academico.nombre}")

        # Feriados nacionales (Argentina 2024)
        feriados = [
            (2025, 1, 1, 'Año Nuevo'),
            (2025, 2, 12, 'Carnaval'),
            (2025, 2, 13, 'Carnaval'),
            (2025, 3, 24, 'Día Nacional de la Memoria por la Verdad y la Justicia'),
            (2025, 3, 29, 'Viernes Santo'),
            (2025, 4, 2, 'Día del Veterano y de los Caídos en la Guerra de Malvinas'),
            (2025, 5, 1, 'Día del Trabajador'),
            (2025, 5, 25, 'Día de la Revolución de Mayo'),
            (2025, 6, 17, 'Paso a la Inmortalidad del General Martín Güemes'),
            (2025, 6, 20, 'Paso a la Inmortalidad del General Manuel Belgrano'),
            (2025, 7, 9, 'Día de la Independencia'),
            (2025, 8, 17, 'Paso a la Inmortalidad del General José de San Martín'),
            (2025, 10, 12, 'Día del Respeto a la Diversidad Cultural'),
            (2025, 11, 18, 'Día de la Soberanía Nacional'),
            (2025, 12, 8, 'Inmaculada Concepción de María'),
            (2025, 12, 25, 'Navidad'),
        ]

        # Recesos académicos (inicio, fin, descripción)
        recesos = [
            (date(2025, 7, 15), date(2025, 7, 26), 'Receso de invierno'),
            (date(2025, 9, 30), date(2025, 10, 4), 'Semana de examen'),
            (date(2025, 11, 25), date(2025, 11, 29), 'Semana de examen final'),
        ]

        fecha_actual = anio_academico.fecha_inicio
        dias_procesados = 0
        dias_clase = 0
        feriados_creados = 0
        recesos_creados = 0

        while fecha_actual <= anio_academico.fecha_fin:
            # Determinar tipo de día
            es_dia_clase = fecha_actual.weekday() < 5  # Lunes a Viernes
            descripcion = ''
            tipo_dia = 'NORMAL'

            # Verificar feriados
            for feriado_anio, feriado_mes, feriado_dia, feriado_nombre in feriados:
                if (fecha_actual.year == feriado_anio and 
                    fecha_actual.month == feriado_mes and 
                    fecha_actual.day == feriado_dia):
                    es_dia_clase = False
                    tipo_dia = 'FERIADO'
                    descripcion = feriado_nombre
                    feriados_creados += 1
                    break

            # Verificar recesos (solo si no es feriado)
            if es_dia_clase:
                for inicio_receso, fin_receso, nombre_receso in recesos:
                    if inicio_receso <= fecha_actual <= fin_receso:
                        es_dia_clase = False
                        tipo_dia = 'RECESO'
                        descripcion = nombre_receso
                        recesos_creados += 1
                        break

            # Crear o actualizar registro
            calendario, created = CalendarioAcademico.objects.get_or_create(
                anio_academico=anio_academico,
                fecha=fecha_actual,
                defaults={
                    'es_dia_clase': es_dia_clase,
                    'descripcion': descripcion,
                }
            )

            if not created:
                # Actualizar si ya existe
                calendario.es_dia_clase = es_dia_clase
                calendario.descripcion = descripcion
                calendario.save()

            if es_dia_clase:
                dias_clase += 1

            dias_procesados += 1
            fecha_actual += timedelta(days=1)

        self.stdout.write(
            self.style.SUCCESS(
                f'✅ Calendario poblado exitosamente!\n'
                f'• Días procesados: {dias_procesados}\n'
                f'• Días de clase: {dias_clase}\n'
                f'• Feriados: {feriados_creados}\n'
                f'• Días de receso: {recesos_creados}'
            )
        )
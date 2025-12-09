from abc import ABC, abstractmethod
from datetime import datetime
from django.db import models
from django.db.models import Avg, Count, Q, Case, When, IntegerField, FloatField, F
from django.db.models.functions import ExtractMonth
from academico.models import (
    InscripcionAlumnoComision, Calificacion, Asistencia, 
    TipoCalificacion, EstadoMateria, CondicionInscripcion,
    Comision, AnioAcademico
)

class ReporteGenerator(ABC):
    """
    Clase base abstracta para generadores de reportes.
    Define la interfaz que deben implementar todos los reportes concretos.
    """
    
    @abstractmethod
    def generar_datos(self, filtros):
        """
        Genera los datos específicos del reporte basado en los filtros proporcionados.
        
        Args:
            filtros (dict): Diccionario con filtros como 'comision_id', 'anio_academico', etc.
            
        Returns:
            dict: Diccionario con los datos procesados del reporte.
        """
        pass

    def _aplicar_filtros_comunes(self, queryset, filtros):
        """Helper para aplicar filtros comunes de inscripción"""
        if filtros.get('comision_id'):
            queryset = queryset.filter(comision_id=filtros['comision_id'])

        if filtros.get('anio_academico'):
            queryset = queryset.filter(comision__anio_academico=filtros['anio_academico'])
            
        return queryset


class ReporteInscripciones(ReporteGenerator):
    """
    Genera reportes relacionados con inscripciones y estados académicos.
    """
    
    def generar_datos(self, filtros):
        inscripciones = InscripcionAlumnoComision.objects.select_related(
            'alumno', 'comision', 'comision__materia'
        )
        inscripciones = self._aplicar_filtros_comunes(inscripciones, filtros)

        # 1. Totales básicos
        total_alumnos = inscripciones.values('alumno').distinct().count()
        total_materias = inscripciones.values('comision__materia').distinct().count()
        total_comisiones = inscripciones.values('comision').distinct().count()

        # 2. Estados Académicos
        # Aprobados: estado_inscripcion = APROBADA
        aprobados = inscripciones.filter(estado_inscripcion=EstadoMateria.APROBADA).count()

        # Desaprobados: estado_inscripcion = DESAPROBADA o LIBRE
        desaprobados = inscripciones.filter(
            Q(estado_inscripcion=EstadoMateria.DESAPROBADA) | 
            Q(estado_inscripcion=EstadoMateria.LIBRE) |
            Q(condicion=CondicionInscripcion.LIBRE)
        ).distinct().count()

        # Regulares (Final Pendiente)
        regulares = inscripciones.filter(
            condicion=CondicionInscripcion.REGULAR
        ).exclude(estado_inscripcion=EstadoMateria.APROBADA).count()

        # En Curso
        en_curso = inscripciones.filter(condicion=CondicionInscripcion.CURSANDO).count()
        
        # Nombre de comisión para contexto si aplica
        nombre_comision = ""
        if filtros.get('comision_id'):
             comision_obj = Comision.objects.filter(id=filtros['comision_id']).select_related('materia').first()
             if comision_obj:
                 nombre_comision = f"{comision_obj.materia.nombre} - {comision_obj.codigo}"

        return {
            'tipo': 'inscripciones',
            'estadisticas': {
                'total_alumnos': total_alumnos,
                'total_materias': total_materias,
                'total_comisiones': total_comisiones,
                'aprobados': aprobados,
                'desaprobados': desaprobados,
                'regulares': regulares,
                'en_curso': en_curso,
            },
            'estados_academicos': (aprobados, desaprobados, regulares, en_curso),
            'nombre_comision': nombre_comision,
            'vista_detalle': bool(filtros.get('comision_id'))
        }


class ReporteNotas(ReporteGenerator):
    """
    Genera reportes relacionados con calificaciones y rendimiento académico.
    """
    
    def generar_datos(self, filtros):
        inscripciones = InscripcionAlumnoComision.objects.all()
        inscripciones = self._aplicar_filtros_comunes(inscripciones, filtros)
        
        es_vista_comision = bool(filtros.get('comision_id'))

        # 1. Promedios (Por alumno o por materia según vista)
        if es_vista_comision:
            promedios_query = Calificacion.objects.filter(
                alumno_comision__in=inscripciones
            ).values(
                'alumno_comision__alumno__apellido',
                'alumno_comision__alumno__nombre'
            ).annotate(
                promedio=Avg('nota')
            ).order_by('-promedio')[:15]

            promedios_materias = [
                (f"{item['alumno_comision__alumno__apellido']} {item['alumno_comision__alumno__nombre']}",
                 item['promedio'])
                for item in promedios_query
            ]
        else:
            promedios_materias_query = Calificacion.objects.filter(
                alumno_comision__in=inscripciones
            ).values(
                'alumno_comision__comision__materia__nombre'
            ).annotate(
                promedio=Avg('nota')
            ).order_by('-promedio')[:15]

            promedios_materias = [
                (item['alumno_comision__comision__materia__nombre'], item['promedio'])
                for item in promedios_materias_query
            ]

        # 2. Top Alumnos por Promedio
        alumnos_promedios_query = Calificacion.objects.filter(
            alumno_comision__in=inscripciones
        ).values(
            'alumno_comision__alumno__apellido',
            'alumno_comision__alumno__nombre'
        ).annotate(
            promedio=Avg('nota')
        ).order_by('-promedio')[:10]

        alumnos_promedios = [
            (f"{item['alumno_comision__alumno__apellido']} {item['alumno_comision__alumno__nombre']}",
             item['promedio'])
            for item in alumnos_promedios_query
        ]

        # 3. Top Alumnos por Materias Aprobadas
        alumnos_materias_query = Calificacion.objects.filter(
            alumno_comision__in=inscripciones,
            tipo=TipoCalificacion.FINAL,
            nota__gte=6
        ).values(
            'alumno_comision__alumno__apellido',
            'alumno_comision__alumno__nombre'
        ).annotate(
            aprobadas=Count('id')
        ).order_by('-aprobadas')[:10]

        alumnos_materias_aprobadas = [
            (f"{item['alumno_comision__alumno__apellido']} {item['alumno_comision__alumno__nombre']}",
             item['aprobadas'])
            for item in alumnos_materias_query
        ]

        # 4. Promedio General
        promedio_general = Calificacion.objects.filter(
            alumno_comision__in=inscripciones
        ).aggregate(Avg('nota'))['nota__avg'] or 0

        return {
            'tipo': 'notas',
            'estadisticas': {
                'promedio_general': round(promedio_general, 2) if promedio_general else 0,
            },
            'promedios_materias': promedios_materias,
            'alumnos_top_promedio': alumnos_promedios[:10],
            'alumnos_materias_aprobadas': alumnos_materias_aprobadas[:10],
        }


class ReporteAsistencia(ReporteGenerator):
    """
    Genera reportes relacionados con la asistencia.
    """
    
    def generar_datos(self, filtros):
        inscripciones = InscripcionAlumnoComision.objects.all()
        inscripciones = self._aplicar_filtros_comunes(inscripciones, filtros)
        
        asistencias_query = Asistencia.objects.filter(
            alumno_comision__in=inscripciones
        )

        if filtros.get('fecha_inicio'):
            asistencias_query = asistencias_query.filter(fecha_asistencia__gte=filtros['fecha_inicio'])
        if filtros.get('fecha_fin'):
            asistencias_query = asistencias_query.filter(fecha_asistencia__lte=filtros['fecha_fin'])

        # 1. Asistencias por Mes
        asistencias_mes = asistencias_query.annotate(
            mes=ExtractMonth('fecha_asistencia')
        ).values('mes').annotate(
            total=Count('id'),
            presentes=Count(Case(When(esta_presente=True, then=1), output_field=IntegerField()))
        ).order_by('mes')

        meses_nombres = {1: 'Ene', 2: 'Feb', 3: 'Mar', 4: 'Abr', 5: 'May', 6: 'Jun',
                         7: 'Jul', 8: 'Ago', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dic'}

        porcentajes_por_mes = {
            meses_nombres[item['mes']]: (item['presentes'] / item['total'] * 100) if item['total'] > 0 else 0
            for item in asistencias_mes
        }

        # 2. Top Alumnos por Asistencia
        alumnos_asistencias_query = Asistencia.objects.filter(
            alumno_comision__in=inscripciones
        ).values(
            'alumno_comision__alumno__apellido',
            'alumno_comision__alumno__nombre'
        ).annotate(
            total=Count('id'),
            presentes=Count(Case(When(esta_presente=True, then=1), output_field=IntegerField()))
        ).annotate(
            porcentaje=Case(
                When(total__gt=0, then=100.0 * F('presentes') / F('total')),
                default=0.0,
                output_field=FloatField()
            )
        ).order_by('-porcentaje')[:10]

        alumnos_asistencias = [
            (f"{item['alumno_comision__alumno__apellido']} {item['alumno_comision__alumno__nombre']}",
             item['porcentaje'])
            for item in alumnos_asistencias_query
        ]

        # 3. Asistencia General
        asist_stats = asistencias_query.aggregate(
            total=Count('id'),
            presentes=Count(Case(When(esta_presente=True, then=1), output_field=IntegerField()))
        )
        porcentaje_general = (asist_stats['presentes'] / asist_stats['total'] * 100) if asist_stats['total'] > 0 else 0

        return {
            'tipo': 'asistencia',
            'estadisticas': {
                'porcentaje_asistencia_general': round(porcentaje_general, 2),
            },
            'asistencias_por_mes': dict(porcentajes_por_mes),
            'alumnos_top_asistencia': alumnos_asistencias[:10],
        }


class ReportFactory:
    """
    Fábrica para crear instancias de generadores de reportes.
    Implementa el patrón Factory Method.
    """
    
    @staticmethod
    def crear_reporte(tipo_reporte):
        """
        Crea y retorna una instancia del generador de reporte solicitado.
        
        Args:
            tipo_reporte (str): Tipo de reporte ('inscripciones', 'notas', 'asistencia').
            
        Returns:
            ReporteGenerator: Instancia del generador de reporte.
            
        Raises:
            ValueError: Si el tipo de reporte no es válido.
        """
        if tipo_reporte == 'inscripciones':
            return ReporteInscripciones()
        elif tipo_reporte == 'notas':
            return ReporteNotas()
        elif tipo_reporte == 'asistencia':
            return ReporteAsistencia()
        else:
            raise ValueError(f"Tipo de reporte desconocido: {tipo_reporte}")

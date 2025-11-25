"""
Utilidades para generación de reportes académicos con gráficos
Incluye funciones para crear gráficos en base64 para HTML/PDF y para Excel
"""
import io
import base64
from datetime import datetime
from collections import defaultdict

import matplotlib
matplotlib.use('Agg')  # Backend sin interfaz gráfica para servidores
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import numpy as np

from openpyxl import Workbook
from openpyxl.chart import BarChart, PieChart, LineChart, Reference
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.utils import get_column_letter

from django.db.models import Avg, Count, Q, Max, Min
from academico.models import (
    Alumno, Materia, Comision, InscripcionAlumnoComision,
    Calificacion, Asistencia, TipoCalificacion
)


def generar_grafico_base64(fig):
    """
    Convierte una figura de matplotlib a base64 para incrustar en HTML o PDF
    """
    buffer = io.BytesIO()
    fig.savefig(buffer, format='png', bbox_inches='tight', dpi=100)
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.read()).decode('utf-8')
    plt.close(fig)
    return image_base64


def grafico_distribucion_notas(calificaciones_data, titulo="Distribución de Notas"):
    """
    Genera un gráfico de barras con la distribución de notas
    calificaciones_data: lista de tuplas (materia_nombre, nota_promedio)
    """
    if not calificaciones_data:
        return None

    fig, ax = plt.subplots(figsize=(10, 6))

    materias = [item[0][:20] for item in calificaciones_data]  # Limitar nombre
    notas = [item[1] for item in calificaciones_data]

    colores = ['#2ecc71' if nota >= 6 else '#e74c3c' for nota in notas]

    bars = ax.bar(materias, notas, color=colores, alpha=0.7)
    ax.axhline(y=6, color='#f39c12', linestyle='--', linewidth=2, label='Nota mínima (6)')

    ax.set_xlabel('Materias', fontsize=12)
    ax.set_ylabel('Nota Promedio', fontsize=12)
    ax.set_title(titulo, fontsize=14, fontweight='bold')
    ax.set_ylim(0, 10)
    ax.legend()
    ax.grid(axis='y', alpha=0.3)

    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()

    return generar_grafico_base64(fig)


def grafico_aprobados_desaprobados(aprobados, desaprobados, regulares):
    """
    Genera un gráfico circular con distribución de estados académicos
    """
    if aprobados == 0 and desaprobados == 0 and regulares == 0:
        return None

    fig, ax = plt.subplots(figsize=(8, 8))

    labels = []
    sizes = []
    colors = []

    if aprobados > 0:
        labels.append(f'Aprobados ({aprobados})')
        sizes.append(aprobados)
        colors.append('#2ecc71')

    if desaprobados > 0:
        labels.append(f'Desaprobados ({desaprobados})')
        sizes.append(desaprobados)
        colors.append('#e74c3c')

    if regulares > 0:
        labels.append(f'Regulares ({regulares})')
        sizes.append(regulares)
        colors.append('#f39c12')

    wedges, texts, autotexts = ax.pie(
        sizes,
        labels=labels,
        colors=colors,
        autopct='%1.1f%%',
        startangle=90,
        textprops={'fontsize': 12}
    )

    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontweight('bold')

    ax.set_title('Distribución de Estados Académicos', fontsize=14, fontweight='bold')
    plt.tight_layout()

    return generar_grafico_base64(fig)


def grafico_evolucion_asistencias(asistencias_por_mes):
    """
    Genera un gráfico de líneas con la evolución de asistencias
    asistencias_por_mes: dict {mes: porcentaje_asistencia}
    """
    if not asistencias_por_mes:
        return None

    fig, ax = plt.subplots(figsize=(10, 6))

    meses = list(asistencias_por_mes.keys())
    porcentajes = list(asistencias_por_mes.values())

    ax.plot(meses, porcentajes, marker='o', linewidth=2, markersize=8, color='#3498db')
    ax.fill_between(meses, porcentajes, alpha=0.3, color='#3498db')
    ax.axhline(y=75, color='#f39c12', linestyle='--', linewidth=2, label='Asistencia mínima (75%)')

    ax.set_xlabel('Mes', fontsize=12)
    ax.set_ylabel('Porcentaje de Asistencia (%)', fontsize=12)
    ax.set_title('Evolución de Asistencias', fontsize=14, fontweight='bold')
    ax.set_ylim(0, 100)
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.xticks(rotation=45)
    plt.tight_layout()

    return generar_grafico_base64(fig)


def grafico_comparativo_alumnos(alumnos_data, metrica='promedio'):
    """
    Genera un gráfico comparativo de múltiples alumnos
    alumnos_data: lista de tuplas (apellido_nombre, valor)
    """
    if not alumnos_data:
        return None

    fig, ax = plt.subplots(figsize=(12, 6))

    nombres = [item[0][:25] for item in alumnos_data]
    valores = [item[1] for item in alumnos_data]

    colores = plt.cm.viridis(np.linspace(0, 1, len(nombres)))

    bars = ax.barh(nombres, valores, color=colores, alpha=0.7)

    ylabel_map = {
        'promedio': 'Nota Promedio',
        'asistencia': 'Porcentaje de Asistencia (%)',
        'materias_aprobadas': 'Cantidad de Materias Aprobadas'
    }

    ax.set_xlabel(ylabel_map.get(metrica, 'Valor'), fontsize=12)
    ax.set_ylabel('Alumnos', fontsize=12)
    ax.set_title(f'Comparativo de Alumnos - {ylabel_map.get(metrica, "Métrica")}',
                 fontsize=14, fontweight='bold')
    ax.grid(axis='x', alpha=0.3)

    plt.tight_layout()

    return generar_grafico_base64(fig)


def obtener_datos_reporte_academico(filtros=None):
    """
    Obtiene y procesa datos para el reporte académico completo

    filtros: dict con opciones {
        'comision_id': int,
        'materia_id': int,
        'anio_academico': int,
        'fecha_inicio': date,
        'fecha_fin': date
    }

    Retorna: dict con todos los datos procesados y listos para gráficos
    """
    filtros = filtros or {}

    # Base queryset de inscripciones
    inscripciones = InscripcionAlumnoComision.objects.select_related(
        'alumno', 'comision', 'comision__materia', 'comision__anio_academico'
    )

    # Aplicar filtros
    if filtros.get('comision_id'):
        inscripciones = inscripciones.filter(comision_id=filtros['comision_id'])

    if filtros.get('materia_id'):
        inscripciones = inscripciones.filter(comision__materia_id=filtros['materia_id'])

    if filtros.get('anio_academico'):
        inscripciones = inscripciones.filter(comision__anio_academico=filtros['anio_academico'])

    # 1. DATOS DE ALUMNOS
    alumnos = Alumno.objects.filter(
        inscripciones_comisiones__in=inscripciones
    ).distinct()

    # 2. CALIFICACIONES POR MATERIA
    calificaciones_por_materia = {}
    materias_set = set()

    for inscripcion in inscripciones:
        materia = inscripcion.comision.materia
        materias_set.add(materia)

        calificaciones = Calificacion.objects.filter(
            alumno_comision=inscripcion
        )

        if calificaciones.exists():
            promedio = calificaciones.aggregate(Avg('nota'))['nota__avg']
            if materia.nombre not in calificaciones_por_materia:
                calificaciones_por_materia[materia.nombre] = []
            calificaciones_por_materia[materia.nombre].append(promedio)

    # Calcular promedios por materia
    promedios_materias = [
        (materia, np.mean(notas))
        for materia, notas in calificaciones_por_materia.items()
    ]
    promedios_materias.sort(key=lambda x: x[1], reverse=True)

    # 3. ESTADOS ACADÉMICOS (Aprobados, Desaprobados, Regulares)
    aprobados = 0
    desaprobados = 0
    regulares = 0

    for inscripcion in inscripciones:
        calificacion_final = Calificacion.objects.filter(
            alumno_comision=inscripcion,
            tipo=TipoCalificacion.FINAL
        ).first()

        if calificacion_final:
            if calificacion_final.nota >= 6:
                aprobados += 1
            else:
                desaprobados += 1
        elif inscripcion.estado_inscripcion == 'REGULAR':
            regulares += 1

    # 4. ASISTENCIAS POR MES
    asistencias = Asistencia.objects.filter(
        alumno_comision__in=inscripciones
    ).select_related('clase')

    if filtros.get('fecha_inicio'):
        asistencias = asistencias.filter(clase__fecha__gte=filtros['fecha_inicio'])

    if filtros.get('fecha_fin'):
        asistencias = asistencias.filter(clase__fecha__lte=filtros['fecha_fin'])

    asistencias_por_mes = defaultdict(lambda: {'presentes': 0, 'total': 0})

    for asistencia in asistencias:
        mes = asistencia.clase.fecha.strftime('%b')
        asistencias_por_mes[mes]['total'] += 1
        if asistencia.esta_presente:
            asistencias_por_mes[mes]['presentes'] += 1

    porcentajes_por_mes = {
        mes: (datos['presentes'] / datos['total'] * 100) if datos['total'] > 0 else 0
        for mes, datos in asistencias_por_mes.items()
    }

    # 5. DATOS COMPARATIVOS DE ALUMNOS
    alumnos_promedios = []
    alumnos_asistencias = []
    alumnos_materias_aprobadas = []

    for alumno in alumnos[:10]:  # Top 10 para legibilidad
        inscripciones_alumno = inscripciones.filter(alumno=alumno)

        # Promedio
        calificaciones = Calificacion.objects.filter(
            alumno_comision__in=inscripciones_alumno
        )
        if calificaciones.exists():
            promedio = calificaciones.aggregate(Avg('nota'))['nota__avg']
            alumnos_promedios.append((f"{alumno.apellido} {alumno.nombre}", promedio))

        # Asistencia
        asistencias_alumno = Asistencia.objects.filter(
            alumno_comision__in=inscripciones_alumno
        )
        if asistencias_alumno.exists():
            total = asistencias_alumno.count()
            presentes = asistencias_alumno.filter(esta_presente=True).count()
            porcentaje = (presentes / total * 100) if total > 0 else 0
            alumnos_asistencias.append((f"{alumno.apellido} {alumno.nombre}", porcentaje))

        # Materias aprobadas
        aprobadas = Calificacion.objects.filter(
            alumno_comision__in=inscripciones_alumno,
            tipo=TipoCalificacion.FINAL,
            nota__gte=6
        ).count()
        alumnos_materias_aprobadas.append((f"{alumno.apellido} {alumno.nombre}", aprobadas))

    # Ordenar por valor
    alumnos_promedios.sort(key=lambda x: x[1], reverse=True)
    alumnos_asistencias.sort(key=lambda x: x[1], reverse=True)
    alumnos_materias_aprobadas.sort(key=lambda x: x[1], reverse=True)

    # 6. ESTADÍSTICAS GENERALES
    total_alumnos = alumnos.count()
    total_materias = len(materias_set)
    total_comisiones = inscripciones.values('comision').distinct().count()

    promedio_general = 0
    total_calificaciones = Calificacion.objects.filter(
        alumno_comision__in=inscripciones
    )
    if total_calificaciones.exists():
        promedio_general = total_calificaciones.aggregate(Avg('nota'))['nota__avg']

    porcentaje_asistencia_general = 0
    if asistencias.exists():
        total_asist = asistencias.count()
        presentes = asistencias.filter(esta_presente=True).count()
        porcentaje_asistencia_general = (presentes / total_asist * 100) if total_asist > 0 else 0

    return {
        'filtros_aplicados': filtros,
        'fecha_generacion': datetime.now(),

        # Estadísticas
        'estadisticas': {
            'total_alumnos': total_alumnos,
            'total_materias': total_materias,
            'total_comisiones': total_comisiones,
            'promedio_general': round(promedio_general, 2) if promedio_general else 0,
            'porcentaje_asistencia_general': round(porcentaje_asistencia_general, 2),
            'aprobados': aprobados,
            'desaprobados': desaprobados,
            'regulares': regulares,
        },

        # Datos para gráficos
        'promedios_materias': promedios_materias,
        'estados_academicos': (aprobados, desaprobados, regulares),
        'asistencias_por_mes': dict(porcentajes_por_mes),
        'alumnos_top_promedio': alumnos_promedios[:10],
        'alumnos_top_asistencia': alumnos_asistencias[:10],
        'alumnos_materias_aprobadas': alumnos_materias_aprobadas[:10],

        # Listas de entidades
        'alumnos': alumnos,
        'materias': list(materias_set),
        'inscripciones': inscripciones,
    }


def generar_excel_reporte_academico(datos_reporte):
    """
    Genera un archivo Excel con datos y gráficos del reporte académico
    """
    wb = Workbook()

    # Estilos
    header_fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
    header_font = Font(bold=True, color='FFFFFF', size=12)

    # HOJA 1: RESUMEN
    ws_resumen = wb.active
    ws_resumen.title = "Resumen Ejecutivo"

    # Título
    ws_resumen['A1'] = 'REPORTE ACADÉMICO COMPLETO'
    ws_resumen['A1'].font = Font(bold=True, size=16)
    ws_resumen['A2'] = f"Generado: {datos_reporte['fecha_generacion'].strftime('%d/%m/%Y %H:%M')}"

    # Estadísticas
    row = 4
    ws_resumen[f'A{row}'] = 'ESTADÍSTICAS GENERALES'
    ws_resumen[f'A{row}'].font = Font(bold=True, size=14)

    estadisticas = datos_reporte['estadisticas']
    row += 2
    for key, value in estadisticas.items():
        ws_resumen[f'A{row}'] = key.replace('_', ' ').title()
        ws_resumen[f'B{row}'] = value
        row += 1

    # HOJA 2: PROMEDIOS POR MATERIA
    ws_materias = wb.create_sheet("Promedios por Materia")
    ws_materias['A1'] = 'Materia'
    ws_materias['B1'] = 'Promedio'

    for cell in ['A1', 'B1']:
        ws_materias[cell].fill = header_fill
        ws_materias[cell].font = header_font

    for idx, (materia, promedio) in enumerate(datos_reporte['promedios_materias'], start=2):
        ws_materias[f'A{idx}'] = materia
        ws_materias[f'B{idx}'] = round(promedio, 2)

    # Agregar gráfico de barras
    if datos_reporte['promedios_materias']:
        chart = BarChart()
        chart.title = "Promedios por Materia"
        chart.x_axis.title = "Materia"
        chart.y_axis.title = "Promedio"

        data = Reference(ws_materias, min_col=2, min_row=1,
                        max_row=len(datos_reporte['promedios_materias']) + 1)
        categories = Reference(ws_materias, min_col=1, min_row=2,
                              max_row=len(datos_reporte['promedios_materias']) + 1)

        chart.add_data(data, titles_from_data=True)
        chart.set_categories(categories)
        ws_materias.add_chart(chart, "D2")

    # HOJA 3: TOP ALUMNOS
    ws_alumnos = wb.create_sheet("Top Alumnos")

    # Sección promedios
    ws_alumnos['A1'] = 'TOP ALUMNOS POR PROMEDIO'
    ws_alumnos['A1'].font = Font(bold=True, size=12)
    ws_alumnos['A2'] = 'Alumno'
    ws_alumnos['B2'] = 'Promedio'

    for cell in ['A2', 'B2']:
        ws_alumnos[cell].fill = header_fill
        ws_alumnos[cell].font = header_font

    row = 3
    for alumno, promedio in datos_reporte['alumnos_top_promedio']:
        ws_alumnos[f'A{row}'] = alumno
        ws_alumnos[f'B{row}'] = round(promedio, 2)
        row += 1

    # Sección asistencias
    row += 2
    ws_alumnos[f'A{row}'] = 'TOP ALUMNOS POR ASISTENCIA'
    ws_alumnos[f'A{row}'].font = Font(bold=True, size=12)
    row += 1
    ws_alumnos[f'A{row}'] = 'Alumno'
    ws_alumnos[f'B{row}'] = 'Asistencia (%)'

    for cell in [f'A{row}', f'B{row}']:
        ws_alumnos[cell].fill = header_fill
        ws_alumnos[cell].font = header_font

    row += 1
    for alumno, asistencia in datos_reporte['alumnos_top_asistencia']:
        ws_alumnos[f'A{row}'] = alumno
        ws_alumnos[f'B{row}'] = round(asistencia, 2)
        row += 1

    # Ajustar anchos de columna
    for ws in [ws_resumen, ws_materias, ws_alumnos]:
        for column in ws.columns:
            max_length = 0
            column_letter = get_column_letter(column[0].column)
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(cell.value)
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column_letter].width = adjusted_width

    # Guardar en buffer
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    return buffer.getvalue()

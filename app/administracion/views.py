from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from datetime import datetime, timedelta

from main.utils import group_required
from .reportes_utils import (
    obtener_datos_reporte_academico,
    grafico_distribucion_notas,
    grafico_aprobados_desaprobados,
    grafico_evolucion_asistencias,
    grafico_comparativo_alumnos,
    generar_excel_reporte_academico
)
from main.utils import generar_certificado_pdf
from academico.models import Comision, AnioAcademico

@login_required
@group_required('Administrativo')
def home_administracion(request):
    return redirect('/admin/')


@login_required
@group_required('Administrativo', 'Docente')
def reporte_academico(request):
    """
    Vista principal del reporte académico con múltiples entidades y gráficos
    Muestra HTML interactivo con Chart.js

    Filtros:
    - Año Académico: obligatorio para filtrar el período
    - Comisión: opcional, para ver detalle de una comisión específica
    """
    # Obtener filtros desde request
    filtros = {}

    comision_id = request.GET.get('comision')
    anio_academico = request.GET.get('anio')

    # Convertir a int para comparaciones en template
    comision_seleccionada = int(comision_id) if comision_id else None
    anio_seleccionado = int(anio_academico) if anio_academico else None

    if comision_id:
        filtros['comision_id'] = int(comision_id)
    if anio_academico:
        filtros['anio_academico'] = int(anio_academico)

    # Obtener datos procesados
    datos_reporte = obtener_datos_reporte_academico(filtros)

    # Generar gráficos en base64 para preview (opcional)
    graficos = {}

    if datos_reporte['promedios_materias']:
        titulo = f"Promedios por Alumno - {datos_reporte.get('nombre_comision', '')}" if datos_reporte.get('vista_detalle') else "Promedios por Materia"
        graficos['distribucion_notas'] = grafico_distribucion_notas(
            datos_reporte['promedios_materias'],
            titulo=titulo
        )

    aprobados, desaprobados, regulares, en_curso = datos_reporte['estados_academicos']
    if aprobados > 0 or desaprobados > 0 or regulares > 0 or en_curso > 0:
        graficos['estados'] = grafico_aprobados_desaprobados(
            aprobados, desaprobados, regulares, en_curso
        )

    if datos_reporte['asistencias_por_mes']:
        graficos['asistencias'] = grafico_evolucion_asistencias(
            datos_reporte['asistencias_por_mes']
        )

    if datos_reporte['alumnos_top_promedio']:
        graficos['comparativo_alumnos'] = grafico_comparativo_alumnos(
            datos_reporte['alumnos_top_promedio'],
            metrica='promedio'
        )

    # Datos para filtros - filtrar comisiones por año si se seleccionó
    comisiones = Comision.objects.select_related('materia', 'anio_academico')
    if anio_seleccionado:
        comisiones = comisiones.filter(anio_academico_id=anio_seleccionado)

    comisiones = comisiones.order_by('materia__nombre', 'codigo')

    anios = AnioAcademico.objects.all().order_by('-fecha_inicio')

    contexto = {
        'datos': datos_reporte,
        'graficos': graficos,
        'comisiones': comisiones,
        'anios': anios,
        'filtros_aplicados': filtros,
        # Variables para mantener selección en template
        'anio_seleccionado': anio_seleccionado,
        'comision_seleccionada': comision_seleccionada,
    }

    return render(request, 'administracion/reporte_academico.html', contexto)


@login_required
@group_required('Administrativo', 'Docente')
def exportar_reporte_pdf(request):
    """
    Exporta el reporte académico a PDF con gráficos embebidos
    """
    # Obtener filtros
    filtros = {}
    if request.GET.get('comision'):
        filtros['comision_id'] = int(request.GET.get('comision'))
    if request.GET.get('anio'):
        filtros['anio_academico'] = int(request.GET.get('anio'))

    # Obtener datos
    datos_reporte = obtener_datos_reporte_academico(filtros)

    # Generar gráficos en base64
    graficos = {}

    if datos_reporte['promedios_materias']:
        titulo = f"Promedios por Alumno - {datos_reporte.get('nombre_comision', '')}" if datos_reporte.get('vista_detalle') else "Promedios por Materia"
        graficos['distribucion_notas'] = grafico_distribucion_notas(
            datos_reporte['promedios_materias'],
            titulo=titulo
        )

    aprobados, desaprobados, regulares, en_curso = datos_reporte['estados_academicos']
    if aprobados > 0 or desaprobados > 0 or regulares > 0 or en_curso > 0:
        graficos['estados'] = grafico_aprobados_desaprobados(
            aprobados, desaprobados, regulares, en_curso
        )

    if datos_reporte['asistencias_por_mes']:
        graficos['asistencias'] = grafico_evolucion_asistencias(
            datos_reporte['asistencias_por_mes']
        )

    if datos_reporte['alumnos_top_promedio']:
        graficos['comparativo_alumnos'] = grafico_comparativo_alumnos(
            datos_reporte['alumnos_top_promedio'],
            metrica='promedio'
        )

    # Contexto para PDF
    contexto = {
        'datos': datos_reporte,
        'graficos': graficos,
        'fecha_generacion': datetime.now().strftime('%d/%m/%Y %H:%M'),
    }

    # Generar PDF
    pdf_content = generar_certificado_pdf(
        contexto,
        template_name='administracion/reporte_academico_pdf.html'
    )

    # Respuesta
    response = HttpResponse(pdf_content, content_type='application/pdf')
    filename = f"reporte_academico_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    return response


@login_required
@group_required('Administrativo', 'Docente')
def exportar_reporte_excel(request):
    """
    Exporta el reporte académico a Excel con datos y gráficos
    """
    # Obtener filtros
    filtros = {}
    if request.GET.get('comision'):
        filtros['comision_id'] = int(request.GET.get('comision'))
    if request.GET.get('anio'):
        filtros['anio_academico'] = int(request.GET.get('anio'))

    # Obtener datos
    datos_reporte = obtener_datos_reporte_academico(filtros)

    # Generar Excel
    excel_content = generar_excel_reporte_academico(datos_reporte)

    # Respuesta
    response = HttpResponse(
        excel_content,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    filename = f"reporte_academico_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    return response
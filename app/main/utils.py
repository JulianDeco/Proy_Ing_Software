from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied

from django.shortcuts import render
from django.http import HttpResponse
from weasyprint import HTML
import tempfile
import os
from datetime import datetime
from django.conf import settings

def generar_certificado_pdf(contexto, template_name='admin/certificado_template.html'):
    from django.template.loader import render_to_string
    html_string = render_to_string(template_name, context=contexto)
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as output:
        HTML(base_url=settings.BASE_DIR, string=html_string).write_pdf(output.name)
        with open(output.name, 'rb') as f:
            pdf_content = f.read()
        os.unlink(output.name)

    return pdf_content

def crear_contexto_certificado(alumno, tipo_certificado, institucion, curso=None, materia=None):
    from academico.models import InscripcionAlumnoComision, Calificacion, Asistencia, TipoCalificacion
    from django.db.models import Avg, Count, Q

    nombre_archivo = institucion.logo.name
    nombre_archivo_solo = nombre_archivo.split('/')[-1]

    # Contexto base
    contexto = {
        'alumno': alumno,
        'tipo_certificado': tipo_certificado,
        'curso': curso,
        'materia': materia,
        'fecha_actual': datetime.now().strftime('%d/%m/%Y'),
        'anio_actual': datetime.now().year,
        'institucion': institucion,
        'logo': nombre_archivo_solo,
    }

    # Obtener inscripciones del alumno
    inscripciones = InscripcionAlumnoComision.objects.filter(
        alumno=alumno
    ).select_related('comision', 'comision__materia', 'comision__anio_academico')

    # Datos adicionales según tipo de certificado
    if tipo_certificado.lower() in ['certificado de asistencia', 'asistencia']:
        # Calcular porcentaje de asistencia general
        total_clases = Asistencia.objects.filter(
            alumno_comision__alumno=alumno
        ).count()

        clases_presentes = Asistencia.objects.filter(
            alumno_comision__alumno=alumno,
            esta_presente=True
        ).count()

        porcentaje_asistencia = (clases_presentes / total_clases * 100) if total_clases > 0 else 0

        contexto.update({
            'total_clases': total_clases,
            'clases_presentes': clases_presentes,
            'porcentaje_asistencia': round(porcentaje_asistencia, 2),
            'materias_cursadas': inscripciones
        })

    elif tipo_certificado.lower() in ['certificado de aprobación', 'aprobacion']:
        # Obtener materias aprobadas (nota >= 7 en FINAL)
        materias_aprobadas = []
        for inscripcion in inscripciones:
            calificacion_final = Calificacion.objects.filter(
                alumno_comision=inscripcion,
                tipo=TipoCalificacion.FINAL
            ).first()

            if calificacion_final and calificacion_final.nota >= 7:
                materias_aprobadas.append({
                    'materia': inscripcion.comision.materia,
                    'nota': calificacion_final.nota,
                    'fecha': calificacion_final.fecha_creacion,
                    'comision': inscripcion.comision
                })

        contexto.update({
            'materias_aprobadas': materias_aprobadas,
            'cantidad_aprobadas': len(materias_aprobadas)
        })

    elif tipo_certificado.lower() in ['certificado de examen', 'examen']:
        # Obtener calificaciones de exámenes finales
        examenes = []
        for inscripcion in inscripciones:
            calificaciones = Calificacion.objects.filter(
                alumno_comision=inscripcion
            ).order_by('-fecha_creacion')

            for calif in calificaciones:
                examenes.append({
                    'materia': inscripcion.comision.materia,
                    'tipo': calif.get_tipo_display(),
                    'nota': calif.nota,
                    'fecha': calif.fecha_creacion,
                    'resultado': 'Aprobado' if calif.nota >= 7 else 'No Aprobado'
                })

        contexto.update({
            'examenes': examenes,
            'cantidad_examenes': len(examenes)
        })

    elif tipo_certificado.lower() in ['certificado de alumno regular', 'alumno_regular']:
        # Verificar estado de regularidad
        materias_regulares = inscripciones.filter(
            estado_inscripcion='REGULAR'
        )

        contexto.update({
            'materias_regulares': materias_regulares,
            'cantidad_materias': materias_regulares.count(),
            'legajo': alumno.legajo,
            'estado': alumno.estado
        })

    elif tipo_certificado.lower() in ['certificado de buen comportamiento', 'buen_comportamiento']:
        # Datos de conducta (por ahora solo básicos)
        contexto.update({
            'legajo': alumno.legajo,
            'materias_cursadas': inscripciones,
            'cantidad_materias': inscripciones.count()
        })

    return contexto

def group_required(*group_names):
    def in_groups(u):
        if u.is_authenticated:
            if bool(u.groups.filter(name__in=group_names)) | u.is_superuser:
                return True
        raise PermissionDenied
    return user_passes_test(in_groups)


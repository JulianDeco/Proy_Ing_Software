from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied

from django.shortcuts import render
from django.http import HttpResponse
from weasyprint import HTML
import tempfile
import os
from datetime import datetime
from django.conf import settings

def generar_certificado_pdf(request, contexto, template_name='admin/certificado_template.html'):
    html_string = render(request, template_name=template_name, context=contexto).content.decode('utf-8')
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as output:
        HTML(base_url=settings.BASE_DIR, string=html_string).write_pdf(output.name)
        with open(output.name, 'rb') as f:
            pdf_content = f.read()
        os.unlink(output.name)
    
    return pdf_content

def crear_contexto_certificado(alumno, tipo_certificado, institucion,curso=None, materia=None):
    nombre_archivo = institucion.logo.name
    nombre_archivo_solo = nombre_archivo.split('/')[-1]
    return {
        'alumno': alumno,
        'tipo_certificado': tipo_certificado,
        'curso': curso,
        'materia': materia,
        'fecha_actual': datetime.now().strftime('%d/%m/%Y'),
        'anio_actual': datetime.now().year,
        'institucion': institucion,
        'logo':nombre_archivo_solo
    }

def group_required(*group_names):
    def in_groups(u):
        if u.is_authenticated:
            if bool(u.groups.filter(name__in=group_names)) | u.is_superuser:
                return True
        raise PermissionDenied
    return user_passes_test(in_groups)


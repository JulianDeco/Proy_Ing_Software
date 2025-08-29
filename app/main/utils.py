from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied

from django.template.loader import render_to_string
from django.http import HttpResponse
from weasyprint import HTML
import tempfile
import os
from datetime import datetime

def generar_certificado_pdf(contexto, template_name='admin/certificado_template.html'):
    # Renderizar el template HTML
    html_string = render_to_string(template_name, contexto)
    
    # Crear un archivo temporal
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as output:
        # Generar PDF con WeasyPrint
        HTML(string=html_string).write_pdf(output.name)
        
        # Leer el contenido del PDF
        with open(output.name, 'rb') as f:
            pdf_content = f.read()
        
        # Eliminar el archivo temporal
        os.unlink(output.name)
    
    return pdf_content

def crear_contexto_certificado(alumno, tipo_certificado, curso=None, materia=None):
    """
    Crea el contexto para el certificado
    """
    return {
        'alumno': alumno,
        'tipo_certificado': tipo_certificado,
        'curso': curso,
        'materia': materia,
        'fecha_actual': datetime.now().strftime('%d/%m/%Y'),
        'anio_actual': datetime.now().year,
        'institucion': {
            'nombre': 'Nombre de tu Institución',
            'direccion': 'Dirección de la institución',
            'logo': ''  # Ajusta esta ruta
        }
    }

def group_required(*group_names):
    def in_groups(u):
        if u.is_authenticated:
            if bool(u.groups.filter(name__in=group_names)) | u.is_superuser:
                return True
        raise PermissionDenied
    return user_passes_test(in_groups)


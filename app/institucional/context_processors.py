from .models import Institucion

def institucion_info(request):
    """
    Context processor para disponibilizar la información de la institución
    en todas las plantillas.
    """
    try:
        institucion = Institucion.objects.first()
    except Exception:
        institucion = None
        
    return {'institucion': institucion}

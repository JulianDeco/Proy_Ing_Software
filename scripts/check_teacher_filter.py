import os
import sys
import django

sys.path.append(os.path.join(os.path.dirname(__file__), '../app'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'main.settings')
django.setup()

from institucional.models import Persona, Empleado
from django.contrib.auth.models import Group

def check_filters():
    print("Checking filters for Teachers...")
    
    # Check if 'Docente' group exists
    if not Group.objects.filter(name='Docente').exists():
        print("Group 'Docente' does not exist.")
        return

    # Count teachers via Persona
    teachers_via_persona = Persona.objects.filter(empleado__usuario__groups__name='Docente')
    print(f"Teachers found via Persona filter: {teachers_via_persona.count()}")
    
    # List a few
    for p in teachers_via_persona[:5]:
        print(f" - {p.nombre} {p.apellido} (ID: {p.id})")

if __name__ == '__main__':
    check_filters()

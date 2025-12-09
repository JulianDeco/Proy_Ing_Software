import pytest
from academico.models import Alumno
from administracion.models import PlanEstudio
from django.utils import timezone

@pytest.mark.django_db
class TestAlumnoPlan:
    
    def test_alumno_unico_plan(self):
        # 1. Crear Planes
        plan1 = PlanEstudio.objects.create(nombre="Plan A", codigo="PLA")
        plan2 = PlanEstudio.objects.create(nombre="Plan B", codigo="PLB")
        
        # 2. Crear Alumno
        alumno = Alumno.objects.create(
            dni="12345678",
            nombre="Juan",
            apellido="Perez",
            fecha_nacimiento=timezone.now().date()
        )
        
        # 3. Asignar Plan 1
        alumno.plan_estudio = plan1
        alumno.save()
        
        alumno.refresh_from_db()
        assert alumno.plan_estudio == plan1
        
        # 4. Asignar Plan 2
        alumno.plan_estudio = plan2
        alumno.save()
        
        alumno.refresh_from_db()
        assert alumno.plan_estudio == plan2
        assert alumno.plan_estudio != plan1
        
        # 5. Verificar que el alumno solo tiene UN plan (implícito por el assert anterior, pero conceptualmente importante)

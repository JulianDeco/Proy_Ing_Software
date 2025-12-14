import os
import sys
import django
from datetime import date
from django.utils import timezone

# Setup Django environment
sys.path.append(os.path.join(os.path.dirname(__file__), '../app'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'main.settings')
django.setup()

from django.contrib.auth import get_user_model
from academico.models import (
    Alumno, Materia, Comision, InscripcionAlumnoComision, 
    AnioAcademico, PlanEstudio, EstadosAlumno, EstadoComision, 
    CondicionInscripcion, Calificacion, TipoCalificacion, Asistencia
)
from academico.services import ServiciosAcademico

def run_test():
    print("--- Iniciando Test de Regularización ---")
    
    # 1. Setup
    User = get_user_model()
    admin_user, _ = User.objects.get_or_create(email='admin_reg@test.com', defaults={'is_staff': True})
    
    anio, _ = AnioAcademico.objects.get_or_create(
        nombre="Anio Test Reg",
        defaults={'fecha_inicio': date(2025, 3, 1), 'fecha_fin': date(2025, 12, 15), 'activo': True, 'cierre_cursada_habilitado': True}
    )

    plan, _ = PlanEstudio.objects.get_or_create(nombre="Plan Test Reg", codigo="TEST-REG")
    materia, _ = Materia.objects.get_or_create(nombre="Materia Reg", codigo="MAT-REG", plan_estudio=plan)
    
    comision, _ = Comision.objects.get_or_create(
        codigo="COM-REG",
        defaults={
            'horario_inicio': "08:00", 'horario_fin': "12:00", 'dia_cursado': 1, 'turno': 'MAÑANA',
            'materia': materia, 'anio_academico': anio, 'estado': EstadoComision.EN_CURSO
        }
    )

    alumno, _ = Alumno.objects.get_or_create(
        dni="88888888", 
        defaults={'nombre': "Alumno", 'apellido': "Regular", 'legajo': "REG-001", 'email': "reg@test.com"}
    )

    # 2. Inscripción Inicial
    inscripcion, _ = InscripcionAlumnoComision.objects.update_or_create(
        alumno=alumno, comision=comision,
        defaults={'condicion': CondicionInscripcion.CURSANDO, 'estado_inscripcion': 'CURSANDO'}
    )
    print(f"[Estado Inicial] Condicion: {inscripcion.condicion}, Estado: {inscripcion.estado_inscripcion}")

    # 3. Simular Notas y Asistencia (Para aprobar)
    Calificacion.objects.create(alumno_comision=inscripcion, tipo=TipoCalificacion.PARCIAL, nota=8, fecha_creacion=timezone.now())
    Asistencia.objects.create(alumno_comision=inscripcion, esta_presente=True, fecha_asistencia=date(2025, 6, 1)) # 100% asistencia de 1 clase

    # 4. Regularizar Alumno
    print("\nRegularizando alumno...")
    condicion, msg = ServiciosAcademico.regularizar_alumno(inscripcion, admin_user, 6.0, 75)
    print(f"Resultado: {condicion} - {msg}")

    # 5. Verificar consistencia
    inscripcion.refresh_from_db()
    print(f"[Estado Final] Condicion: {inscripcion.condicion}, Estado: {inscripcion.estado_inscripcion}")

    if inscripcion.condicion == 'REGULAR' and inscripcion.estado_inscripcion == 'REGULAR':
        print("CHECK OK: Los estados son consistentes.")
    else:
        print("ERROR: Inconsistencia detectada.")

    # Cleanup
    inscripcion.delete()
    comision.delete()
    materia.delete()
    
if __name__ == '__main__':
    run_test()

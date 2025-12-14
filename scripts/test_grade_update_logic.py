import os
import sys
import django
from datetime import date, timedelta
from django.utils import timezone

# Setup Django environment
sys.path.append(os.path.join(os.path.dirname(__file__), '../app'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'main.settings')
django.setup()

from django.contrib.auth import get_user_model
from academico.models import (
    Alumno, Materia, Comision, InscripcionAlumnoComision, 
    MesaExamen, InscripcionMesaExamen, AnioAcademico, 
    PlanEstudio, EstadoComision, CondicionInscripcion, 
    Calificacion, TipoCalificacion
)

def run_test():
    print("--- Iniciando Test de Modificación de Nota ---")

    # 1. Setup
    anio, _ = AnioAcademico.objects.get_or_create(
        nombre="Anio Update",
        defaults={'fecha_inicio': date(2025, 3, 1), 'fecha_fin': date(2025, 12, 15), 'activo': True, 'nota_aprobacion': 6.0}
    )
    plan, _ = PlanEstudio.objects.get_or_create(nombre="Plan Update", codigo="UPD-001")
    materia, _ = Materia.objects.get_or_create(nombre="Materia Update", codigo="MAT-UPD", plan_estudio=plan)
    comision, _ = Comision.objects.get_or_create(
        codigo="COM-UPD",
        defaults={'horario_inicio': "08:00", 'horario_fin': "12:00", 'dia_cursado': 1, 'turno': 'MAÑANA',
                  'materia': materia, 'anio_academico': anio, 'estado': EstadoComision.FINALIZADA}
    )
    alumno, _ = Alumno.objects.get_or_create(
        dni="66666666", 
        defaults={'nombre': "Alumno", 'apellido': "Update", 'legajo': "UPD-001", 'email': "upd@test.com"}
    )
    cursada, _ = InscripcionAlumnoComision.objects.update_or_create(
        alumno=alumno, comision=comision,
        defaults={'condicion': CondicionInscripcion.REGULAR, 'estado_inscripcion': 'REGULAR'}
    )
    mesa = MesaExamen.objects.create(
        materia=materia, anio_academico=anio,
        fecha_examen=timezone.now(),
        fecha_limite_inscripcion=timezone.now() - timedelta(days=1),
        estado='ABIERTA'
    )
    
    # 2. Inscripción y carga inicial (simulada directa o via servicio anterior)
    inscripcion_mesa = InscripcionMesaExamen.objects.create(
        mesa_examen=mesa, alumno=alumno, condicion='REGULAR',
        estado_inscripcion='APROBADO', nota_examen=8.0 # Nota inicial 8
    )
    
    # YA NO Creamos la calificación inicial manual, el signal lo debe haber hecho.
    
    print("Nota inicial: 8.0. Verificando si el signal creó la calificación...")
    calif_inicial = Calificacion.objects.get(alumno_comision=cursada, tipo=TipoCalificacion.FINAL)
    print(f"Calificación inicial creada automágicamente: {calif_inicial.nota}")

    # 3. MODIFICACIÓN DIRECTA (Como si fuera el Admin)
    # Cambiamos la nota a 9.0
    print("Modificando nota en InscripcionMesaExamen a 9.0 (Directo save())...")
    inscripcion_mesa.nota_examen = 9.0
    inscripcion_mesa.save()

    # 4. Verificar Calificación
    calificacion = Calificacion.objects.get(alumno_comision=cursada, tipo=TipoCalificacion.FINAL)
    print(f"Nota en Mesa: {inscripcion_mesa.nota_examen}")
    print(f"Nota en Calificación: {calificacion.nota}")

    if calificacion.nota == 9.0:
        print("CHECK OK: La calificación se actualizó automáticamente.")
    else:
        print("FALLO: La calificación NO se actualizó (sigue en 8.0). Hay desincronización.")

    # Cleanup
    calificacion.delete()
    inscripcion_mesa.delete()
    mesa.delete()
    cursada.delete()
    comision.delete()
    materia.delete()

if __name__ == '__main__':
    run_test()

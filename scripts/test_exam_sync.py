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
    PlanEstudio, EstadosAlumno, EstadoComision, CondicionInscripcion, 
    Calificacion, TipoCalificacion
)
from academico.services import ServiciosAcademico

def run_test():
    print("--- Iniciando Test de Sincronización Examen -> Calificación ---")

    # 1. Setup
    User = get_user_model()
    admin_user, _ = User.objects.get_or_create(email='admin_sync@test.com', defaults={'is_staff': True})
    
    anio, _ = AnioAcademico.objects.get_or_create(
        nombre="Anio Sync",
        defaults={'fecha_inicio': date(2025, 3, 1), 'fecha_fin': date(2025, 12, 15), 'activo': True, 'nota_aprobacion': 6.0}
    )

    plan, _ = PlanEstudio.objects.get_or_create(nombre="Plan Sync", codigo="SYNC-001")
    materia, _ = Materia.objects.get_or_create(nombre="Materia Sync", codigo="MAT-SYNC", plan_estudio=plan)
    
    comision, _ = Comision.objects.get_or_create(
        codigo="COM-SYNC",
        defaults={
            'horario_inicio': "08:00", 'horario_fin': "12:00", 'dia_cursado': 1, 'turno': 'MAÑANA',
            'materia': materia, 'anio_academico': anio, 'estado': EstadoComision.FINALIZADA
        }
    )
    
    alumno, _ = Alumno.objects.get_or_create(
        dni="77777777", 
        defaults={'nombre': "Alumno", 'apellido': "Sync", 'legajo': "SYNC-001", 'email': "sync@test.com"}
    )

    # 2. Cursada Regular
    cursada, _ = InscripcionAlumnoComision.objects.update_or_create(
        alumno=alumno, comision=comision,
        defaults={'condicion': CondicionInscripcion.REGULAR, 'estado_inscripcion': 'REGULAR'}
    )

    # 3. Mesa de Examen
    mesa = MesaExamen.objects.create(
        materia=materia, anio_academico=anio,
        fecha_examen=timezone.now() + timedelta(days=2),
        fecha_limite_inscripcion=timezone.now() + timedelta(days=1),
        estado='ABIERTA'
    )
    
    InscripcionMesaExamen.objects.create(mesa_examen=mesa, alumno=alumno, condicion='REGULAR')
    inscripcion_mesa = InscripcionMesaExamen.objects.get(mesa_examen=mesa, alumno=alumno)

    # 4. Cargar Nota (Aprobado)
    print("Cargando nota 9 en Mesa de Examen...")
    ServiciosAcademico.cargar_nota_examen_final(inscripcion_mesa, 9.0, admin_user)

    # 5. Verificar Calificación
    calificacion = Calificacion.objects.filter(
        alumno_comision=cursada,
        tipo=TipoCalificacion.FINAL
    ).first()

    if calificacion:
        print(f"CHECK OK: Se creó la Calificación automáticamente. Nota: {calificacion.nota}")
    else:
        print("ERROR: No se creó la Calificación.")

    # Cleanup
    if calificacion: calificacion.delete()
    inscripcion_mesa.delete()
    mesa.delete()
    cursada.delete()
    comision.delete()
    materia.delete()

if __name__ == '__main__':
    run_test()

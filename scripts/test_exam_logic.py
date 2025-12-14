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
    PlanEstudio, EstadosAlumno, EstadoComision, CondicionInscripcion, EstadoMateria
)
from academico.services import ServiciosAcademico
from institucional.models import Institucion, Empleado, Usuario

def run_test():
    print("--- Iniciando Test de Lógica de Exámenes ---")

    # 1. Setup Básico (Año, Plan, Materia, Alumno, Docente)
    User = get_user_model()
    admin_user, _ = User.objects.get_or_create(email='admin_test@test.com', defaults={'is_staff': True, 'is_superuser': True})
    
    anio, _ = AnioAcademico.objects.get_or_create(
        nombre="Anio Test Exam",
        defaults={
            'fecha_inicio': date(2025, 3, 1),
            'fecha_fin': date(2025, 12, 15),
            'activo': True,
            'nota_aprobacion': 6.0
        }
    )

    plan, _ = PlanEstudio.objects.get_or_create(nombre="Plan Test", codigo="TEST-EXAM")
    materia, _ = Materia.objects.get_or_create(nombre="Materia Test", codigo="MAT-TEST", plan_estudio=plan)
    
    estado_alumno, _ = EstadosAlumno.objects.get_or_create(descripcion="Activo")
    alumno, _ = Alumno.objects.get_or_create(
        dni="99999999", 
        defaults={
            'nombre': "Alumno", 'apellido': "TestExam", 'legajo': "TEST-001", 
            'email': "alumno_test@exam.com", 'estado': estado_alumno
        }
    )

    # 2. Simular Cursada REGULAR
    print("\n[Paso 1] Creando Cursada con condición REGULAR...")
    # Necesitamos una comisión para crear la inscripción (aunque sea dummy)
    comision, _ = Comision.objects.get_or_create(
        codigo="COM-TEST-EXAM",
        defaults={
            'horario_inicio': "08:00", 'horario_fin': "12:00", 'dia_cursado': 1, 'turno': 'MAÑANA',
            'materia': materia, 'anio_academico': anio, 'estado': EstadoComision.FINALIZADA
        }
    )

    cursada, created = InscripcionAlumnoComision.objects.update_or_create(
        alumno=alumno,
        comision=comision,
        defaults={
            'condicion': CondicionInscripcion.REGULAR, # ALUMNO REGULAR
            'estado_inscripcion': EstadoMateria.REGULAR, # Materia regularizada
            'nota_cursada': 8.0,
            'fecha_regularizacion': timezone.now()
        }
    )
    print(f"   > Cursada creada/actualizada. Condición: {cursada.condicion}, Estado: {cursada.estado_inscripcion}")

    # 3. Crear Mesa de Examen
    print("\n[Paso 2] Creando Mesa de Examen...")
    mesa = MesaExamen.objects.create(
        materia=materia,
        anio_academico=anio,
        fecha_examen=timezone.now() + timedelta(days=5),
        fecha_limite_inscripcion=timezone.now() + timedelta(days=2),
        estado='ABIERTA',
        cupo_maximo=10,
        creado_por=admin_user
    )
    print(f"   > Mesa creada: {mesa}")

    # 4. Inscribir Alumno a Mesa
    print("\n[Paso 3] Inscribiendo Alumno a la Mesa...")
    success, msg = ServiciosAcademico.inscribir_alumno_mesa(alumno, mesa)
    if not success:
        print(f"   ERROR: Falló inscripción: {msg}")
        return

    inscripcion_mesa = InscripcionMesaExamen.objects.get(alumno=alumno, mesa_examen=mesa)
    print(f"   > Inscripción exitosa. Condición en mesa: {inscripcion_mesa.condicion}")
    
    if inscripcion_mesa.condicion != 'REGULAR':
        print("   ERROR: La condición en la mesa debería ser REGULAR.")

    # 5. Escenario A: Desaprobar Examen
    print("\n[Paso 4] Simulando DESAPROBACIÓN del examen (Nota: 2)...")
    success, msg = ServiciosAcademico.cargar_nota_examen_final(inscripcion_mesa, 2.0, admin_user)
    print(f"   > Resultado carga: {msg}")

    # Verificar estado de la cursada
    cursada.refresh_from_db()
    print(f"   > Estado Cursada tras desaprobar: {cursada.estado_inscripcion}")
    print(f"   > Condición Cursada tras desaprobar: {cursada.condicion}")

    if cursada.estado_inscripcion == EstadoMateria.REGULAR:
        print("   CHECK OK: El estado de la materia se mantuvo en REGULAR.")
    else:
        print(f"   ERROR: El estado de la materia cambió a {cursada.estado_inscripcion} (debería ser REGULAR).")

    # 6. Escenario B: Aprobar Examen (re-intento o corrección)
    print("\n[Paso 5] Simulando APROBACIÓN del examen (Nota: 8)...")
    # Para simplificar, actualizamos la misma inscripción de mesa
    success, msg = ServiciosAcademico.cargar_nota_examen_final(inscripcion_mesa, 8.0, admin_user)
    print(f"   > Resultado carga: {msg}")

    # Verificar estado de la cursada
    cursada.refresh_from_db()
    print(f"   > Estado Cursada tras aprobar: {cursada.estado_inscripcion}")
    print(f"   > Nota Final en Cursada: {cursada.nota_final}")

    if cursada.estado_inscripcion == EstadoMateria.APROBADA:
        print("   CHECK OK: El estado de la materia cambió a APROBADA.")
    else:
        print(f"   ERROR: El estado de la materia es {cursada.estado_inscripcion} (debería ser APROBADA).")

    # Limpieza
    print("\n--- Limpiando datos de prueba ---")
    inscripcion_mesa.delete()
    mesa.delete()
    cursada.delete()
    comision.delete()
    # alumno.delete() # Dejar alumno para otros tests si se quiere

if __name__ == '__main__':
    run_test()

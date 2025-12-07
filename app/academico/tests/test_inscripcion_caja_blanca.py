import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone
from academico.models import (
    InscripcionAlumnoComision, Alumno, Comision, Materia,
    AnioAcademico, PlanEstudio, Turno
)
from institucional.models import Persona, Empleado, Usuario # Modificado: Importar Empleado

@pytest.mark.django_db
class TestInscripcionCajaBlanca:
    """
    Pruebas de Caja Blanca - Ruta Básica
    Método bajo prueba: InscripcionAlumnoComision.clean()
    Complejidad Ciclomática: V(G) = 6
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        """Configuración inicial para todas las pruebas"""
        # Crear año académico
        self.anio = AnioAcademico.objects.create(
            nombre="2025", # Corregido: anio es nombre en AnioAcademico
            fecha_inicio=timezone.now().date(),
            fecha_fin=timezone.now().date() + timezone.timedelta(days=365),
            cierre_cursada_habilitado=True # Asegurar para algunos tests futuros
        )

        # Crear plan de estudio
        self.plan = PlanEstudio.objects.create(
            nombre="Tecnicatura en Desarrollo",
            codigo="TDS-2025"
        )

        # Crear materias
        self.algoritmos = Materia.objects.create(
            codigo="ALG",
            nombre="Algoritmos",
            plan_estudio=self.plan
        )
        self.ed = Materia.objects.create(
            codigo="ED",
            nombre="Estructuras de Datos",
            plan_estudio=self.plan
        )
        self.ed.correlativas.add(self.algoritmos)

        self.prog1 = Materia.objects.create(
            codigo="PROG1",
            nombre="Programación I",
            plan_estudio=self.plan
        )
        self.prog2 = Materia.objects.create(
            codigo="PROG2",
            nombre="Programación II",
            plan_estudio=self.plan
        )
        self.prog2.correlativas.add(self.prog1)

        # Crear docente (usando Empleado directamente)
        self.docente = Empleado.objects.create(
            dni="12345678",
            nombre="Profesor",
            apellido="Test"
        )

        # Crear alumnos
        self.alumnos = []
        for i in range(1, 7):
            alumno = Alumno.objects.create(
                dni=f"4000000{i}",
                nombre=f"Alumno{i}",
                apellido="Test",
                legajo=f"2025-{i:05d}",
                # plan_estudio=self.plan # Alumno no tiene plan_estudio en academico.models
                fecha_nacimiento=timezone.now().date() - timezone.timedelta(days=365*20)
            )
            self.alumnos.append(alumno)

    # ============================================
    # CASO DE PRUEBA 1: Ruta 1
    # ============================================
    def test_cp01_inscripcion_sin_restricciones(self):
        """
        CP01 - Ruta 1: Inscripción válida sin cupo_maximo ni correlativas
        Sentencias: [1, 2, 3, 7, 8, 13]
        Decisiones: [3-NO, 8-NO]
        """
        # Crear comisión sin cupo máximo (simulado con cupo alto)
        comision = Comision.objects.create(
            codigo="ALG-2025-1",
            materia=self.algoritmos,
            anio_academico=self.anio,
            docente=self.docente,
            horario_inicio=timezone.now().time(),
            horario_fin=(timezone.now() + timezone.timedelta(hours=2)).time(),
            dia_cursado=1,
            turno=Turno.MANANA,
            cupo_maximo=100  # Modificado: Cupo alto en lugar de None
        )

        # Crear inscripción
        inscripcion = InscripcionAlumnoComision(
            alumno=self.alumnos[0],
            comision=comision
        )

        # Ejecutar validación
        try:
            inscripcion.clean()
            resultado = "EXITO"
        except ValidationError as e:
            resultado = f"ERROR: {e}"

        # Verificar resultado
        assert resultado == "EXITO", f"Se esperaba EXITO pero se obtuvo: {resultado}"

        # Guardar inscripción
        inscripcion.save()
        assert InscripcionAlumnoComision.objects.count() == 1

    # ============================================
    # CASO DE PRUEBA 2: Ruta 2
    # ============================================
    def test_cp02_inscripcion_con_cupo_disponible(self):
        """
        CP02 - Ruta 2: Inscripción válida con cupo_maximo disponible
        Sentencias: [1, 2, 3, 4, 5, 7, 8, 13]
        Decisiones: [3-SI, 5-NO, 8-NO]
        """
        # Crear comisión con cupo
        comision = Comision.objects.create(
            codigo="BD-2025-1",
            materia=Materia.objects.create(
                codigo="BD",
                nombre="Base de Datos",
                plan_estudio=self.plan
            ),
            anio_academico=self.anio,
            docente=self.docente,
            horario_inicio=timezone.now().time(),
            horario_fin=(timezone.now() + timezone.timedelta(hours=2)).time(),
            dia_cursado=2,
            turno=Turno.TARDE,
            cupo_maximo=30
        )

        # Inscribir 15 alumnos (cupo disponible)
        for i in range(15):
            InscripcionAlumnoComision.objects.create(
                alumno=Alumno.objects.create(
                    dni=f"5000000{i}",
                    nombre=f"Previo{i}",
                    apellido="Test",
                    legajo=f"2024-{i:05d}",
                    fecha_nacimiento=timezone.now().date() - timezone.timedelta(days=365*20)
                ),
                comision=comision
            )

        # Intentar nueva inscripción
        inscripcion = InscripcionAlumnoComision(
            alumno=self.alumnos[1],
            comision=comision
        )

        # Ejecutar validación
        try:
            inscripcion.clean()
            resultado = "EXITO"
        except ValidationError as e:
            resultado = f"ERROR: {e}"

        # Verificar resultado
        assert resultado == "EXITO"
        inscripcion.save()
        assert comision.inscripcionalumnocomision_set.count() == 16

    # ============================================
    # CASO DE PRUEBA 3: Ruta 3
    # ============================================
    def test_cp03_rechazo_por_cupo_lleno(self):
        """
        CP03 - Ruta 3: Rechazo por cupo lleno
        Sentencias: [1, 2, 3, 4, 5, 6]
        Decisiones: [3-SI, 5-SI]
        """
        # Crear comisión con cupo
        comision = Comision.objects.create(
            codigo="PROG-2025-1",
            materia=self.prog2,
            anio_academico=self.anio,
            docente=self.docente,
            horario_inicio=timezone.now().time(),
            horario_fin=(timezone.now() + timezone.timedelta(hours=2)).time(),
            dia_cursado=3,
            turno=Turno.NOCHE,
            cupo_maximo=20
        )

        # Llenar el cupo (20 inscriptos)
        for i in range(20):
            InscripcionAlumnoComision.objects.create(
                alumno=Alumno.objects.create(
                    dni=f"6000000{i}",
                    nombre=f"Lleno{i}",
                    apellido="Test",
                    legajo=f"2024-{100+i:05d}",
                    fecha_nacimiento=timezone.now().date() - timezone.timedelta(days=365*20)
                ),
                comision=comision
            )

        # Intentar inscripción con cupo lleno
        inscripcion = InscripcionAlumnoComision(
            alumno=self.alumnos[2],
            comision=comision
        )

        # Ejecutar validación
        with pytest.raises(ValidationError) as exc_info:
            inscripcion.clean()

        # Verificar mensaje de error
        error_msg = str(exc_info.value)
        assert "ha alcanzado su capacidad máxima" in error_msg
        assert "20 estudiantes" in error_msg

    # ============================================
    # CASO DE PRUEBA 4: Ruta 4
    # ============================================
    def test_cp04_inscripcion_con_correlativa_aprobada(self):
        """
        CP04 - Ruta 4: Inscripción con correlativa aprobada
        Sentencias: [1, 2, 3, 7, 8, 9, 10, 12, 13]
        Decisiones: [3-NO, 8-SI, 10-SI]
        """
        # Crear comisión de Algoritmos
        comision_alg = Comision.objects.create(
            codigo="ALG-2024-1",
            materia=self.algoritmos,
            anio_academico=self.anio,
            docente=self.docente,
            horario_inicio=timezone.now().time(),
            horario_fin=(timezone.now() + timezone.timedelta(hours=2)).time(),
            dia_cursado=4, # Jueves
            turno=Turno.MANANA, # Mañana
        )

        # Inscribir y aprobar Algoritmos
        InscripcionAlumnoComision.objects.create(
            alumno=self.alumnos[3],
            comision=comision_alg,
            estado_inscripcion='APROBADA'
        )

        # Crear comisión de Estructuras de Datos
        comision_ed = Comision.objects.create(
            codigo="ED-2025-1",
            materia=self.ed,
            anio_academico=self.anio,
            docente=self.docente,
            horario_inicio=timezone.now().time(),
            horario_fin=(timezone.now() + timezone.timedelta(hours=2)).time(),
            dia_cursado=5, # Viernes
            turno=Turno.TARDE, # Tarde
        )

        # Intentar inscripción en ED (tiene correlativa aprobada)
        inscripcion = InscripcionAlumnoComision(
            alumno=self.alumnos[3],
            comision=comision_ed
        )

        # Ejecutar validación
        try:
            inscripcion.clean()
            resultado = "EXITO"
        except ValidationError as e:
            resultado = f"ERROR: {e}"

        # Verificar resultado
        assert resultado == "EXITO"
        inscripcion.save()

    # ============================================
    # CASO DE PRUEBA 5: Ruta 5
    # ============================================
    def test_cp05_rechazo_por_correlativa_no_aprobada(self):
        """
        CP05 - Ruta 5: Rechazo por correlativa no aprobada
        Sentencias: [1, 2, 3, 7, 8, 9, 10, 11]
        Decisiones: [3-NO, 8-SI, 10-NO]
        """
        # Crear comisión de Estructuras de Datos
        comision_ed = Comision.objects.create(
            codigo="ED-2025-1",
            materia=self.ed,
            anio_academico=self.anio,
            docente=self.docente,
            horario_inicio=timezone.now().time(),
            horario_fin=(timezone.now() + timezone.timedelta(hours=2)).time(),
            dia_cursado=6, # Sábado
            turno=Turno.NOCHE, # Noche
        )

        # Intentar inscripción SIN tener aprobada Algoritmos
        inscripcion = InscripcionAlumnoComision(
            alumno=self.alumnos[4],  # No tiene aprobada Algoritmos
            comision=comision_ed
        )

        # Ejecutar validación
        with pytest.raises(ValidationError) as exc_info:
            inscripcion.clean()

        # Verificar mensaje de error
        error_msg = str(exc_info.value)
        assert "debe aprobar la materia correlativa" in error_msg
        assert "Algoritmos" in error_msg

    # ============================================
    # CASO DE PRUEBA 6: Ruta 6
    # ============================================
    def test_cp06_inscripcion_completa_validaciones(self):
        """
        CP06 - Ruta 6: Inscripción con todas las validaciones exitosas
        Sentencias: [1, 2, 3, 4, 5, 7, 8, 9, 10, 12, 13]
        Decisiones: [3-SI, 5-NO, 8-SI, 10-SI]
        """
        # Crear comisión de Programación I
        comision_prog1 = Comision.objects.create(
            codigo="PROG1-2024-1",
            materia=self.prog1,
            anio_academico=self.anio,
            docente=self.docente,
            horario_inicio=timezone.now().time(),
            horario_fin=(timezone.now() + timezone.timedelta(hours=2)).time(),
            dia_cursado=1,
            turno=Turno.MANANA,
        )

        # Inscribir y aprobar Programación I
        InscripcionAlumnoComision.objects.create(
            alumno=self.alumnos[5],
            comision=comision_prog1,
            estado_inscripcion='APROBADA'
        )

        # Crear comisión de Programación II con cupo
        comision_prog2 = Comision.objects.create(
            codigo="PROG2-2025-1",
            materia=self.prog2,
            anio_academico=self.anio,
            docente=self.docente,
            horario_inicio=timezone.now().time(),
            horario_fin=(timezone.now() + timezone.timedelta(hours=2)).time(),
            dia_cursado=2,
            turno=Turno.TARDE,
            cupo_maximo=25
        )

        # Inscribir 10 alumnos previos
        for i in range(10):
            InscripcionAlumnoComision.objects.create(
                alumno=Alumno.objects.create(
                    dni=f"7000000{i}",
                    nombre=f"Prog{i}",
                    apellido="Test",
                    legajo=f"2024-{200+i:05d}",
                    fecha_nacimiento=timezone.now().date() - timezone.timedelta(days=365*20)
                ),
                comision=comision_prog2
            )

        # Intentar inscripción con cupo disponible y correlativa aprobada
        inscripcion = InscripcionAlumnoComision(
            alumno=self.alumnos[5],
            comision=comision_prog2
        )

        # Ejecutar validación
        try:
            inscripcion.clean()
            resultado = "EXITO"
        except ValidationError as e:
            resultado = f"ERROR: {e}"

        # Verificar resultado
        assert resultado == "EXITO"
        inscripcion.save()
        assert comision_prog2.inscripcionalumnocomision_set.count() == 11 # Modificado

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone
from academico.models import (
    InscripcionAlumnoComision, Alumno, Comision, Materia,
    AnioAcademico, PlanEstudio, Turno
)
from academico.forms import InscripcionAlumnoComisionAdminForm
from institucional.models import Persona, Empleado, Usuario

@pytest.mark.django_db
class TestInscripcionCajaNegra:
    """
    Pruebas de Caja Negra - Partición Equivalente y Valores Límite
    Componente bajo prueba: InscripcionAlumnoComisionAdminForm (Interfaz Admin)
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        """Configuración inicial"""
        # Crear usuario admin
        self.admin_user = Usuario(
            email='admin@test.com',
            is_staff=True,
            is_superuser=True
        )
        self.admin_user.set_password('admin123')
        self.admin_user.save()

        # Año académico
        self.anio = AnioAcademico.objects.create(
            nombre="2025",
            fecha_inicio=timezone.now().date(),
            fecha_fin=timezone.now().date() + timezone.timedelta(days=365)
        )

        # Plan de estudio
        self.plan = PlanEstudio.objects.create(
            nombre="Tecnicatura",
            codigo="TEC-2025"
        )

        # Materias
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

        self.prog = Materia.objects.create(
            codigo="PROG",
            nombre="Programación",
            plan_estudio=self.plan
        )

        # Docente
        self.docente = Empleado.objects.create(
            dni="12345678",
            nombre="Profesor",
            apellido="Test"
        )

        # Comisiones
        self.comision_alg = Comision.objects.create(
            codigo="ALG-2025-1",
            materia=self.algoritmos,
            anio_academico=self.anio,
            docente=self.docente,
            cupo_maximo=100,
            horario_inicio=timezone.now().time(),
            horario_fin=(timezone.now() + timezone.timedelta(hours=2)).time(),
            dia_cursado=1,
            turno=Turno.MANANA,
        )

        self.comision_bd = Comision.objects.create(
            codigo="BD-2025-1",
            materia=Materia.objects.create(
                codigo="BD",
                nombre="Base de Datos",
                plan_estudio=self.plan
            ),
            anio_academico=self.anio,
            docente=self.docente,
            cupo_maximo=30,
            horario_inicio=timezone.now().time(),
            horario_fin=(timezone.now() + timezone.timedelta(hours=2)).time(),
            dia_cursado=2,
            turno=Turno.TARDE,
        )

        self.comision_prog = Comision.objects.create(
            codigo="PROG-2025-1",
            materia=self.prog,
            anio_academico=self.anio,
            docente=self.docente,
            cupo_maximo=20,
            horario_inicio=timezone.now().time(),
            horario_fin=(timezone.now() + timezone.timedelta(hours=2)).time(),
            dia_cursado=3,
            turno=Turno.NOCHE,
        )

        # Alumnos
        self.crear_alumnos()

    def crear_alumnos(self):
        """Crear alumnos de prueba"""
        dnis = [
            "40123456", "35678901", "42345678", "43456789",
            "45678901", "46789012"
        ]
        self.alumnos = {}

        for idx, dni in enumerate(dnis, 1):
            alumno = Alumno.objects.create(
                dni=dni,
                nombre=f"Alumno{dni}",
                apellido="Test",
                legajo=f"2025-{idx:05d}",
                fecha_nacimiento=timezone.now().date() - timezone.timedelta(days=365*20)
            )
            self.alumnos[dni] = alumno

    # ============================================
    # CASOS VÁLIDOS
    # ============================================

        data = {
            'alumno': self.alumnos['40123456'].pk,
            'comision': self.comision_alg.pk,
            'estado_inscripcion': 'CURSANDO',
            'condicion': 'CURSANDO'
        }
        form = InscripcionAlumnoComisionAdminForm(data=data)
        assert form.is_valid() is True
        form.save()
        assert InscripcionAlumnoComision.objects.filter(
            alumno__dni='40123456',
            comision__codigo='ALG-2025-1'
        ).exists()

    def test_cv02_inscripcion_con_cupo_disponible(self):
        """CV02: Inscripción con cupo disponible"""
        # Inscribir 15 alumnos previamente
        for i in range(15):
            alumno = Alumno.objects.create(
                dni=f"5000000{i}",
                nombre=f"Previo{i}",
                apellido="Test",
                legajo=f"2024-{i:05d}",
                fecha_nacimiento=timezone.now().date() - timezone.timedelta(days=365*20)
            )
            InscripcionAlumnoComision.objects.create(
                alumno=alumno,
                comision=self.comision_bd
            )

        data = {
            'alumno': self.alumnos['35678901'].pk,
            'comision': self.comision_bd.pk,
            'estado_inscripcion': 'CURSANDO',
            'condicion': 'CURSANDO'
        }
        form = InscripcionAlumnoComisionAdminForm(data=data)
        assert form.is_valid() is True
        form.save()
        assert self.comision_bd.inscripcionalumnocomision_set.count() == 16

    def test_cv03_inscripcion_con_correlativa_aprobada(self):
        """CV03: Inscripción con correlativa aprobada"""
        # Inscribir y aprobar Algoritmos
        InscripcionAlumnoComision.objects.create(
            alumno=self.alumnos['42345678'],
            comision=self.comision_alg,
            estado_inscripcion='APROBADA'
        )

        # Crear comisión de ED
        comision_ed = Comision.objects.create(
            codigo="ED-2025-1",
            materia=self.ed,
            anio_academico=self.anio,
            docente=self.docente,
            horario_inicio=timezone.now().time(),
            horario_fin=(timezone.now() + timezone.timedelta(hours=2)).time(),
            dia_cursado=4,
            turno=Turno.MANANA,
        )

        data = {
            'alumno': self.alumnos['42345678'].pk,
            'comision': comision_ed.pk,
            'estado_inscripcion': 'CURSANDO',
            'condicion': 'CURSANDO'
        }
        form = InscripcionAlumnoComisionAdminForm(data=data)
        assert form.is_valid() is True

    def test_cv04_inscripcion_limite_cupo(self):
        """CV04: Inscripción en el límite de cupo (valor límite)"""
        # Llenar hasta 19 inscriptos (cupo=20)
        for i in range(19):
            alumno = Alumno.objects.create(
                dni=f"6000000{i}",
                nombre=f"Limite{i}",
                apellido="Test",
                legajo=f"2024-{100+i:05d}",
                fecha_nacimiento=timezone.now().date() - timezone.timedelta(days=365*20)
            )
            InscripcionAlumnoComision.objects.create(
                alumno=alumno,
                comision=self.comision_prog
            )

        data = {
            'alumno': self.alumnos['43456789'].pk,
            'comision': self.comision_prog.pk,
            'estado_inscripcion': 'CURSANDO',
            'condicion': 'CURSANDO'
        }
        form = InscripcionAlumnoComisionAdminForm(data=data)
        assert form.is_valid() is True
        form.save()
        assert self.comision_prog.inscripcionalumnocomision_set.count() == 20

    # ============================================
    # CASOS INVÁLIDOS
    # ============================================

    def test_ci04_cupo_completo(self):
        """CI04: Cupo completo"""
        # Llenar completamente el cupo
        for i in range(20):
            alumno = Alumno.objects.create(
                dni=f"7000000{i}",
                nombre=f"Lleno{i}",
                apellido="Test",
                legajo=f"2024-{200+i:05d}",
                fecha_nacimiento=timezone.now().date() - timezone.timedelta(days=365*20)
            )
            InscripcionAlumnoComision.objects.create(
                alumno=alumno,
                comision=self.comision_prog
            )

        data = {
            'alumno': self.alumnos['40123456'].pk,
            'comision': self.comision_prog.pk,
            'estado_inscripcion': 'CURSANDO',
            'condicion': 'CURSANDO'
        }
        form = InscripcionAlumnoComisionAdminForm(data=data)
        
        assert form.is_valid() is False
        # Verificar que el error sea de cupo (capturado en ValidationError y propagado al form)
        assert any("capacidad máxima" in str(e) for e in form.non_field_errors())

    def test_ci05_correlativa_no_aprobada(self):
        """CI05: Correlativa no aprobada"""
        # Crear comisión de ED
        comision_ed = Comision.objects.create(
            codigo="ED-2025-1",
            materia=self.ed,
            anio_academico=self.anio,
            docente=self.docente,
            horario_inicio=timezone.now().time(),
            horario_fin=(timezone.now() + timezone.timedelta(hours=2)).time(),
            dia_cursado=5,
            turno=Turno.TARDE,
        )

        data = {
            'alumno': self.alumnos['45678901'].pk,  # No tiene aprobada Algoritmos
            'comision': comision_ed.pk,
            'estado_inscripcion': 'CURSANDO',
            'condicion': 'CURSANDO'
        }
        form = InscripcionAlumnoComisionAdminForm(data=data)
        
        assert form.is_valid() is False
        assert any("correlativa" in str(e) for e in form.non_field_errors())

    def test_ci06_inscripcion_duplicada(self):
        """CI06: Inscripción duplicada"""
        # Limpiar cualquier inscripción existente para asegurar estado limpio
        InscripcionAlumnoComision.objects.filter(
            alumno=self.alumnos['40123456'],
            comision=self.comision_alg
        ).delete()

        # Primera inscripción
        InscripcionAlumnoComision.objects.create(
            alumno=self.alumnos['40123456'],
            comision=self.comision_alg
        )

        data = {
            'alumno': self.alumnos['40123456'].pk,
            'comision': self.comision_alg.pk,
            'estado_inscripcion': 'CURSANDO',
            'condicion': 'CURSANDO'
        }
        form = InscripcionAlumnoComisionAdminForm(data=data)
        
        assert form.is_valid() is False
        # Error de unicidad suele estar en field errors o non_field_errors dependiendo de Django ver.
        # unique_together normalmente va a non_field_errors
        errors = str(form.errors.as_data()).lower()
        assert "ya existe" in errors or "already exists" in errors

    def test_ci09_alumno_vacio(self):
        """CI09: Alumno vacío (Equivalente a DNI vacío)"""
        data = {
            'alumno': '',
            'comision': self.comision_alg.pk,
            'estado_inscripcion': 'CURSANDO',
            'condicion': 'CURSANDO'
        }
        form = InscripcionAlumnoComisionAdminForm(data=data)
        assert form.is_valid() is False
        assert 'alumno' in form.errors

    def test_ci10_comision_vacia(self):
        """CI10: Comisión vacía"""
        data = {
            'alumno': self.alumnos['40123456'].pk,
            'comision': '',
            'estado_inscripcion': 'CURSANDO',
            'condicion': 'CURSANDO'
        }
        form = InscripcionAlumnoComisionAdminForm(data=data)
        assert form.is_valid() is False
        assert 'comision' in form.errors
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.models import Group
from django.db import transaction
from institucional.models import Usuario, Persona, Empleado, Institucion, PreguntaFrecuente
from administracion.models import PlanEstudio
from academico.models import (
    AnioAcademico, Materia, Comision, Alumno, 
    InscripcionAlumnoComision, CalendarioAcademico, Asistencia, 
    Calificacion, TipoCalificacion, Turno, Dia, EstadoComision, EstadosAlumno,
    MesaExamen, InscripcionMesaExamen
)
import random
from datetime import timedelta, date, time

class Command(BaseCommand):
    help = 'Genera datos de prueba específicos para casos de testeo de inscripciones y correlativas.'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING('Iniciando proceso de seed de casos de prueba...'))
        
        with transaction.atomic():
            self.limpiar_datos_test()
            self.crear_estructura_base_test()
            
            anio = self.crear_academico_test()
            
            # Docente de prueba
            docente_user = Usuario.objects.create_user('docente_test@test.com', 'docente123')
            docente_user.groups.add(Group.objects.get(name='Docente'))
            docente_test = Empleado.objects.create(
                dni="30000000", nombre="Profe", apellido="Testing",
                usuario=docente_user
            )

            # Materias con correlativas
            plan = PlanEstudio.objects.get(codigo="PLAN-TEST")
            materia_base = Materia.objects.create(
                nombre="Introducción a la Programación", codigo="PROG001", plan_estudio=plan,
                descripcion="Materia base sin correlativas"
            )
            materia_intermedia = Materia.objects.create(
                nombre="Programación Avanzada", codigo="PROG002", plan_estudio=plan,
                descripcion="Requiere PROG001"
            )
            materia_intermedia.correlativas.add(materia_base)
            
            materia_final = Materia.objects.create(
                nombre="Desarrollo Web", codigo="WEB001", plan_estudio=plan,
                descripcion="Requiere PROG002"
            )
            materia_final.correlativas.add(materia_intermedia)

            # Comisiones de prueba
            comision_prog001 = Comision.objects.create(
                codigo="C-PROG001-2025-1", horario_inicio=time(9,0), horario_fin=time(11,0),
                dia_cursado=Dia.LUNES, turno=Turno.MANANA, docente=docente_test, materia=materia_base,
                aula="Aula 101", cupo_maximo=30, estado=EstadoComision.EN_CURSO, anio_academico=anio
            )
            comision_prog002 = Comision.objects.create(
                codigo="C-PROG002-2025-1", horario_inicio=time(11,0), horario_fin=time(13,0),
                dia_cursado=Dia.MARTES, turno=Turno.MANANA, docente=docente_test, materia=materia_intermedia,
                aula="Aula 102", cupo_maximo=30, estado=EstadoComision.EN_CURSO, anio_academico=anio
            )
            comision_web001 = Comision.objects.create(
                codigo="C-WEB001-2025-1", horario_inicio=time(14,0), horario_fin=time(16,0),
                dia_cursado=Dia.MIERCOLES, turno=Turno.TARDE, docente=docente_test, materia=materia_final,
                aula="Aula 103", cupo_maximo=30, estado=EstadoComision.EN_CURSO, anio_academico=anio
            )

            # Estado de alumno por defecto
            estado_activo, _ = EstadosAlumno.objects.get_or_create(descripcion="Activo")

            # Alumno 1: Con Materias Aprobadas (PROG001 y PROG002)
            user_aprobado = Usuario.objects.create_user('alumno_aprobado@test.com', 'alumno123')
            user_aprobado.groups.add(Group.objects.get(name='Alumno'))
            alumno_aprobado = Alumno.objects.create(
                dni="41000000", nombre="Matias", apellido="Aprobado", legajo="2025-001A",
                email='alumno_aprobado@test.com', estado=estado_activo, fecha_nacimiento=date(2000,1,1)
            )
            # Inscribir y aprobar PROG001
            insc_prog001_aprobado = InscripcionAlumnoComision.objects.create(
                alumno=alumno_aprobado, comision=comision_prog001,
                estado_inscripcion='REGULAR', condicion='APROBADO' # Simula aprobada
            )
            Calificacion.objects.create(
                alumno_comision=insc_prog001_aprobado, tipo=TipoCalificacion.FINAL, nota=8,
                fecha_creacion=timezone.now()
            )
            # Inscribir y aprobar PROG002
            insc_prog002_aprobado = InscripcionAlumnoComision.objects.create(
                alumno=alumno_aprobado, comision=comision_prog002,
                estado_inscripcion='REGULAR', condicion='APROBADO' # Simula aprobada
            )
            Calificacion.objects.create(
                alumno_comision=insc_prog002_aprobado, tipo=TipoCalificacion.FINAL, nota=7,
                fecha_creacion=timezone.now()
            )

            # Alumno 2: Con correlativa NO aprobada (PROG001 desaprobada)
            user_desaprobado = Usuario.objects.create_user('alumno_desaprobado@test.com', 'alumno123')
            user_desaprobado.groups.add(Group.objects.get(name='Alumno'))
            alumno_desaprobado = Alumno.objects.create(
                dni="42000000", nombre="Pedro", apellido="Desaprobado", legajo="2025-002D",
                email='alumno_desaprobado@test.com', estado=estado_activo, fecha_nacimiento=date(2000,1,1)
            )
            # Inscribir y desaprobar PROG001
            insc_prog001_desaprobado = InscripcionAlumnoComision.objects.create(
                alumno=alumno_desaprobado, comision=comision_prog001,
                estado_inscripcion='REGULAR', condicion='DESAPROBADO' # Simula desaprobada
            )
            Calificacion.objects.create(
                alumno_comision=insc_prog001_desaprobado, tipo=TipoCalificacion.FINAL, nota=3,
                fecha_creacion=timezone.now()
            )

            # Alumno 3: Nuevo alumno sin inscripciones previas
            user_nuevo = Usuario.objects.create_user('alumno_nuevo@test.com', 'alumno123')
            user_nuevo.groups.add(Group.objects.get(name='Alumno'))
            alumno_nuevo = Alumno.objects.create(
                dni="43000000", nombre="Laura", apellido="Nueva", legajo="2025-003N",
                email='alumno_nuevo@test.com', estado=estado_activo, fecha_nacimiento=date(2000,1,1)
            )

            # Alumno 4: Con condición 'LIBRE' en PROG001
            user_libre = Usuario.objects.create_user('alumno_libre@test.com', 'alumno123')
            user_libre.groups.add(Group.objects.get(name='Alumno'))
            alumno_libre = Alumno.objects.create(
                dni="44000000", nombre="Sofia", apellido="Libre", legajo="2025-004L",
                email='alumno_libre@test.com', estado=estado_activo, fecha_nacimiento=date(2000,1,1)
            )
            insc_prog001_libre = InscripcionAlumnoComision.objects.create(
                alumno=alumno_libre, comision=comision_prog001,
                estado_inscripcion='REGULAR', condicion='LIBRE' # Simula libre
            )


            self.stdout.write(self.style.SUCCESS('¡Datos de prueba de casos específicos creados exitosamente!'))

    def limpiar_datos_test(self):
        self.stdout.write("Limpiando datos específicos de prueba...")
        try:
            with transaction.atomic():
                # Borrar solo los objetos relacionados con este seed
                Usuario.objects.filter(email__endswith='@test.com').delete()
                PlanEstudio.objects.filter(codigo="PLAN-TEST").delete()
                AnioAcademico.objects.filter(nombre="Ciclo Lectivo Test").delete()
                # Otros objetos creados (Materias, Comisiones, Alumnos, Inscripciones, Calificaciones)
                # se borrarán en cascada o se recrearán para evitar conflictos.
                Materia.objects.filter(codigo__startswith="PROG").delete()
                Materia.objects.filter(codigo__startswith="WEB").delete()
                Comision.objects.filter(codigo__startswith="C-").delete()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error al limpiar datos: {e}"))

    def crear_estructura_base_test(self):
        # Institución (si no existe, para evitar errores)
        if not Institucion.objects.exists():
            Institucion.objects.create(
                nombre="Instituto de Test",
                direccion="Calle Falsa 123",
                nro_telefono="+54 11 9999-9999",
                email_contacto="test@instituto.edu.ar"
            )
        
        # Grupos
        grupos = ['Administrativo', 'Docente', 'Alumno']
        for g in grupos:
            Group.objects.get_or_create(name=g)

        # Superusuario (si no existe)
        if not Usuario.objects.filter(email='admin@admin.com').exists():
            admin = Usuario.objects.create_superuser('admin@admin.com', 'admin123')
            admin.groups.add(Group.objects.get(name='Administrativo'))
        
        # Administrativo Empleado (si no existe)
        if not Usuario.objects.filter(email='secretaria@instituto.edu').exists():
            adm_user = Usuario.objects.create_user('secretaria@instituto.edu', 'admin123')
            adm_user.groups.add(Group.objects.get(name='Administrativo'))
            Empleado.objects.create(
                dni="10000001", nombre="Admin", apellido="Test",
                usuario=adm_user
            )

    def crear_academico_test(self):
        anio = AnioAcademico.objects.create(
            nombre="Ciclo Lectivo Test",
            fecha_inicio=date(2025, 3, 1),
            fecha_fin=date(2025, 12, 15),
            activo=True,
            cierre_cursada_habilitado=True
        )
        
        # Calendario básico para el año de prueba
        inicio = anio.fecha_inicio
        fin = anio.fecha_fin
        delta = timedelta(days=1)
        
        fechas = []
        while inicio <= fin:
            if inicio.weekday() < 5: # Lunes a Viernes
                fechas.append(CalendarioAcademico(
                    anio_academico=anio,
                    fecha=inicio,
                    es_dia_clase=True
                ))
            inicio += delta
        CalendarioAcademico.objects.bulk_create(fechas, ignore_conflicts=True)

        PlanEstudio.objects.create(nombre="Plan de Prueba", codigo="PLAN-TEST")
        
        return anio

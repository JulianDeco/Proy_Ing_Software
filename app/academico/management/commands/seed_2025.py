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
    help = 'Genera datos de prueba para el año 2025 (Mockup completo)'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING('Iniciando proceso de seed... Esto borrará los datos existentes.'))
        
        # 1. Limpiar DB (fuera de la transacción de creación para asegurar commit)
        self.limpiar_datos()
        
        with transaction.atomic():
            # 2. Crear Grupos y Usuarios Base
            self.crear_estructura_base()
            
            # 3. Configuración Académica 2025
            anio = self.crear_academico()
            
            # 4. Personas (Docentes y Alumnos)
            docentes = self.crear_docentes()
            alumnos = self.crear_alumnos()
            
            # 5. Comisiones y Cursada
            self.crear_cursada(anio, docentes, alumnos)

        self.stdout.write(self.style.SUCCESS('¡Datos de prueba 2025 creados exitosamente!'))

    def limpiar_datos(self):
        self.stdout.write("Limpiando base de datos...")
        # Orden seguro de borrado
        try:
            with transaction.atomic():
                InscripcionMesaExamen.objects.all().delete()
                MesaExamen.objects.all().delete()
                Calificacion.objects.all().delete()
                Asistencia.objects.all().delete()
                InscripcionAlumnoComision.objects.all().delete()
                Comision.objects.all().delete()
                Materia.objects.all().delete()
                PlanEstudio.objects.all().delete()
                CalendarioAcademico.objects.all().delete()
                AnioAcademico.objects.all().delete()
                # Pago.objects.all().delete() # Eliminado
                Alumno.objects.all().delete()
                Empleado.objects.all().delete()
                Usuario.objects.all().delete() 
                Institucion.objects.all().delete()
                PreguntaFrecuente.objects.all().delete()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error al limpiar datos: {e}"))

    def crear_estructura_base(self):
        # Institución
        Institucion.objects.create(
            nombre="Instituto Tecnológico 2025",
            direccion="Av. Innovación 123",
            nro_telefono="+54 11 1234-5678",
            email_contacto="info@instituto2025.edu.ar"
        )
        
        # Preguntas Frecuentes
        PreguntaFrecuente.objects.create(pregunta="¿Cómo recupero mi clave?", respuesta="Contacte a soporte.", orden=1)
        PreguntaFrecuente.objects.create(pregunta="¿Cuándo cierran las notas?", respuesta="Al finalizar el cuatrimestre.", orden=2)

        # Grupos
        grupos = ['Administrativo', 'Docente', 'Alumno']
        for g in grupos:
            Group.objects.get_or_create(name=g)

        # Superusuario
        if not Usuario.objects.filter(email='admin@admin.com').exists():
            admin = Usuario.objects.create_superuser('admin@admin.com', 'admin123')
            admin.groups.add(Group.objects.get(name='Administrativo'))
        
        # Administrativo Empleado
        adm_user = Usuario.objects.create_user('secretaria@instituto.edu', 'admin123')
        adm_user.groups.add(Group.objects.get(name='Administrativo'))
        Empleado.objects.create(
            dni="10000000", nombre="Ana", apellido="Secretaria",
            usuario=adm_user
        )

    def crear_academico(self):
        # Año 2025
        anio = AnioAcademico.objects.create(
            nombre="Ciclo Lectivo 2025",
            fecha_inicio=date(2025, 3, 1),
            fecha_fin=date(2025, 12, 15),
            activo=True,
            cierre_cursada_habilitado=True # Habilitado para pruebas
        )
        
        # Crear calendario básico (Lunes a Viernes clase)
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

        # Plan
        plan = PlanEstudio.objects.create(nombre="Tecnicatura en Software", codigo="TS-2025")
        
        # Materias
        nombres_materias = [
            "Programación I", "Matemática", "Sistemas Operativos", 
            "Base de Datos I", "Ingeniería de Software", "Programación II"
        ]
        
        for idx, nombre in enumerate(nombres_materias):
            Materia.objects.create(
                nombre=nombre, 
                codigo=f"MAT-{100+idx}", 
                plan_estudio=plan,
                descripcion="Materia fundamental"
            )
            
        return anio

    def crear_docentes(self):
        docentes = []
        nombres = ["Juan", "Maria", "Carlos", "Laura", "Pedro", "Sofia", "Luis", "Ana", "Jorge", "Lucia"]
        apellidos = ["Perez", "Gomez", "Rodriguez", "Fernandez", "Lopez", "Diaz", "Martinez", "Garcia", "Sánchez", "Romero"]
        
        for i in range(10):
            email = f"profe{i}@instituto.edu"
            user = Usuario.objects.create_user(email, 'docente123')
            user.groups.add(Group.objects.get(name='Docente'))
            
            docente = Empleado.objects.create(
                dni=f"2000000{i}",
                nombre=random.choice(nombres),
                apellido=random.choice(apellidos),
                usuario=user
            )
            docentes.append(docente)
        return docentes

    def crear_alumnos(self):
        alumnos = []
        estado, _ = EstadosAlumno.objects.get_or_create(descripcion="Activo")
        nombres = ["Kevin", "Brenda", "Brian", "Jessica", "Jonathan", "Micaela", "Ezequiel", "Camila", "Matias", "Florencia", 
                   "Lucas", "Agustina", "Facundo", "Rocio", "Nicolas", "Antonella", "Franco", "Julieta", "Maxi", "Sol"]
        
        for i in range(20): # 20 alumnos
            email = f"alumno{i}@instituto.edu"
            user = Usuario.objects.create_user(email, 'alumno123')
            user.groups.add(Group.objects.get(name='Alumno'))
            
            alumno = Alumno.objects.create(
                dni=f"400000{i:02d}",
                nombre=random.choice(nombres),
                apellido=f"Estudiante{i}",
                legajo=f"2025-{i:04d}",
                email=email,
                estado=estado,
                fecha_nacimiento=date(2000, 1, 1)
            )
            alumnos.append(alumno)
        return alumnos

    def crear_cursada(self, anio, docentes, alumnos):
        materias = Materia.objects.all()
        turnos = [Turno.MANANA, Turno.TARDE, Turno.NOCHE]
        dias = [1, 2, 3, 4, 5] # Lunes a Viernes
        
        comisiones = []
        
        # Crear 10 comisiones variadas
        for i, materia in enumerate(materias):
            docente = docentes[i % len(docentes)]
            turno = turnos[i % 3]
            
            comision = Comision.objects.create(
                codigo=f"{materia.codigo}-{anio.nombre[-4:]}-{i+1}",
                horario_inicio=time(8,0) if turno == Turno.MANANA else (time(14,0) if turno == Turno.TARDE else time(19,0)),
                horario_fin=time(12,0) if turno == Turno.MANANA else (time(18,0) if turno == Turno.TARDE else time(22,0)),
                dia_cursado=dias[i % 5],
                turno=turno,
                docente=docente,
                materia=materia,
                aula=f"Aula {100+i}",
                cupo_maximo=30,
                estado=EstadoComision.EN_CURSO if i < 8 else EstadoComision.FINALIZADA, # 2 finalizadas
                anio_academico=anio
            )
            comisiones.append(comision)
            
            # Inscribir alumnos (entre 5 y 15 por comisión)
            alumnos_comision = random.sample(alumnos, k=random.randint(5, 15))
            
            for alumno in alumnos_comision:
                inscripcion = InscripcionAlumnoComision.objects.create(
                    alumno=alumno,
                    comision=comision,
                    estado_inscripcion='CURSANDO' if comision.estado == 'EN_CURSO' else 'REGULAR',
                    condicion='CURSANDO' if comision.estado == 'EN_CURSO' else random.choice(['REGULAR', 'LIBRE'])
                )
                
                # Generar Asistencias
                # (Simulado: solo algunas fechas recientes)
                fechas_clase = CalendarioAcademico.objects.filter(
                    anio_academico=anio, 
                    fecha__week_day=comision.dia_cursado + 1,
                    fecha__lte=timezone.now().date()
                ).order_by('-fecha')[:5] # Últimas 5 clases
                
                for fecha_obj in fechas_clase:
                    Asistencia.objects.update_or_create(
                        alumno_comision=inscripcion,
                        fecha_asistencia=fecha_obj.fecha,
                        defaults={'esta_presente': random.choice([True, True, True, False])} # 75% asistencia prob
                    )
                
                # Generar Calificaciones
                if random.choice([True, False]): # Algunos tienen notas
                    Calificacion.objects.create(
                        alumno_comision=inscripcion,
                        tipo=TipoCalificacion.PARCIAL,
                        nota=random.randint(2, 10),
                        fecha_creacion=timezone.now()
                    )
                    if random.choice([True, False]):
                        Calificacion.objects.create(
                            alumno_comision=inscripcion,
                            tipo=TipoCalificacion.TRABAJO_PRACTICO,
                            nota=random.randint(4, 10),
                            fecha_creacion=timezone.now()
                        )

    def crear_pagos(self, alumnos):
        # Placeholder vacío
        pass

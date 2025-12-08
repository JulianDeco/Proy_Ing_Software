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
    help = 'Genera un conjunto completo de datos históricos para 2023, 2024 y 2025, incluyendo diversos casos de prueba.'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING('Iniciando proceso de seed con historial completo...'))
        
        # Limpieza inicial de datos
        self.limpiar_todos_los_datos()
        
        with transaction.atomic():
            # Crear estructura base (grupos, institución, admin)
            self.crear_estructura_base()
            
            # Crear planes de estudio y materias (con correlativas)
            plan = self.crear_plan_y_materias()
            
            # Crear docentes
            docentes = self.crear_docentes()

            # Diccionarios para almacenar años, alumnos, comisiones para acceso fácil
            anios = {}
            alumnos_por_anio = {}
            comisiones_por_anio = {}

            for year in range(2023, 2026):
                self.stdout.write(self.style.NOTICE(f"--- Generando datos para el año {year} ---"))
                
                # Año académico y calendario
                anio_academico = self.crear_anio_academico_y_calendario(year)
                anios[year] = anio_academico
                
                # Alumnos para este año (algunos nuevos, otros que continúan)
                alumnos_por_anio[year] = self.crear_alumnos_para_anio(year, anios, alumnos_por_anio)
                
                # Comisiones para este año
                comisiones_por_anio[year] = self.crear_comisiones_para_anio(anio_academico, plan, docentes)
                
                # Inscripciones, calificaciones y asistencias para este año
                self.simular_cursada_y_resultados(anio_academico, alumnos_por_anio[year], comisiones_por_anio[year])
            
            # Casos de prueba específicos adicionales (más allá de la simulación general)
            self.crear_casos_especificos(anios, docentes, plan)

        self.stdout.write(self.style.SUCCESS('¡Seed con historial completo generado exitosamente!'))

    def limpiar_todos_los_datos(self):
        self.stdout.write("Limpiando toda la base de datos...")
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
                Alumno.objects.all().delete()
                Empleado.objects.all().delete()
                Usuario.objects.all().delete() 
                Institucion.objects.all().delete()
                PreguntaFrecuente.objects.all().delete()
                Group.objects.all().delete() # Borrar grupos también para empezar de cero
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error al limpiar datos: {e}"))

    def crear_estructura_base(self):
        self.stdout.write("Creando estructura base (grupos, institución, admin)...")
        # Grupos
        grupos = ['Administrativo', 'Docente', 'Alumno']
        for g in grupos:
            Group.objects.get_or_create(name=g)

        # Institución
        Institucion.objects.create(
            nombre="Instituto Histórico UAI",
            direccion="Av. Siempre Viva 742",
            nro_telefono="+54 11 9876-5432",
            email_contacto="contacto@instituto-historico.edu.ar"
        )
        
        # Superusuario
        if not Usuario.objects.filter(email='admin@admin.com').exists():
            admin = Usuario.objects.create_superuser('admin@admin.com', 'admin123')
            admin.groups.add(Group.objects.get(name='Administrativo'))
        
        # Administrativo Empleado
        if not Usuario.objects.filter(email='secretaria@instituto.edu').exists():
            adm_user = Usuario.objects.create_user('secretaria@instituto.edu', 'admin123', is_staff=True)
            adm_user.groups.add(Group.objects.get(name='Administrativo'))
            Empleado.objects.create(dni="10000000", nombre="Admin", apellido="General", usuario=adm_user)

    def crear_plan_y_materias(self):
        self.stdout.write("Creando plan de estudio y materias con correlativas...")
        plan = PlanEstudio.objects.create(nombre="Ingeniería de Software", codigo="ING-SOFT")
        
        # Materias base (sin correlativas)
        materia_algoritmos = Materia.objects.create(nombre="Algoritmos y Estructuras de Datos", codigo="AED", plan_estudio=plan, descripcion="Base de programación")
        materia_calculo = Materia.objects.create(nombre="Cálculo I", codigo="CAL1", plan_estudio=plan, descripcion="Base matemática")
        materia_intro_comp = Materia.objects.create(nombre="Introducción a la Computación", codigo="ICOMP", plan_estudio=plan, descripcion="Conceptos fundamentales")

        # Materias con una correlativa
        materia_prog1 = Materia.objects.create(nombre="Programación I", codigo="PROG1", plan_estudio=plan, descripcion="Primer lenguaje")
        materia_prog1.correlativas.add(materia_algoritmos)

        materia_bdd1 = Materia.objects.create(nombre="Base de Datos I", codigo="BDD1", plan_estudio=plan, descripcion="Modelado de datos")
        materia_bdd1.correlativas.add(materia_intro_comp)

        # Materias con múltiples correlativas
        materia_prog2 = Materia.objects.create(nombre="Programación II", codigo="PROG2", plan_estudio=plan, descripcion="Programación orientada a objetos")
        materia_prog2.correlativas.add(materia_prog1)

        materia_arq = Materia.objects.create(nombre="Arquitectura de Computadoras", codigo="ARQCOMP", plan_estudio=plan, descripcion="Hardware y software")
        materia_arq.correlativas.add(materia_intro_comp)

        materia_ing_soft = Materia.objects.create(nombre="Ingeniería de Software I", codigo="ISOF1", plan_estudio=plan, descripcion="Ciclo de vida del software")
        materia_ing_soft.correlativas.add(materia_prog1, materia_bdd1) # Requiere Prog1 y BDD1

        return plan

    def crear_docentes(self):
        self.stdout.write("Creando docentes...")
        docentes = []
        nombres = ["Juan", "Maria", "Carlos", "Laura", "Pedro", "Sofia"]
        apellidos = ["Gomez", "Perez", "Rodriguez", "Fernandez", "Lopez", "Diaz"]
        
        for i in range(len(nombres)):
            email = f"docente{i+1}@instituto.edu"
            user, created = Usuario.objects.get_or_create(email=email)
            if created:
                user.set_password('docente123')
                user.save()
                user.groups.add(Group.objects.get(name='Docente'))
            else: # Si el usuario ya existe, asegurarse de que tenga la contraseña correcta y el grupo
                user.set_password('docente123')
                user.save()
                if not user.groups.filter(name='Docente').exists():
                    user.groups.add(Group.objects.get(name='Docente'))
            docente, created = Empleado.objects.get_or_create(
                dni=f"2000000{i}", defaults={
                    'nombre': nombres[i], 'apellido': apellidos[i], 'usuario': user
                })
            docentes.append(docente)
        return docentes

    def crear_anio_academico_y_calendario(self, year):
        self.stdout.write(f"Creando Año Académico {year} y su calendario...")
        anio, created = AnioAcademico.objects.get_or_create(
            nombre=f"Ciclo Lectivo {year}",
            defaults={
                'fecha_inicio': date(year, 3, 1),
                'fecha_fin': date(year, 12, 15),
                'activo': (year == timezone.now().year),
                'cierre_cursada_habilitado': True
            }
        )
        
        # Si el año es nuevo, o el calendario está vacío, poblarlo
        if created or not CalendarioAcademico.objects.filter(anio_academico=anio).exists():
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
        return anio

    def crear_alumnos_para_anio(self, year, anios_existentes, alumnos_existentes_por_anio):
        self.stdout.write(f"Creando alumnos para {year} (nuevos y continuadores)...")
        alumnos_este_anio = []
        estado_activo, _ = EstadosAlumno.objects.get_or_create(descripcion="Activo")
        
        nombres = ["Matias", "Brenda", "Carlos", "Diana", "Esteban", "Florencia", "Gabriel", "Hebe", "Ignacio", "Julia"]

        # Alumnos que continúan de años anteriores
        if year > 2023:
            for prev_alumno in alumnos_existentes_por_anio[year - 1]:
                if random.random() < 0.7: # 70% de chance de que un alumno continúe
                    alumnos_este_anio.append(prev_alumno)
        
        # Alumnos nuevos
        num_nuevos = 5 if year == 2023 else random.randint(2, 4)
        for i in range(num_nuevos):
            idx = (year * 100 + i) % len(nombres) # Asegurar nombres variados
            email = f"alumno{year}-{i+1}@instituto.edu" # Definir email aquí
            
            alumno, created = Alumno.objects.get_or_create(
                legajo=f"{year}-{i+1:04d}", defaults={
                    'dni': f"40{year}{i:04d}", 'nombre': nombres[idx], 'apellido': f"Apellido{year}{i}",
                    'email': email, 'estado': estado_activo, 'fecha_nacimiento': date(year - 20, 1, 1),
                })
            alumnos_este_anio.append(alumno)
        
        return alumnos_este_anio

    def crear_comisiones_para_anio(self, anio_academico, plan, docentes):
        self.stdout.write(f"Creando comisiones para {anio_academico.nombre} (distribución equitativa a docentes)...")
        comisiones_creadas = []
        materias = list(Materia.objects.filter(plan_estudio=plan))
        random.shuffle(materias) # Aleatorizar materias para una distribución más variada

        # Determinar el estado de las comisiones (Finalizada para años anteriores, En curso para el actual)
        estado_comision_defecto = EstadoComision.EN_CURSO
        if anio_academico.nombre == "Ciclo Lectivo 2023" or anio_academico.nombre == "Ciclo Lectivo 2024":
            estado_comision_defecto = EstadoComision.FINALIZADA

        # Asignar a cada docente un número inicial de comisiones (4-5)
        docentes_con_materias = {docente: [] for docente in docentes}
        
        materias_disponibles = list(materias)
        random.shuffle(materias_disponibles)

        # Primera ronda: garantizar un mínimo de comisiones por docente
        for docente in docentes:
            num_comisiones_a_asignar = random.randint(4, 5)
            # Asegurarse de no asignar más materias de las disponibles
            num_comisiones_a_asignar = min(num_comisiones_a_asignar, len(materias_disponibles))

            for _ in range(num_comisiones_a_asignar):
                if materias_disponibles:
                    materia = materias_disponibles.pop(0) # Tomar la primera materia disponible
                    docentes_con_materias[docente].append(materia)

        # Segunda ronda: asignar las materias restantes (si las hay) de forma equitativa
        docente_idx = 0
        while materias_disponibles:
            materia = materias_disponibles.pop(0)
            docente = docentes[docente_idx % len(docentes)]
            docentes_con_materias[docente].append(materia)
            docente_idx += 1

        # Crear las comisiones basadas en la asignación
        comision_counter = 1
        for docente, materias_asignadas in docentes_con_materias.items():
            for materia in materias_asignadas:
                turno = random.choice([Turno.MANANA, Turno.TARDE, Turno.NOCHE])
                dia = random.choice([Dia.LUNES, Dia.MARTES, Dia.MIERCOLES, Dia.JUEVES, Dia.VIERNES])
                
                comision = Comision.objects.create(
                    codigo=f"{materia.codigo}-{anio_academico.nombre[-4:]}-{comision_counter:02d}",
                    horario_inicio=time(8,0) if turno == Turno.MANANA else (time(14,0) if turno == Turno.TARDE else time(19,0)),
                    horario_fin=time(12,0) if turno == Turno.MANANA else (time(18,0) if turno == Turno.TARDE else time(22,0)),
                    dia_cursado=dia,
                    turno=turno,
                    docente=docente,
                    materia=materia,
                    aula=f"Aula {100 + comision_counter}",
                    cupo_maximo=random.randint(20, 30),
                    estado=estado_comision_defecto,
                    anio_academico=anio_academico
                )
                comisiones_creadas.append(comision)
                comision_counter += 1
        return comisiones_creadas

    def simular_cursada_y_resultados(self, anio_academico, alumnos, comisiones):
        self.stdout.write(f"Simulando cursada y resultados para {anio_academico.nombre}...")
        
        # Obtener todas las materias y sus correlativas de una vez
        materias_con_correlativas = {materia.pk: set(materia.correlativas.values_list('pk', flat=True)) 
                                     for materia in Materia.objects.all().prefetch_related('correlativas')}

        for alumno in alumnos:
            # Mantener un registro de materias aprobadas por el alumno
            materias_aprobadas_pk = set(InscripcionAlumnoComision.objects.filter(
                alumno=alumno,
                condicion='APROBADO',
                comision__anio_academico__fecha_inicio__lt=anio_academico.fecha_inicio # Aprobadas en años anteriores
            ).values_list('comision__materia__pk', flat=True))

            random.shuffle(comisiones) # Aleatorizar el orden de inscripción a comisiones
            for comision in comisiones:
                # 70% de chance de inscribirse en una materia
                if random.random() < 0.7:
                    materia_pk = comision.materia.pk
                    
                    # Verificar correlativas
                    requiere_correlativas = materias_con_correlativas.get(materia_pk, set())
                    puede_cursar = requiere_correlativas.issubset(materias_aprobadas_pk)
                    
                    if not puede_cursar:
                        # Si no puede cursar por correlativas, no lo inscribimos o lo marcamos de alguna forma
                        # Para este seed, simplemente no lo inscribimos si no cumple correlativas
                        continue
                    
                    condicion_inscripcion = 'CURSANDO'
                    condicion_final = 'REGULAR'

                    if comision.estado == EstadoComision.FINALIZADA:
                        condicion_inscripcion = 'REGULAR' # Ya se evaluó el estado final
                        if random.random() < 0.7: # 70% chance de aprobar
                            condicion_final = 'APROBADO'
                            materias_aprobadas_pk.add(materia_pk) # Actualizar materias aprobadas
                        elif random.random() < 0.9: # 20% chance de ser LIBRE
                            condicion_final = 'LIBRE'
                        else: # 10% chance de DESAPROBADO
                            condicion_final = 'DESAPROBADO'
                    
                    inscripcion, created = InscripcionAlumnoComision.objects.get_or_create(
                        alumno=alumno,
                        comision=comision,
                        defaults={
                            'estado_inscripcion': condicion_inscripcion,
                            'condicion': condicion_final
                        }
                    )
                    
                    if not created: # Si ya existía la inscripción, actualizarla
                        inscripcion.estado_inscripcion = condicion_inscripcion
                        inscripcion.condicion = condicion_final
                        inscripcion.save()

                    # Generar Asistencias (si la comisión no ha finalizado o si ya se generaron)
                    if comision.estado == EstadoComision.EN_CURSO or random.random() < 0.8: # Generar asistencias históricas
                        fechas_clase = CalendarioAcademico.objects.filter(
                            anio_academico=anio_academico, 
                            fecha__week_day=comision.dia_cursado + 1,
                            fecha__lte=timezone.now().date() if comision.estado == EstadoComision.EN_CURSO else anio_academico.fecha_fin
                        ).order_by('fecha')
                        
                        num_clases_simuladas = min(fechas_clase.count(), random.randint(5, 15)) # Simular algunas clases
                        for fecha_obj in random.sample(list(fechas_clase), num_clases_simuladas):
                            Asistencia.objects.update_or_create(
                                alumno_comision=inscripcion,
                                fecha_asistencia=fecha_obj.fecha,
                                defaults={'esta_presente': random.choice([True, True, True, False])} # 75% presente
                            )
                    
                    # Generar Calificaciones
                    if (comision.estado == EstadoComision.FINALIZADA and (condicion_final == 'APROBADO' or condicion_final == 'DESAPROBADO')) or (comision.estado == EstadoComision.EN_CURSO and random.random() < 0.5):
                        
                        # Generar 1-2 calificaciones parciales/TP
                        num_parciales_o_tps = random.randint(0, 2)
                        for n in range(1, num_parciales_o_tps + 1):
                            nota = random.randint(4, 10) if condicion_final == 'APROBADO' else random.randint(1, 5)
                            Calificacion.objects.create(
                                alumno_comision=inscripcion,
                                tipo=random.choice([TipoCalificacion.PARCIAL, TipoCalificacion.TRABAJO_PRACTICO]),
                                numero=n, # Usar número incremental para la restricción única
                                nota=nota,
                                fecha_creacion=anio_academico.fecha_inicio + timedelta(days=random.randint(30, (anio_academico.fecha_fin - anio_academico.fecha_inicio).days - 30))
                            )

                        # Generar una calificación final si aplica
                        if condicion_final == 'APROBADO' or condicion_final == 'DESAPROBADO':
                            nota = random.randint(6, 10) if condicion_final == 'APROBADO' else random.randint(1, 5)
                            Calificacion.objects.create(
                                alumno_comision=inscripcion,
                                tipo=TipoCalificacion.FINAL,
                                numero=1, # Solo una calificación final, así que número 1 está bien
                                nota=nota,
                                fecha_creacion=anio_academico.fecha_inicio + timedelta(days=random.randint( (anio_academico.fecha_fin - anio_academico.fecha_inicio).days - 60, (anio_academico.fecha_fin - anio_academico.fecha_inicio).days - 10))
                            )

    def crear_casos_especificos(self, anios, docentes, plan):
        self.stdout.write("Creando casos de prueba específicos (alumno con correlativas no aprobadas, etc.)...")
        
        # Obtener materias para los casos de prueba
        materia_algoritmos = Materia.objects.get(codigo="AED")
        materia_prog1 = Materia.objects.get(codigo="PROG1")
        materia_prog2 = Materia.objects.get(codigo="PROG2")
        materia_ing_soft = Materia.objects.get(codigo="ISOF1") # Requiere Prog1 y BDD1
        materia_bdd1 = Materia.objects.get(codigo="BDD1")

        # Año 2025
        anio_2025 = anios[2025]
        docente_test = random.choice(docentes)
        estado_activo, _ = EstadosAlumno.objects.get_or_create(descripcion="Activo")

        # Comisiones para casos específicos en 2025
        comision_prog1_2025 = Comision.objects.get_or_create(
            codigo="PROG1-2025-ESP", defaults={
                'horario_inicio': time(9,0), 'horario_fin': time(11,0), 'dia_cursado': Dia.LUNES, 
                'turno': Turno.MANANA, 'docente': docente_test, 'materia': materia_prog1,
                'aula': "Esp-1", 'cupo_maximo': 20, 'estado': EstadoComision.EN_CURSO, 'anio_academico': anio_2025
            })[0]
        
        comision_prog2_2025 = Comision.objects.get_or_create(
            codigo="PROG2-2025-ESP", defaults={
                'horario_inicio': time(11,0), 'horario_fin': time(13,0), 'dia_cursado': Dia.MARTES, 
                'turno': Turno.MANANA, 'docente': docente_test, 'materia': materia_prog2,
                'aula': "Esp-2", 'cupo_maximo': 20, 'estado': EstadoComision.EN_CURSO, 'anio_academico': anio_2025
            })[0]
        
        comision_ing_soft_2025 = Comision.objects.get_or_create(
            codigo="ISOF1-2025-ESP", defaults={
                'horario_inicio': time(14,0), 'horario_fin': time(16,0), 'dia_cursado': Dia.MIERCOLES, 
                'turno': Turno.TARDE, 'docente': docente_test, 'materia': materia_ing_soft,
                'aula': "Esp-3", 'cupo_maximo': 20, 'estado': EstadoComision.EN_CURSO, 'anio_academico': anio_2025
            })[0]

        # --- CASO 1: Alumno con correlativa NO aprobada para PROG1 (debe fallar inscripción manual a PROG2) ---
        email_no_aprobado = 'alumno_corr_fail@test.com'
        alumno_no_aprobado = Alumno.objects.create(
            dni="45000000", nombre="Correlativa", apellido="Fallida", legajo="2025-FAIL",
            email=email_no_aprobado, estado=estado_activo, fecha_nacimiento=date(2000,1,1)
        )
        # Inscribirlo en Algoritmos y "aprobarlo" (simular aprobación en 2024)
        anio_2024 = anios[2024]
        comision_aed_2024 = Comision.objects.filter(materia=materia_algoritmos, anio_academico=anio_2024).first()
        if comision_aed_2024:
            InscripcionAlumnoComision.objects.create(
                alumno=alumno_no_aprobado, comision=comision_aed_2024,
                estado_inscripcion='REGULAR', condicion='APROBADO'
            )
            Calificacion.objects.create(
                alumno_comision=InscripcionAlumnoComision.objects.get(alumno=alumno_no_aprobado, comision=comision_aed_2024),
                tipo=TipoCalificacion.FINAL, nota=7, fecha_creacion=anio_2024.fecha_fin
            )
        
        # Ahora el alumno puede (o debería poder) inscribirse en PROG1 (2025)
        # pero no en PROG2 si no tiene PROG1 aprobada todavía.
        # Creamos una inscripcion para PROG1 en 2025 (cursando)
        InscripcionAlumnoComision.objects.create(
            alumno=alumno_no_aprobado, comision=comision_prog1_2025,
            estado_inscripcion='CURSANDO', condicion='REGULAR'
        )
        # Este alumno *no* debería poder inscribirse en PROG2 en 2025 porque PROG1 no está "APROBADO" todavía.
        # La prueba para esto se haría intentando inscribirlo via la lógica de la app.

        # --- CASO 2: Alumno que cumple todas las correlativas (para ING. SOFTWARE I) ---
        email_full_ok = 'alumno_corr_ok@test.com'
        alumno_full_ok = Alumno.objects.create(
            dni="46000000", nombre="Correlativa", apellido="Exitosa", legajo="2025-OK",
            email=email_full_ok, estado=estado_activo, fecha_nacimiento=date(1999,5,10)
        )
        # Simular aprobación de PROG1 y BDD1 en 2024
        anio_2024 = anios[2024]
        comision_prog1_2024 = Comision.objects.filter(materia=materia_prog1, anio_academico=anio_2024).first()
        comision_bdd1_2024 = Comision.objects.filter(materia=materia_bdd1, anio_academico=anio_2024).first()

        if comision_prog1_2024:
            InscripcionAlumnoComision.objects.create(alumno=alumno_full_ok, comision=comision_prog1_2024, estado_inscripcion='REGULAR', condicion='APROBADO')
            Calificacion.objects.create(alumno_comision=InscripcionAlumnoComision.objects.get(alumno=alumno_full_ok, comision=comision_prog1_2024), tipo=TipoCalificacion.FINAL, nota=7, fecha_creacion=anio_2024.fecha_fin)
        if comision_bdd1_2024:
            InscripcionAlumnoComision.objects.create(alumno=alumno_full_ok, comision=comision_bdd1_2024, estado_inscripcion='REGULAR', condicion='APROBADO')
            Calificacion.objects.create(alumno_comision=InscripcionAlumnoComision.objects.get(alumno=alumno_full_ok, comision=comision_bdd1_2024), tipo=TipoCalificacion.FINAL, nota=8, fecha_creacion=anio_2024.fecha_fin)
        
        # Este alumno *sí* debería poder inscribirse en ING. SOFTWARE I en 2025.
        # La prueba para esto se haría intentando inscribirlo via la lógica de la app.
        InscripcionAlumnoComision.objects.create(
            alumno=alumno_full_ok, comision=comision_ing_soft_2025,
            estado_inscripcion='CURSANDO', condicion='REGULAR'
        )

        # --- CASO 3: Alumno con múltiples inscripciones en el mismo año (una aprobada, otra en curso) ---
        email_multi = 'alumno_multi@test.com'
        alumno_multi = Alumno.objects.create(
            dni="47000000", nombre="Multi", apellido="Inscripcion", legajo="2025-MULTI",
            email=email_multi, estado=estado_activo, fecha_nacimiento=date(2001,8,20)
        )
        # En 2025: Inscribir en Algoritmos (APROBADO)
        comision_aed_2025 = Comision.objects.filter(materia=materia_algoritmos, anio_academico=anio_2025).first()
        if comision_aed_2025:
            InscripcionAlumnoComision.objects.create(alumno=alumno_multi, comision=comision_aed_2025, estado_inscripcion='REGULAR', condicion='APROBADO')
            Calificacion.objects.create(alumno_comision=InscripcionAlumnoComision.objects.get(alumno=alumno_multi, comision=comision_aed_2025), tipo=TipoCalificacion.FINAL, nota=9, fecha_creacion=anio_2025.fecha_fin)
        # En 2025: Inscribir en PROG1 (CURSANDO)
        InscripcionAlumnoComision.objects.create(
            alumno=alumno_multi, comision=comision_prog1_2025,
            estado_inscripcion='CURSANDO', condicion='REGULAR'
        )

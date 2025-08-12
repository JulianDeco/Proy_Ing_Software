# models.py
from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth.hashers import make_password, check_password
from datetime import datetime, timedelta

class TipoCalificacion(models.Model):
    descripcion = models.CharField(max_length=255)

    def __str__(self):
        return self.descripcion

class TipoEstado(models.Model):
    descripcion = models.CharField(max_length=100)

    def __str__(self):
        return self.descripcion

class Persona(models.Model):
    dni = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.nombre} {self.apellido}"

class Administrativo(models.Model):
    persona = models.OneToOneField(Persona, on_delete=models.CASCADE)
    area = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.persona} - Área: {self.area}"

class Docente(models.Model):
    persona = models.OneToOneField(Persona, on_delete=models.CASCADE)
    legajo = models.CharField(max_length=50)

    def listar_materias(self):
        return Materia.objects.filter(profesor=self)

    def __str__(self):
        return str(self.persona)

class Correlativa(models.Model):
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return self.nombre

class Materia(models.Model):
    nombre = models.CharField(max_length=100)
    codigo = models.IntegerField(unique=True)
    cupo_maximo = models.IntegerField()
    correlativas = models.ManyToManyField('self', symmetrical=False, blank=True, related_name='materias_correlativas')
    profesor = models.ForeignKey(Docente, on_delete=models.SET_NULL, null=True, blank=True)

    def agregar_correlativa(self, materia_correlativa):
        if materia_correlativa == self:
            raise ValidationError("Una materia no puede ser correlativa de sí misma.")
        if self in materia_correlativa.get_correlativas_indirectas():
            raise ValidationError("Correlativas cíclicas no permitidas.")
        self.correlativas.add(materia_correlativa)

    def get_correlativas_indirectas(self, visited=None):
        if visited is None:
            visited = set()
        for c in self.correlativas.all():
            if c not in visited:
                visited.add(c)
                c.get_correlativas_indirectas(visited)
        return visited

    def asignar_profesor(self, docente):
        self.profesor = docente
        self.save()

    def __str__(self):
        return self.nombre

class PlanEstudio(models.Model):
    nombre = models.CharField(max_length=100)
    codigo = models.CharField(max_length=20)
    materias = models.ManyToManyField(Materia, blank=True)

    def listar_materias(self):
        return self.materias.all()

    def agregar_materia(self, materia):
        self.materias.add(materia)

    def remover_materia(self, materia):
        if Inscripcion.objects.filter(comision__materia=materia, estado="Activo").exists():
            raise ValidationError("No se puede eliminar la materia, hay inscripciones activas.")
        self.materias.remove(materia)

    def __str__(self):
        return self.nombre

class Comision(models.Model):
    codigo = models.IntegerField(unique=True)
    horario_inicio = models.TimeField()
    horario_fin = models.TimeField()
    turno = models.CharField(max_length=50)
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE)

    @property
    def duracion(self):
        formato = '%H:%M:%S'
        hi = datetime.strptime(str(self.horario_inicio), formato)
        hf = datetime.strptime(str(self.horario_fin), formato)
        duracion = hf - hi
        if duracion.total_seconds() < 0:
            duracion += timedelta(days=1)
        return duracion

    @property
    def profesor(self):
        return self.materia.profesor

    def ver_inscriptos(self):
        return Inscripcion.objects.filter(comision=self)

    def es_completa(self):
        cupo = self.materia.cupo_maximo
        inscritos = self.ver_inscriptos().count()
        return inscritos >= cupo

    def __str__(self):
        return f"{self.materia.nombre} ({self.horario_inicio.strftime('%H:%M')} - {self.horario_fin.strftime('%H:%M')})"

class Alumno(models.Model):
    persona = models.OneToOneField(Persona, on_delete=models.CASCADE)
    estado = models.ForeignKey(TipoEstado, on_delete=models.SET_NULL, null=True)
    comisiones = models.ManyToManyField(Comision, through='Inscripcion')

    def inscribir(self, comision):
        if not self.estado or self.estado.descripcion != "Activo":
            raise ValidationError("El alumno no está en estado activo.")
        if comision.profesor is None:
            raise ValidationError("La comisión no tiene un profesor asignado.")
        if not PlanEstudio.objects.filter(materias=comision.materia).exists():
            raise ValidationError("La materia no pertenece a ningún plan de estudios activo.")
        if comision.es_completa():
            raise ValidationError("La comisión ya está completa.")
        if Inscripcion.objects.filter(alumno=self, comision=comision).exists():
            raise ValidationError("El alumno ya está inscripto en esta comisión.")
        return Inscripcion.objects.create(alumno=self, comision=comision, estado="Activo")

    def ver_calificaciones(self):
        return Calificacion.objects.filter(alumno=self)

    def ver_asistencias(self):
        return Asistencia.objects.filter(alumno=self)

    def __str__(self):
        return str(self.persona)

class Inscripcion(models.Model):
    alumno = models.ForeignKey(Alumno, on_delete=models.CASCADE)
    comision = models.ForeignKey(Comision, on_delete=models.CASCADE)
    fecha = models.DateField(auto_now_add=True)
    estado = models.CharField(max_length=50)

    def es_valida(self):
        return True

    def __str__(self):
        return f"{self.alumno} inscrito en {self.comision} [{self.estado}]"

class Calificacion(models.Model):
    alumno = models.ForeignKey(Alumno, on_delete=models.CASCADE)
    comision = models.ForeignKey(Comision, on_delete=models.CASCADE)
    fecha = models.DateField()
    nota = models.FloatField()
    tipo = models.ForeignKey(TipoCalificacion, on_delete=models.SET_NULL, null=True)

    def listar_calificaciones(self):
        return Calificacion.objects.filter(alumno=self.alumno)

    def es_aprobada(self):
        return self.nota >= 6.0 

    def __str__(self):
        return f"{self.alumno} - {self.nota} ({self.tipo})"

class Asistencia(models.Model):
    alumno = models.ForeignKey(Alumno, on_delete=models.CASCADE)
    comision = models.ForeignKey(Comision, on_delete=models.CASCADE)
    fecha = models.DateField()
    presente = models.BooleanField(default=False)

    def marcar_asistencia(self, presente=True):
        self.presente = presente
        self.save()

    def __str__(self):
        estado = "Presente" if self.presente else "Ausente"
        return f"{self.alumno} - {self.fecha} - {estado}"

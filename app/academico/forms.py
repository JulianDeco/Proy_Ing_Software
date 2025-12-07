from django import forms
from django.utils import timezone

from academico.models import (
    InscripcionAlumnoComision, Materia, TipoCalificacion,
    Calificacion, InscripcionMesaExamen, MesaExamen
)

class MateriaAdminForm(forms.ModelForm):
    class Meta:
        model = Materia
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        if self.instance and self.instance.pk and self.instance.plan_estudio:
            self.fields['correlativas'].queryset = Materia.objects.filter(
                plan_estudio=self.instance.plan_estudio
            ).exclude(pk=self.instance.pk)


    def clean(self):
        cleaned_data = super().clean()
        if self.instance and self.instance.pk:
            plan_estudio = cleaned_data.get('plan_estudio', self.instance.plan_estudio)
            for correlativa in self.instance.correlativas.all():
                if correlativa.plan_estudio != plan_estudio:
                    raise forms.ValidationError({
                        'correlativas': f'La materia "{correlativa.nombre}" es correlativa pero '
                                      f'pertenece al plan "{correlativa.plan_estudio}" '
                                      f'(debe ser del mismo plan: "{plan_estudio}").'
                    })
        return cleaned_data
    
class InscripcionComisionAdminForm(forms.ModelForm):
    class Meta:
        model = InscripcionAlumnoComision
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk and self.instance.plan_estudio:
            self.fields['correlativas'].queryset = Materia.objects.filter(
                plan_estudio=self.instance.plan_estudio
            ).exclude(pk=self.instance.pk)


    def clean(self):
        cleaned_data = super().clean()
        if self.instance and self.instance.pk:
            plan_estudio = cleaned_data.get('plan_estudio', self.instance.plan_estudio)
            for correlativa in self.instance.correlativas.all():
                if correlativa.plan_estudio != plan_estudio:
                    raise forms.ValidationError({
                        'correlativas': f'La materia "{correlativa.nombre}" es correlativa pero '
                                      f'pertenece al plan "{correlativa.plan_estudio}" '
                                      f'(debe ser del mismo plan: "{plan_estudio}").'
                    })
        return cleaned_data


class RegistroAsistenciaForm(forms.Form):
    """Formulario para validar el registro de asistencias"""
    fecha_asistencia = forms.DateField(
        required=True,
        error_messages={
            'required': 'La fecha de asistencia es obligatoria.',
            'invalid': 'Formato de fecha inválido. Use YYYY-MM-DD.'
        }
    )

    def clean_fecha_asistencia(self):
        """Validar que la fecha no sea futura"""
        fecha = self.cleaned_data.get('fecha_asistencia')

        if fecha and fecha > timezone.now().date():
            raise forms.ValidationError('No se puede registrar asistencia para fechas futuras.')

        return fecha


class CalificacionForm(forms.Form):
    """Formulario para validar la creación de calificaciones"""
    fecha = forms.DateField(
        required=True,
        error_messages={
            'required': 'La fecha de calificación es obligatoria.',
            'invalid': 'Formato de fecha inválido. Use YYYY-MM-DD.'
        }
    )
    tipo = forms.ChoiceField(
        choices=TipoCalificacion.choices,
        required=True,
        error_messages={
            'required': 'El tipo de calificación es obligatorio.',
            'invalid_choice': 'El tipo de calificación seleccionado no es válido.'
        }
    )

    def clean_fecha(self):
        """Validar que la fecha no sea futura"""
        fecha = self.cleaned_data.get('fecha')

        if fecha and fecha > timezone.now().date():
            raise forms.ValidationError('No se puede registrar calificación para fechas futuras.')

        return fecha


class NotaIndividualForm(forms.Form):
    """Formulario para validar una calificación individual"""
    nota = forms.DecimalField(
        min_value=0,
        max_value=10,
        decimal_places=2,
        required=True,
        error_messages={
            'required': 'La nota es obligatoria.',
            'invalid': 'La nota debe ser un número válido.',
            'min_value': 'La nota no puede ser menor a 0.',
            'max_value': 'La nota no puede ser mayor a 10.'
        }
    )


# ============================================
# Forms para Admin con validaciones del modelo
# ============================================

class CalificacionAdminForm(forms.ModelForm):
    """Form para el admin que ejecuta las validaciones del modelo"""
    class Meta:
        model = Calificacion
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        # Crear instancia temporal para validar
        instance = Calificacion(
            alumno_comision=cleaned_data.get('alumno_comision'),
            tipo=cleaned_data.get('tipo'),
            nota=cleaned_data.get('nota'),
            fecha_creacion=cleaned_data.get('fecha_creacion')
        )
        if self.instance.pk:
            instance.pk = self.instance.pk
        # Ejecutar validaciones del modelo
        instance.clean()
        return cleaned_data


class InscripcionAlumnoComisionAdminForm(forms.ModelForm):
    """Form para el admin que ejecuta las validaciones del modelo"""
    class Meta:
        model = InscripcionAlumnoComision
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        
        alumno = cleaned_data.get('alumno')
        comision = cleaned_data.get('comision')

        # Si faltan campos requeridos, no validar lógica de negocio aún
        if not alumno or not comision:
            return cleaned_data

        # Crear instancia temporal para validar
        instance = InscripcionAlumnoComision(
            alumno=alumno,
            comision=comision,
            estado_inscripcion=cleaned_data.get('estado_inscripcion', 'REGULAR'),
            condicion=cleaned_data.get('condicion', 'CURSANDO')
        )
        if self.instance.pk:
            instance.pk = self.instance.pk
        # Ejecutar validaciones del modelo
        instance.clean()
        return cleaned_data


class InscripcionMesaExamenAdminForm(forms.ModelForm):
    """Form para el admin que ejecuta las validaciones del modelo"""
    class Meta:
        model = InscripcionMesaExamen
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        # Crear instancia temporal para validar
        instance = InscripcionMesaExamen(
            mesa_examen=cleaned_data.get('mesa_examen'),
            alumno=cleaned_data.get('alumno'),
            condicion=cleaned_data.get('condicion'),
            estado_inscripcion=cleaned_data.get('estado_inscripcion', 'INSCRIPTO'),
            nota_examen=cleaned_data.get('nota_examen')
        )
        if self.instance.pk:
            instance.pk = self.instance.pk
        # Ejecutar validaciones del modelo
        instance.clean()
        return cleaned_data


class MesaExamenAdminForm(forms.ModelForm):
    """Form para el admin que ejecuta las validaciones del modelo"""
    class Meta:
        model = MesaExamen
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        # Crear instancia temporal para validar
        instance = MesaExamen(
            materia=cleaned_data.get('materia'),
            anio_academico=cleaned_data.get('anio_academico'),
            fecha_examen=cleaned_data.get('fecha_examen'),
            fecha_limite_inscripcion=cleaned_data.get('fecha_limite_inscripcion'),
            estado=cleaned_data.get('estado', 'ABIERTA'),
            cupo_maximo=cleaned_data.get('cupo_maximo', 50)
        )
        if self.instance.pk:
            instance.pk = self.instance.pk
        # Ejecutar validaciones del modelo
        instance.clean()
        return cleaned_data
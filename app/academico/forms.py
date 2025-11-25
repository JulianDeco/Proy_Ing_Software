from django import forms
from django.utils import timezone

from academico.models import InscripcionAlumnoComision, Materia, TipoCalificacion

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
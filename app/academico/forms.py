from django import forms

from academico.models import InscripcionAlumnoComision, Materia

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
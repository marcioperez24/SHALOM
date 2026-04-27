from django import forms
from .models import Empleado, ContratoLaboral, HorarioEmpleado, DiaFeriado
from django.core.exceptions import ValidationError

class EmpleadoForm(forms.ModelForm):
    class Meta:
        model = Empleado
        fields = [
            'nombres', 'apellidos', 'cedula', 'numero_inss', 
            'fecha_nacimiento', 'telefono', 'direccion', 
            'cargo', 'fecha_contratacion', 'curriculum', 'diplomas'
        ]
        widgets = {
            'nombres': forms.TextInput(attrs={'class': 'form-control'}),
            'apellidos': forms.TextInput(attrs={'class': 'form-control'}),
            'cedula': forms.TextInput(attrs={'class': 'form-control'}),
            'numero_inss': forms.TextInput(attrs={'class': 'form-control'}),
            'fecha_nacimiento': forms.DateInput(
                format='%Y-%m-%d',
                attrs={'type': 'date', 'class': 'form-control'}
            ),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'direccion': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'cargo': forms.TextInput(attrs={'class': 'form-control'}),
            'fecha_contratacion': forms.DateInput(
                format='%Y-%m-%d',
                attrs={'type': 'date', 'class': 'form-control'}
            ),
            'curriculum': forms.FileInput(attrs={'class': 'form-control'}),
            'diplomas': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def clean_cedula(self):
        cedula = self.cleaned_data.get('cedula')
        if Empleado.objects.filter(cedula=cedula).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("¡Error! Esta cédula ya pertenece a otro trabajador.")
        return cedula

    def clean_numero_inss(self):
        inss = self.cleaned_data.get('numero_inss')
        if inss and Empleado.objects.filter(numero_inss=inss).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("¡Error! Este número de INSS ya está duplicado en el sistema.")
        return inss

class ContratoForm(forms.ModelForm):
    class Meta:
        model = ContratoLaboral
        fields = ['salario_base', 'paga_inss', 'paga_ir', 'porcentaje_antiguedad']
        widgets = {
            'salario_base': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'porcentaje_antiguedad': forms.NumberInput(attrs={'class': 'form-control'}),
            'paga_inss': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'paga_ir': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class HorarioForm(forms.ModelForm):
    class Meta:
        model = HorarioEmpleado
        fields = ['entrada_esperada', 'salida_esperada', 'minutos_tolerancia', 'es_flexible']
        widgets = {
            'entrada_esperada': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'salida_esperada': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'minutos_tolerancia': forms.NumberInput(attrs={'class': 'form-control'}),
            'es_flexible': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class DiaFeriadoForm(forms.ModelForm):
    class Meta:
        model = DiaFeriado
        fields = ['fecha', 'motivo', 'es_nacional']
        widgets = {
            'fecha': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'motivo': forms.TextInput(attrs={'class': 'form-control'}),
            'es_nacional': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
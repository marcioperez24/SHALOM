from django import forms
# 1. AGREGAMOS DocumentoDocente A LOS IMPORTS
from .models import Docente, CargaAcademica, DocumentoDocente
from .models import Nivel, Seccion, Materias

class DocenteForm(forms.ModelForm):
    class Meta:
        model = Docente
        fields = ['nombres', 'apellidos', 'cedula', 'telefono', 'email', 'direccion', 'fecha_contratacion']
        
        widgets = {
            'nombres': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Juan Alberto'}),
            'apellidos': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Pérez López'}),
            'cedula': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 001-000000-0000U'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '(+505) 0000-0000'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'profesor@ejemplo.com'}),
            'direccion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'fecha_contratacion': forms.DateInput(
                format='%Y-%m-%d',
                attrs={'class': 'form-control', 'type': 'date'}
            ),
        }

class CargaAcademicaForm(forms.ModelForm):
    materias = forms.ModelMultipleChoiceField(
        queryset=Materias.objects.none(),
        widget=forms.SelectMultiple(attrs={'class': 'form-control', 'id': 'id_materias'}),
        label="Materias / Asignaturas"
    )

    class Meta:
        model = CargaAcademica
        fields = ['docente', 'nivel', 'seccion', 'anio_lectivo'] 
        
        widgets = {
            'docente': forms.Select(attrs={'class': 'form-select select2'}), 
            'nivel': forms.Select(attrs={'class': 'form-select', 'id': 'id_nivel'}),
            'seccion': forms.Select(attrs={'class': 'form-select', 'id': 'id_seccion'}),
            'anio_lectivo': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['nivel'].queryset = Nivel.objects.filter(Activo=True)
        
        if 'nivel' in self.data:
            try:
                nivel_id = int(self.data.get('nivel'))
                self.fields['seccion'].queryset = Seccion.objects.filter(NivelID=nivel_id)
                self.fields['materias'].queryset = Materias.objects.filter(NivelID=nivel_id)
            except (ValueError, TypeError):
                pass
        else:
            self.fields['seccion'].queryset = Seccion.objects.none()

# --- NUEVO FORMULARIO PARA SUBIR DOCUMENTOS ---
class DocumentoForm(forms.ModelForm):
    class Meta:
        model = DocumentoDocente
        fields = ['nombre_documento', 'archivo']
        widgets = {
            'nombre_documento': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Planificación Anual 2025'}),
            'archivo': forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf,.doc,.docx,.jpg,.png'}),
        }
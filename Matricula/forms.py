# matricula/forms.py
from django import forms
from django.forms import inlineformset_factory
from .models import Estudiantes_Nueva, Matricula, Inscripciones
from configuracion.models import Materias, Seccion, Nivel, Modalidades, TipoMatricula, Turno
from django.forms import modelformset_factory
from .models import Inscripciones
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Fieldset


# Formulario para registrar un nuevo estudiante
class EstudianteForm(forms.ModelForm):
    # (Tu campo FechaNacimiento va aquí, fuera de Meta)
    FechaNacimiento = forms.DateField(
            widget=forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'},
                format='%Y-%m-%d'  # <-- AÑADE ESTA LÍNEA
            ),
            input_formats=['%Y-%m-%d'],
            localize=False
    )
    
    class Meta:
        model = Estudiantes_Nueva
        exclude = ['EstudianteID', 'UsuarioID', 'activo', 'Edad']
        
        # (Aquí van todos tus widgets)
        widgets = {
            'Codigo_MINED': forms.TextInput(attrs={'class': 'form-control'}),
            'NombreCompleto': forms.TextInput(attrs={'class': 'form-control'}),
            'Genero': forms.Select(choices=[('M', 'Masculino'), ('F', 'Femenino')], attrs={'class': 'form-control'}),
            'Direccion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'NombreMadre': forms.TextInput(attrs={'class': 'form-control'}),
            'CedulaMadre': forms.TextInput(attrs={'class': 'form-control'}),
            'TelefonoMadre': forms.TextInput(attrs={'class': 'form-control'}),
            'OcupacionMadre': forms.TextInput(attrs={'class': 'form-control'}),
            'NombrePadre': forms.TextInput(attrs={'class': 'form-control'}),
            'CedulaPadre': forms.TextInput(attrs={'class': 'form-control'}),
            'TelefonoPadre': forms.TextInput(attrs={'class': 'form-control'}),
            'OcupacionPadre': forms.TextInput(attrs={'class': 'form-control'}),
            'NombreTutor': forms.TextInput(attrs={'class': 'form-control'}),
            'CedulaTutor': forms.TextInput(attrs={'class': 'form-control'}),
            'TelefonoTutor': forms.TextInput(attrs={'class': 'form-control'}),
            'OcupacionTutor': forms.TextInput(attrs={'class': 'form-control'}),
            'ResponsableEP': forms.TextInput(attrs={'class': 'form-control'}),
            'ColegioProcedencia': forms.TextInput(attrs={'class': 'form-control'}),
            'FechaRetiro': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            # 'Fotocarnet' se añadirá automáticamente si está en el modelo
        }
        
        # (Aquí van todos tus labels)
        labels = {
            'Codigo_MINED': 'Código MINED',
            'NombreCompleto': 'Nombre Completo',
            'Genero': 'Género',
            'Direccion': 'Dirección',
            'NombreMadre': 'Nombre de la Madre',
            'CedulaMadre': 'Cédula de la Madre',
            'TelefonoMadre': 'Teléfono de la Madre',
            'OcupacionMadre': 'Ocupación de la Madre',
            'NombrePadre': 'Nombre del Padre',
            'CedulaPadre': 'Cédula del Padre',
            'TelefonoPadre': 'Teléfono del Padre',
            'OcupacionPadre': 'Ocupación del Padre',
            'NombreTutor': 'Nombre del Tutor',
            'CedulaTutor': 'Cédula del Tutor',
            'TelefonoTutor': 'Teléfono del Tutor',
            'OcupacionTutor': 'Ocupación del Tutor',
            'ResponsableEP': 'Responsable EP',
            'ColegioProcedencia': 'Colegio de Procedencia',
            'FechaRetiro': 'Fecha de Retiro',
            'Fotocarnet': 'Foto del Carnet',
        }

    # --- AQUÍ ESTÁ LA MAGIA DE CRISPY ---
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        # No queremos que crispy-forms añada la etiqueta <form>
        # porque ya la tenemos en el template (con el enctype).
        self.helper.form_tag = False 
        
        self.helper.layout = Layout(
            Fieldset(
                'Datos del Estudiante', # Título del grupo
                Row(
                    Column('Codigo_MINED', css_class='col-md-6'),
                    Column('NombreCompleto', css_class='col-md-6')
                ),
                Row(
                    Column('Genero', css_class='col-md-6'),
                    Column('FechaNacimiento', css_class='col-md-6')
                ),
                'Direccion', # Campo de ancho completo
            ),
            Fieldset(
                'Datos de la Madre',
                Row(
                    Column('NombreMadre', css_class='col-md-6'),
                    Column('CedulaMadre', css_class='col-md-6')
                ),
                Row(
                    Column('TelefonoMadre', css_class='col-md-6'),
                    Column('OcupacionMadre', css_class='col-md-6')
                )
            ),
            Fieldset(
                'Datos del Padre',
                Row(
                    Column('NombrePadre', css_class='col-md-6'),
                    Column('CedulaPadre', css_class='col-md-6')
                ),
                Row(
                    Column('TelefonoPadre', css_class='col-md-6'),
                    Column('OcupacionPadre', css_class='col-md-6')
                )
            ),
            Fieldset(
                'Datos del Tutor',
                Row(
                    Column('NombreTutor', css_class='col-md-6'),
                    Column('CedulaTutor', css_class='col-md-6')
                ),
                Row(
                    Column('TelefonoTutor', css_class='col-md-6'),
                    Column('OcupacionTutor', css_class='col-md-6')
                )
            ),
            Fieldset(
                'Otros Datos',
                Row(
                    Column('ResponsableEP', css_class='col-md-6'),
                    Column('ColegioProcedencia', css_class='col-md-6') # <-- AÑADIDO AQUÍ
                ),
                Row(
                    Column('FotoCarnet', css_class='col-md-6'),      # <-- AÑADIDO AQUÍ
                    Column('FechaRetiro', css_class='col-md-6')
                )
            )
        )


class MatriculaForm(forms.ModelForm):
    AñoMatricula = forms.IntegerField(
        label='Año de Matrícula',
        min_value=2000,
        max_value=2050,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ej. 2025'})
    )

    class Meta:
        model = Matricula
        exclude = ['MatriculaID', 'EstudianteID', 'UsuarioID', 'FechaRegistro', 'activo']
        labels = {
            'NivelID': 'Nivel',
            'SeccionID': 'Sección',
            'FechaMatricula': 'Fecha de Matrícula',
            'TipoMatriculaID': 'Tipo de Matrícula',
            'ModalidadID': 'Modalidad',
            'TurnoID': 'Turno',
        }
        widgets = {
            'NivelID': forms.Select(attrs={'class': 'form-control', 'id': 'id_NivelID'}),
            'SeccionID': forms.Select(attrs={'class': 'form-control', 'id': 'id_SeccionID'}),
            'FechaMatricula': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'TipoMatriculaID': forms.Select(attrs={'class': 'form-control'}),
            'ModalidadID': forms.Select(attrs={'class': 'form-control'}),
            'TurnoID': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # --- INICIAN CAMBIOS PARA MATRICULAFORM ---
        self.helper = FormHelper()
        self.helper.form_tag = False # El template ya tiene <form>
        
        # Definimos el layout responsivo
        self.helper.layout = Layout(
            Row(
                Column('NivelID', css_class='col-md-6'),
                Column('SeccionID', css_class='col-md-6')
            ),
            Row(
                Column('FechaMatricula', css_class='col-md-6'),
                Column('AñoMatricula', css_class='col-md-6')
            ),
            Row(
                Column('TipoMatriculaID', css_class='col-md-6'),
                Column('ModalidadID', css_class='col-md-6')
            ),
            Row(
                Column('TurnoID', css_class='col-md-6')
                # Columna vacía para alinear el botón si quieres
            )
        )
        # --- TERMINAN CAMBIOS PARA MATRICULAFORM ---

        # Tu lógica existente para los querysets
        self.fields['NivelID'].queryset = Nivel.objects.filter(Activo=True) 
        self.fields['TipoMatriculaID'].queryset = TipoMatricula.objects.filter(activo=True)
        self.fields['ModalidadID'].queryset = Modalidades.objects.filter(activo=True)
        self.fields['TurnoID'].queryset = Turno.objects.filter(activo=True)
        self.fields['SeccionID'].queryset = Seccion.objects.none()

        if 'NivelID' in self.data:
            try:
                nivel_id = int(self.data.get('NivelID'))
                self.fields['SeccionID'].queryset = Seccion.objects.filter(NivelID=nivel_id, Activo=True).order_by('NombreSeccion')
            except (ValueError, TypeError):
                pass

class InscripcionesForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        matricula = kwargs.pop('matricula', None)
        super().__init__(*args, **kwargs)
        
        # --- INICIAN CAMBIOS PARA INSCRIPCIONESFORM ---
        # Añadimos un helper básico para que funcione |as_crispy_field
        self.helper = FormHelper()
        self.helper.form_tag = False
        # No definimos layout, el template lo maneja
        # --- TERMINAN CAMBIOS PARA INSCRIPCIONESFORM ---

        if matricula:
            self.fields['MateriaID'].queryset = Materias.objects.filter(NivelID=matricula.NivelID, activo=True)
        else:
            self.fields['MateriaID'].queryset = Materias.objects.none()

    class Meta:
        model = Inscripciones
        fields = ['MateriaID']
        widgets = {
            'MateriaID': forms.Select(attrs={'class': 'form-control'}),
        }

InscripcionesFormset = modelformset_factory(Inscripciones, form=InscripcionesForm, extra=1, can_delete=True)
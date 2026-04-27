# configuracion/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth import get_user_model
from django import forms
from django.db.models import Q
from django.core.exceptions import ValidationError
from .models import Nivel, Seccion, TServicio, Servicios, Materias, TipoMatricula, Turno, Modalidades, Semestres
from .models import Cortes, TiposCambio
from .models import Licencia

User = get_user_model() # Obtiene el modelo de usuario activo (generalmente auth.User)

class CustomUserCreationForm(UserCreationForm):
    first_name = forms.CharField(label='Nombre', max_length=150, required=True)
    last_name = forms.CharField(label='Apellido', max_length=150, required=True)
    email = forms.EmailField(label='Correo Electrónico', required=True)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('first_name', 'last_name', 'email',)

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']
        user.is_staff = True # <--- Aquí establecemos is_staff a True (1 en la DB)

        if commit:
            user.save()
        return user

class CustomUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        # Aquí personalizamos los campos con sus etiquetas en español
        fields = ('username', 'first_name', 'last_name', 'email', 'is_active', 'is_staff')
        labels = {
            'username': 'Nombre de Usuario',
            'first_name': 'Nombre',
            'last_name': 'Apellido',
            'email': 'Correo Electrónico',
            'is_active': 'Activo',
            'is_staff': 'Es Staff',
        }
        
class RestablecerContrasenaAdminForm(forms.Form):
    """
    Formulario simple para que el administrador restablezca la contraseña de un usuario.
    """
    nueva_contrasena = forms.CharField(
        label='Nueva Contraseña',
        widget=forms.PasswordInput,
        strip=False,
        help_text=("Ingrese la nueva contraseña."),
    )
    confirmar_contrasena = forms.CharField(
        label='Confirmar Contraseña',
        widget=forms.PasswordInput,
        strip=False,
        help_text=("Repita la nueva contraseña para confirmarla."),
    )

    def clean(self):
        """Asegura que ambas contraseñas coincidan."""
        cleaned_data = super().clean()
        nueva = cleaned_data.get("nueva_contrasena")
        confirmar = cleaned_data.get("confirmar_contrasena")

        if nueva and confirmar and nueva != confirmar:
            # Añade un error al campo confirmar_contrasena
            self.add_error('confirmar_contrasena', 'Las contraseñas no coinciden.')
        
        # Opcional: Podrías añadir validaciones de complejidad de contraseña aquí si lo necesitas.
        return cleaned_data
        
        
class NivelForm(forms.ModelForm):
    class Meta:
        model = Nivel
        fields = ['NombreNivel', 'Activo']
        labels = {
            'NombreNivel': 'Nivel',
            'Activo': 'Nivel ACtivo'
        }
        widgets = {
            'NombreNivel': forms.TextInput(attrs={'class': 'form-control'}),
            'Activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        
class SeccionForm(forms.ModelForm):
    # Sobrescribimos el campo NivelID para filtrar los departamentos activos
    NivelID = forms.ModelChoiceField(
        queryset=Nivel.objects.filter(Activo=True).order_by('NombreNivel'),
        label='Nivel',
        widget=forms.Select(attrs={'class': 'form-control'})
    )    
    
    
    class Meta:
        model = Seccion
        fields = ['NivelID', 'NombreSeccion', 'CuposDisponibles', 'Activo']
        labels = {
            'NivelID': 'Nivel',
            'NombreSeccion': 'Nombre de la Sección',
            'CuposDisponibles': 'Cupos Disponibles',
            'Activo': 'Sección Activa'
        }
        widgets = {
            'NivelID': forms.Select(attrs={'class': 'form-control'}),
            'NombreSeccion': forms.TextInput(attrs={'class': 'form-control'}),
            'CuposDisponibles': forms.NumberInput(attrs={'class': 'form-control'}),
            'Activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        
class TServicioForm(forms.ModelForm):
    class Meta:
        model = TServicio
        fields = ['TipoServicio', 'activo']
        labels = {
            'TipoServicio': 'Tipo de Servicio',
            'activo': 'Activo'
        }
        widgets = {
            'TipoServicio': forms.TextInput(attrs={'class': 'form-control'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        

class ServiciosForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtra el queryset para el campo NivelID
        self.fields['NivelID'].queryset = Nivel.objects.filter(Activo=True)
        # Filtra el queryset para el campo TipoServicioID
        self.fields['TipoServicioID'].queryset = TServicio.objects.filter(activo=True)
        
    def clean(self):
        cleaned_data = super().clean()
        nombre_servicio = cleaned_data.get('NombreServicio')
        nivel_id = cleaned_data.get('NivelID')
        anio = cleaned_data.get('Anio')
        
        if nombre_servicio and nivel_id and anio:
            servicio_existente = Servicios.objects.filter(
                NombreServicio__iexact=nombre_servicio,
                NivelID=nivel_id,
                Anio=anio,
                Activo=True
            ).exclude(
                ServicioID=self.instance.ServicioID if self.instance else None
            )

            if servicio_existente.exists():
                # Lanza la ValidationError asociada al campo NombreServicio
                self.add_error(
                    'NombreServicio',
                    f"El servicio '{nombre_servicio}' ya está registrado para '{nivel_id.NombreNivel}' en el año '{anio}'."
                )

        return cleaned_data
        
    class Meta:
        model = Servicios
        fields = ['NombreServicio', 'Precio', 'NivelID', 'TipoServicioID', 'Anio', 'FechaCreacion', 'Activo']
        labels = {
            'NombreServicio': 'Nombre del Servicio',
            'Precio': 'Precio',
            'NivelID': 'Nivel',
            'TipoServicioID': 'Tipo de Servicio',
            'Anio': 'Año',
            'FechaCreacion': 'Fecha de Creación',
            'Activo': 'Activo'
        }
        widgets = {
            'NombreServicio': forms.TextInput(attrs={'class': 'form-control'}),
            'Precio': forms.NumberInput(attrs={'class': 'form-control'}),
            'NivelID': forms.Select(attrs={'class': 'form-control'}),
            'TipoServicioID': forms.Select(attrs={'class': 'form-control'}),
            'Anio': forms.NumberInput(attrs={'class': 'form-control'}),
            'FechaCreacion': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'Activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        
class MateriasForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['NivelID'].queryset = Nivel.objects.filter(Activo=True)
        
    def clean(self):
        cleaned_data = super().clean()
        nombre_materia = cleaned_data.get('NombreMateria')
        nivel_id = cleaned_data.get('NivelID')
        
        # Validar si ya existe una materia con el mismo nombre y nivel
        if nombre_materia and nivel_id:
            # Filtra para encontrar materias con el mismo nombre y nivel
            materia_existente = Materias.objects.filter(
                NombreMateria__iexact=nombre_materia,
                NivelID=nivel_id,
                activo=True
            ).exclude(
                # Excluye la materia actual si estamos editando
                MateriaID=self.instance.MateriaID if self.instance else None
            )

            if materia_existente.exists():
                raise ValidationError(
                    f"La materia '{nombre_materia}' ya está registrada para el nivel '{nivel_id.NombreNivel}'.",
                    code='materia_duplicada'
                )

        return cleaned_data
        
    class Meta:
        model = Materias
        fields = ['NombreMateria', 'NivelID', 'activo']
        labels = {
            'NombreMateria': 'Nombre de la Materia',
            'NivelID': 'Nivel',
            'activo': 'Activo'
        }
        widgets = {
            'NombreMateria': forms.TextInput(attrs={'class': 'form-control'}),
            'NivelID': forms.Select(attrs={'class': 'form-control'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        
        
class TipoMatriculaForm(forms.ModelForm):
    class Meta:
        model = TipoMatricula
        fields = ['Descripcion', 'activo']
        labels = {
            'Descripcion': 'Descripción',
            'activo': 'Activo'
        }
        widgets = {
            'Descripcion': forms.TextInput(attrs={'class': 'form-control'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        
    
class TurnoForm(forms.ModelForm):
    class Meta:
        model = Turno
        fields = ['NombreTurno', 'Descripcion', 'activo']
        labels = {
            'NombreTurno': 'Nombre del Turno',
            'Descripcion': 'Descripción',
            'activo': 'Activo'
        }
        widgets = {
            'NombreTurno': forms.TextInput(attrs={'class': 'form-control'}),
            'Descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        
    
class ModalidadesForm(forms.ModelForm):
    class Meta:
        model = Modalidades
        fields = ['NombreModalidad', 'activo']
        labels = {
            'NombreModalidad': 'Nombre de la Modalidad',
            'activo': 'Activo'
        }
        widgets = {
            'NombreModalidad': forms.TextInput(attrs={'class': 'form-control'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        
class SemestresForm(forms.ModelForm):
    class Meta:
        model = Semestres
        fields = ['NombreSemestre', 'activo']
        labels = {
            'NombreSemestre': 'Nombre del Semestre',
            'activo': 'Activo'
        }
        widgets = {
            'NombreSemestre': forms.TextInput(attrs={'class': 'form-control'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        
        
class CortesForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtra el queryset para el campo SemestreID
        self.fields['SemestreID'].queryset = Semestres.objects.filter(activo=True)
    
    class Meta:
        model = Cortes
        fields = ['NombreCorte', 'SemestreID', 'activo']
        labels = {
            'NombreCorte': 'Nombre del Corte',
            'SemestreID': 'Semestre',
            'activo': 'Activo'
        }
        widgets = {
            'NombreCorte': forms.TextInput(attrs={'class': 'form-control'}),
            'SemestreID': forms.Select(attrs={'class': 'form-control'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class TiposCambioForm(forms.ModelForm):
    class Meta:
        model = TiposCambio
        fields = ['VigenciaInicio', 'VigenciaFin', 'CambioCompra', 'CambioVenta', 'MonedaOrigen', 'MonedaDestino']
        labels = {
            'VigenciaInicio': 'Vigencia Inicio',
            'VigenciaFin': 'Vigencia Fin',
            'CambioCompra': 'Cambio Compra',
            'CambioVenta': 'Cambio Venta',
            'MonedaOrigen': 'Moneda Origen',
            'MonedaDestino': 'Moneda Destino',
        }
        widgets = {
            'VigenciaInicio': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'VigenciaFin': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'CambioCompra': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001'}),
            'CambioVenta': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001'}),
            'MonedaOrigen': forms.TextInput(attrs={'class': 'form-control'}),
            'MonedaDestino': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        vigencia_inicio = cleaned_data.get("VigenciaInicio")
        vigencia_fin = cleaned_data.get("VigenciaFin")
        moneda_origen = cleaned_data.get("MonedaOrigen")
        moneda_destino = cleaned_data.get("MonedaDestino")

        if vigencia_inicio and vigencia_fin and moneda_origen and moneda_destino:
            # Condición de solapamiento
            # Buscar si existe un Tipo de Cambio con las mismas monedas
            # cuyas fechas se solapan con las fechas del nuevo registro.
            q_solapamiento = Q(
                Q(VigenciaInicio__lte=vigencia_fin) & Q(VigenciaFin__gte=vigencia_inicio)
            )

            # Restringir la búsqueda solo a los registros con las mismas monedas
            q_monedas = Q(MonedaOrigen=moneda_origen) & Q(MonedaDestino=moneda_destino)
            
            # Combinar las dos condiciones
            existing_records = TiposCambio.objects.filter(q_monedas & q_solapamiento)

            # Excluir el objeto actual si estamos editando
            if self.instance and self.instance.pk:
                existing_records = existing_records.exclude(pk=self.instance.pk)
            
            if existing_records.exists():
                raise ValidationError("El rango de fechas se superpone con un tipo de cambio existente para estas monedas.")

        # Validar que la fecha de inicio no sea posterior a la de fin
        if vigencia_inicio and vigencia_fin and vigencia_inicio > vigencia_fin:
             raise ValidationError("La fecha de inicio no puede ser posterior a la fecha de fin.")

        return cleaned_data
    
    
class LicenciaAdminForm(forms.ModelForm):
    # Aquí puedes personalizar el campo de fecha si usas un widget específico (ej. DatePicker)
    fecha_caducidad = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label='Nueva Fecha de Caducidad'
    )
    clave = forms.CharField(
        label='Clave de Licencia (Opcional)',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = Licencia
        # Solo permitiremos editar la clave y la fecha de caducidad.
        # fecha_activacion y activa se manejan automáticamente o en el modelo.
        fields = ('clave', 'fecha_caducidad',)
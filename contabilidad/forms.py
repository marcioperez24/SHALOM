from django import forms
from .models import MovimientoCaja, CategoriaMovimiento
from docentes.models import Docente  # Importamos el modelo de docentes que ya tienes

class MovimientoForm(forms.ModelForm):
    class Meta:
        model = MovimientoCaja
        fields = ['categoria', 'descripcion', 'monto', 'docente', 'comprobante']
        widgets = {
            'categoria': forms.Select(attrs={'class': 'form-select'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Ej: Pago de factura de luz enero'}),
            'monto': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00'}),
            'docente': forms.Select(attrs={'class': 'form-select'}),
            'comprobante': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'N° de recibo o factura'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtramos categorías activas
        self.fields['categoria'].queryset = CategoriaMovimiento.objects.filter(activo=True)
        # Hacemos que el docente sea opcional en el formulario
        self.fields['docente'].required = False
        self.fields['docente'].empty_label = "--- Seleccione Docente (Opcional) ---"
from django import forms
from .models import Producto, VarianteProducto

class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ['Categoria', 'Nombre', 'Descripcion', 'PrecioVenta', 'Foto', 'TieneVariantes', 'Activo']

class VarianteProductoForm(forms.ModelForm):
    class Meta:
        model = VarianteProducto
        fields = ['Talla', 'Color', 'StockActual', 'Activo']

from django.db import models
from django.utils import timezone

class CategoriaProducto(models.Model):
    CategoriaID = models.AutoField(primary_key=True)
    Nombre = models.CharField(max_length=100)
    Descripcion = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.Nombre

    class Meta:
        db_table = 'CategoriaProductos'
        verbose_name = "Categoría de Producto"
        verbose_name_plural = "Categorías de Productos"

class Producto(models.Model):
    ProductoID = models.AutoField(primary_key=True)
    Categoria = models.ForeignKey(CategoriaProducto, on_delete=models.SET_NULL, null=True, blank=True)
    Nombre = models.CharField(max_length=150)
    Descripcion = models.TextField(blank=True, null=True)
    PrecioVenta = models.DecimalField(max_digits=10, decimal_places=2)
    Foto = models.ImageField(upload_to="productos/", blank=True, null=True)
    TieneVariantes = models.BooleanField(default=False)
    Activo = models.BooleanField(default=True)
    FechaRegistro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.Nombre}"

    def get_stock_total(self):
        if self.TieneVariantes:
            return sum(v.StockActual for v in self.variantes.all() if v.Activo)
        else:
            # Producto simple tiene una única variante por defecto
            v = self.variantes.first()
            return v.StockActual if v else 0

    class Meta:
        db_table = 'Productos'
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
        permissions = [
            ("gestionar_inventario", "Puede agregar, editar y ver inventario"),
        ]

class VarianteProducto(models.Model):
    VarianteID = models.AutoField(primary_key=True)
    Producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='variantes')
    Talla = models.CharField(max_length=50, blank=True, null=True)
    Color = models.CharField(max_length=50, blank=True, null=True)
    StockActual = models.IntegerField(default=0)
    Activo = models.BooleanField(default=True)

    def __str__(self):
        if self.Producto.TieneVariantes:
            talla_str = f" - Talla: {self.Talla}" if self.Talla else ""
            color_str = f" - Color: {self.Color}" if self.Color else ""
            return f"{self.Producto.Nombre}{talla_str}{color_str}"
        return self.Producto.Nombre

    class Meta:
        db_table = 'VarianteProductos'
        verbose_name = "Variante de Producto"
        verbose_name_plural = "Variantes de Producto"

class Proveedor(models.Model):
    ProveedorID = models.AutoField(primary_key=True)
    Nombre = models.CharField(max_length=150)
    Contacto = models.CharField(max_length=100, blank=True, null=True)
    Telefono = models.CharField(max_length=20, blank=True, null=True)
    Direccion = models.TextField(blank=True, null=True)
    Email = models.EmailField(blank=True, null=True)
    Activo = models.BooleanField(default=True)
    FechaRegistro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.Nombre

    class Meta:
        db_table = 'Proveedores'
        verbose_name = "Proveedor"
        verbose_name_plural = "Proveedores"

class Compra(models.Model):
    CompraID = models.AutoField(primary_key=True)
    Proveedor = models.ForeignKey(Proveedor, on_delete=models.SET_NULL, null=True, blank=True)
    NoFactura = models.CharField(max_length=50, blank=True, null=True, verbose_name="Nº Factura Física")
    FechaCompra = models.DateTimeField(default=timezone.now)
    Total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    Estado = models.CharField(max_length=20, choices=[('Completada', 'Completada'), ('Anulada', 'Anulada')], default='Completada')
    Observaciones = models.TextField(blank=True, null=True)
    FechaRegistro = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        prov_name = self.Proveedor.Nombre if self.Proveedor else 'Sin Proveedor'
        return f"Compra #{self.CompraID} - {prov_name}"

    class Meta:
        db_table = 'Compras'
        verbose_name = "Compra"
        verbose_name_plural = "Compras"

class DetalleCompra(models.Model):
    DetalleID = models.AutoField(primary_key=True)
    Compra = models.ForeignKey(Compra, on_delete=models.CASCADE, related_name='detalles')
    VarianteProducto = models.ForeignKey(VarianteProducto, on_delete=models.PROTECT)
    Cantidad = models.IntegerField()
    PrecioCosto = models.DecimalField(max_digits=10, decimal_places=2)
    Subtotal = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"Detalle {self.DetalleID} de Compra #{self.Compra.CompraID}"

    class Meta:
        db_table = 'DetallesCompra'
        verbose_name = "Detalle de Compra"
        verbose_name_plural = "Detalles de Compra"

#facturacion/models.py
from django.db import models
from Matricula.models import Matricula, Estudiantes_Nueva # Importa el modelo Estudiantes_Nueva
from configuracion.models import Servicios, TiposCambio
from django.contrib.auth import get_user_model
from decimal import Decimal
from django.contrib.auth import get_user_model


User = get_user_model()

class Facturas(models.Model):
    FacturaID = models.AutoField(primary_key=True)
    Fecha = models.DateField(db_column='Fecha')
    Total = models.DecimalField(max_digits=10, decimal_places=2, db_column='Total')
    # ¡Campos agregados para MontoPagado y Saldo!
    MontoPagado = models.DecimalField(max_digits=10, decimal_places=2, db_column='MontoPagado', default=Decimal('0.00'))
    Saldo = models.DecimalField(max_digits=10, decimal_places=2, db_column='Saldo', default=Decimal('0.00'))
    Moneda = models.CharField(max_length=3, db_column='Moneda')
    TipoCambioID = models.ForeignKey(
        TiposCambio,
        on_delete=models.SET_NULL,
        db_column='TipoCambioID',
        null=True
    )
    UsuarioID = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        db_column='UsuarioID',
        null=True
    )
    FechaRegistro = models.DateTimeField(db_column='FechaRegistro')
    EsPorCuotas = models.BooleanField(db_column='EsPorCuotas')
    Activa = models.BooleanField(db_column='Activa')
    Estado = models.CharField(max_length=20, db_column='Estado')
    MatriculaID = models.ForeignKey(
        Matricula,
        on_delete=models.SET_NULL,
        db_column='MatriculaID',
        null=True
    )
    EstudianteID = models.ForeignKey(
        Estudiantes_Nueva,
        on_delete=models.SET_NULL,
        db_column='EstudianteID',
        null=True
    )
    Descuento = models.DecimalField(max_digits=10, decimal_places=2, db_column='Descuento')
    DescuentoPorcentaje = models.DecimalField(max_digits=5, decimal_places=2, db_column='DescuentoPorcentaje')
    
    def __str__(self):
        return f"Factura #{self.FacturaID}"

    class Meta:
        db_table = 'Facturas'
        verbose_name = "Factura"
        verbose_name_plural = "Facturas"
        permissions = [
            ("ver_facturas", "Puede ver facturas, historial e información del estudiante"),
            ("crear_facturas", "Puede crear nuevas facturas"),

        ]


# Modelo para los detalles de la factura, basado en la tabla 'DetallesFactura'
class DetalleFactura(models.Model):
    DetalleID = models.AutoField(primary_key=True)
    FacturaID = models.ForeignKey(
        'Facturas',
        on_delete=models.CASCADE,
        db_column='FacturaID'
    )
    ServicioID = models.ForeignKey(
        Servicios,
        on_delete=models.PROTECT,
        db_column='ServicioID',
        null=True,
        blank=True
    )
    VarianteProductoID = models.ForeignKey(
        'inventario.VarianteProducto',
        on_delete=models.PROTECT,
        db_column='VarianteProductoID',
        null=True,
        blank=True
    )
    Cantidad = models.IntegerField(db_column='Cantidad')
    PrecioUnitario = models.DecimalField(max_digits=10, decimal_places=2, db_column='PrecioUnitario')
    Subtotal = models.DecimalField(max_digits=10, decimal_places=2, db_column='Subtotal')
    FechaRegistro = models.DateTimeField(db_column='FechaRegistro')
    Activa = models.BooleanField(db_column='Activa')
    MontoPagado = models.DecimalField(max_digits=10, decimal_places=2, db_column='MontoPagado', null=True, blank=True)
    Saldo = models.DecimalField(max_digits=10, decimal_places=2, db_column='Saldo', null=True, blank=True)
    Descuento = models.DecimalField(max_digits=10, decimal_places=2, db_column='Descuento')
    DescuentoPorcentaje = models.DecimalField(max_digits=5, decimal_places=2, db_column='DescuentoPorcentaje')
    ReciboID = models.ForeignKey(
        'Recibo',
        on_delete=models.SET_NULL,
        db_column='ReciboID',
        null=True,
        blank=True
    )

    def __str__(self):
        return f"Detalle de Factura #{self.FacturaID.FacturaID} - {self.ServicioID.NombreServicio}"
        
    class Meta:
        # Aquí se ha corregido el nombre de la tabla
        db_table = 'DetallesFactura'
        # Puedes eliminar 'managed = False' para que Django gestione la tabla
        # managed = False 
        verbose_name = "Detalle de Factura"
        verbose_name_plural = "Detalles de Factura"


class Recibo(models.Model):
    ReciboID = models.AutoField(primary_key=True)
    FacturaID = models.ForeignKey(
        'Facturas',
        on_delete=models.CASCADE,
        db_column='FacturaID'
    )
    FechaPago = models.DateField(db_column='FechaPago')
    MontoPagado = models.DecimalField(max_digits=10, decimal_places=2, db_column='MontoPagado')
    # ESTE ES EL CAMPO QUE NECESITAS AGREGAR para que el modelo coincida con la DB.
    Saldo = models.DecimalField(max_digits=10, decimal_places=2, db_column='Saldo')
    Total = models.DecimalField(max_digits=10, decimal_places=2, db_column='Total')
    FechaRegistro = models.DateTimeField(db_column='FechaRegistro')
    Estado = models.CharField(max_length=20, db_column='Estado')

    def __str__(self):
        return f"Recibo #{self.ReciboID}"

    class Meta:
        db_table = 'Recibo'
        verbose_name = "Recibo"
        verbose_name_plural = "Recibos"
        permissions = [
            ("ver_recibo", "Puede ver los detalles del recibo e imprimir"),
            ("crear_recibo", "Puede crear un nuevo recibo para un pago"),
            ("anular_recibo", "Puede anular un recibo"),
        ]


class Arqueos(models.Model):
    ArqueoID = models.AutoField(primary_key=True, db_column='ArqueoID')
    UsuarioID = models.ForeignKey(User, on_delete=models.CASCADE, db_column='UsuarioID')
    FechaRegistro = models.DateTimeField(db_column='FechaRegistro')
    Activa = models.BooleanField(db_column='Activa', default=True)
    MontoDeclarado_Cordobas = models.DecimalField(max_digits=10, decimal_places=2, db_column='MontoDeclarado_Cordobas')
    MontoDeclarado_USD = models.DecimalField(max_digits=10, decimal_places=2, db_column='MontoDeclarado_USD')
    MontoCalculado_Cordobas = models.DecimalField(max_digits=10, decimal_places=2, db_column='MontoCalculado_Cordobas')
    MontoCalculado_USD = models.DecimalField(max_digits=10, decimal_places=2, db_column='MontoCalculado_USD')
    Diferencia_Cordobas = models.DecimalField(max_digits=10, decimal_places=2, db_column='Diferencia_Cordobas')
    Diferencia_USD = models.DecimalField(max_digits=10, decimal_places=2, db_column='Diferencia_USD')
    Fecha = models.DateField(db_column='Fecha')
    Hora = models.TimeField(db_column='Hora')
    Observaciones = models.TextField(blank=True, null=True, db_column='Observaciones')

    def __str__(self):
        return f"Arqueo #{self.ArqueoID} de {self.UsuarioID.username}"

    class Meta:
        managed = False  # Indica que Django no gestionará la tabla
        db_table = 'Arqueos'  # Nombre de la tabla en tu base de datos
        verbose_name = "Arqueo"
        verbose_name_plural = "Arqueos"
        permissions = [
            ("ver_arqueos", "Puede ver e imprimir arqueos"),
            ("gestionar_arqueos", "Puede abrir y cerrar un nuevo arqueo"),
        ]


class DetallesArqueo(models.Model):
    DetalleArqueoID = models.AutoField(primary_key=True, db_column='DetalleArqueoID')
    ArqueoID = models.ForeignKey(
        Arqueos, 
        on_delete=models.CASCADE,
        db_column='ArqueoID'
    )
    ServicioID = models.ForeignKey(
        Servicios, 
        on_delete=models.SET_NULL, 
        db_column='ServicioID',
        null=True, 
        blank=True
    )
    VarianteProductoID = models.ForeignKey(
        'inventario.VarianteProducto',
        on_delete=models.SET_NULL,
        db_column='VarianteProductoID',
        null=True,
        blank=True
    )
    FacturaID = models.IntegerField(db_column='FacturaID', null=True, blank=True)
    Monto = models.DecimalField(max_digits=10, decimal_places=2, db_column='Monto')
    Anulada = models.BooleanField(db_column='Anulada', default=False)
    FechaRegistro = models.DateTimeField(db_column='FechaRegistro')
    Activa = models.BooleanField(db_column='Activa', default=True)
    MontoCordobas = models.DecimalField(max_digits=10, decimal_places=2, db_column='MontoCordobas', blank=True, null=True)
    MontoUSD = models.DecimalField(max_digits=10, decimal_places=2, db_column='MontoUSD', blank=True, null=True)
    TipoPago = models.CharField(max_length=10, db_column='TipoPago')
    Fecha = models.DateField(db_column='Fecha')
    ReciboID = models.ForeignKey(
        Recibo, 
        on_delete=models.SET_NULL, 
        db_column='ReciboID',
        null=True, 
        blank=True
    )

    def __str__(self):
        return f"Detalle de Arqueo #{self.ArqueoID.ArqueoID}"

    class Meta:
        db_table = 'DetallesArqueo'
        verbose_name = "DetallesArqueo"
        verbose_name_plural = "DetallesArqueos"



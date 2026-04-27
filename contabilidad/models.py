from django.db import models
from django.conf import settings

class CategoriaMovimiento(models.Model):
    """Clasificación de gastos e ingresos (Luz, Agua, Planilla, Venta Uniformes)"""
    nombre = models.CharField(max_length=100)
    tipo = models.CharField(max_length=10, choices=[('INGRESO', 'Ingreso'), ('EGRESO', 'Egreso')])
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Categoría de Movimiento"
        verbose_name_plural = "Categorías de Movimientos"

    def __str__(self):
        return f"{self.nombre} ({self.tipo})"

class MovimientoCaja(models.Model):
    """Registro detallado de entradas y salidas de dinero"""
    fecha = models.DateTimeField(auto_now_add=True)
    categoria = models.ForeignKey(CategoriaMovimiento, on_delete=models.PROTECT)
    descripcion = models.TextField()
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Usamos string 'docentes.Docente' para evitar errores de importación
    # Asegúrate que tu app se llame 'docentes' y el modelo 'Docente'
    docente = models.ForeignKey(
        'docentes.Docente', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="Solo si el movimiento es un pago a docente"
    )
    
    comprobante = models.CharField(max_length=50, blank=True, null=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    class Meta:
        verbose_name = "Movimiento de Caja"
        verbose_name_plural = "Movimientos de Caja"

    def __str__(self):
        return f"{self.fecha.date()} - {self.categoria.nombre} - {self.monto}"
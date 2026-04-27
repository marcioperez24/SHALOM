from django.db import models
from django.contrib.auth.models import User
import os

# TABLA 1: INFORMACIÓN PERSONAL (Lo que no cambia seguido)
# Función para organizar los archivos por carpeta de empleado
def path_documentos_empleado(instance, filename):
    # Se guardará en: media/empleados/[cedula]/[nombre_archivo]
    return os.path.join('empleados', instance.cedula, filename)

class Empleado(models.Model):
    nombres = models.CharField(max_length=150)
    apellidos = models.CharField(max_length=150)
    cedula = models.CharField(max_length=20, unique=True)
    numero_inss = models.CharField(max_length=20, blank=True, null=True)
    fecha_nacimiento = models.DateField()
    direccion = models.TextField(blank=True, null=True)
    telefono = models.CharField(max_length=20)
    cargo = models.CharField(max_length=100) # Ej: Administrador, Docente, Conserje
    fecha_contratacion = models.DateField()
    activo = models.BooleanField(default=True)

    # Solo agregamos estos dos como campos opcionales para no romper la migración
    curriculum = models.FileField(upload_to=path_documentos_empleado, blank=True, null=True)
    diplomas = models.FileField(upload_to=path_documentos_empleado, blank=True, null=True)

    def __str__(self):
        return f"{self.nombres} {self.apellidos}"

# TABLA 2: CONFIGURACIÓN SALARIAL (Donde defines su salario estático y ajustes)
class ContratoLaboral(models.Model):
    empleado = models.OneToOneField(Empleado, on_delete=models.CASCADE, related_name='contrato')
    salario_base = models.DecimalField(max_digits=12, decimal_places=2)
    paga_inss = models.BooleanField(default=True)
    paga_ir = models.BooleanField(default=True)
    # Porcentajes de antigüedad o bonos fijos si los tiene
    porcentaje_antiguedad = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    def __str__(self):
        return f"Contrato de {self.empleado.nombres}"

# TABLA 3: HISTÓRICO DE PLANILLA (Donde se guarda cada pago como la imagen)
class RegistroPlanilla(models.Model):
    """Histórico de pagos mensuales con desglose de ingresos y deducciones."""
    empleado = models.ForeignKey(Empleado, on_delete=models.PROTECT)
    mes = models.IntegerField()
    anio = models.IntegerField()
    
    # Prorrateo y Control de Tiempos
    TIPO_PERIODOS = [
        ('MENSUAL', 'Mensual Completo (30 Días)'),
        ('PRIMERA_QUINCENA', 'Primera Quincena (1-15)'),
        ('SEGUNDA_QUINCENA', 'Segunda Quincena (16-30)')
    ]
    tipo_periodo = models.CharField(max_length=20, choices=TIPO_PERIODOS, default='MENSUAL')
    dias_trabajados = models.DecimalField(max_digits=4, decimal_places=1, default=30.0)
    
    
    # Ingresos
    salario_basico = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Detalle de Horas Extras (Insumos para el cálculo)
    horas_extras_cantidad = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    horas_extras_valor_pago = models.DecimalField(max_digits=12, decimal_places=2, default=0) # Valor de 1hr extra (doble)
    horas_extras_monto = models.DecimalField(max_digits=12, decimal_places=2, default=0) # Resultado: Cantidad * Valor
    
    monto_antiguedad = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_devengado = models.DecimalField(max_digits=12, decimal_places=2) # Suma de ingresos
    
    # Deducciones de Ley (Nicaragua)
    inss_laboral = models.DecimalField(max_digits=12, decimal_places=2) # 7%
    ir_mensual = models.DecimalField(max_digits=12, decimal_places=2)   # Tabla DGI
    otras_deducciones = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Aportes Patronales (Costos ocultos para la empresa)
    inss_patronal = models.DecimalField(max_digits=12, decimal_places=2, default=0) # 22.5%
    inatec = models.DecimalField(max_digits=12, decimal_places=2, default=0)        # 2%
    
    
    # Neto Final
    total_a_pagar = models.DecimalField(max_digits=12, decimal_places=2) #
    
    # Metadatos
    fecha_emision = models.DateTimeField(auto_now_add=True)
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    contabilizado = models.BooleanField(default=False)

    class Meta:
        unique_together = ('empleado', 'mes', 'anio') # Evita duplicidad de pagos en un mismo periodo

    def __str__(self):
        return f"Planilla {self.empleado.nombres} - {self.mes}/{self.anio}"

# TABLA 4: CONTROL DE ASISTENCIA
class RegistroAsistencia(models.Model):
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE, related_name='asistencias')
    fecha = models.DateField()
    hora_entrada = models.TimeField(blank=True, null=True)
    hora_salida = models.TimeField(blank=True, null=True)
    
    minutos_tarde = models.IntegerField(default=0, help_text="Minutos de llegada después de la hora entrada + tolerancia")
    minutos_temprano = models.IntegerField(default=0, help_text="Minutos de salida antes de la hora de salida establecida")
    observaciones = models.TextField(blank=True, null=True, help_text="Justificaciones o notas")
    
    class Meta:
        unique_together = ('empleado', 'fecha')

    def __str__(self):
        return f"Asistencia {self.empleado.nombres} - {self.fecha.strftime('%d/%m/%Y')}"

# TABLA 5: HORARIOS DE TRABAJO
class HorarioEmpleado(models.Model):
    empleado = models.OneToOneField(Empleado, on_delete=models.CASCADE, related_name='horario')
    entrada_esperada = models.TimeField(default="08:00")
    salida_esperada = models.TimeField(default="16:00")
    minutos_tolerancia = models.IntegerField(default=15, help_text="Margen de gracia antes de marcar tardanza")
    
    def __str__(self):
        return f"Horario de {self.empleado}"

# TABLA 6: CALENDARIO DE NO LABORALES / FERIADOS
class DiaFeriado(models.Model):
    fecha = models.DateField(unique=True)
    motivo = models.CharField(max_length=200)
    es_nacional = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Día Feriado / No Laboral"
        verbose_name_plural = "Días Feriados / No Laborales"
        ordering = ['-fecha']

    def __str__(self):
        return f"{self.fecha.strftime('%d/%m/%Y')} - {self.motivo}"

# TABLA 5: LIQUIDACION FINAL (FINIQUITOS)
class RegistroLiquidacion(models.Model):
    empleado = models.OneToOneField(Empleado, on_delete=models.PROTECT)
    fecha_salida = models.DateField()
    
    MOTIVOS = [
        ('RENUNCIA_INMEDIATA', 'Renuncia Inmediata (Art. 44)'),
        ('RENUNCIA_PREAVISO', 'Renuncia con Preaviso 15 días (Art. 45)'),
        ('DESPIDO_INJUSTIFICADO', 'Despido Injustificado (Art. 45)'),
        ('MUTUO_ACUERDO', 'Mutuo Acuerdo / Fin de Contrato')
    ]
    motivo = models.CharField(max_length=30, choices=MOTIVOS)
    
    # Base de cálculo
    salario_base_calculo = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Componentes Legales (Pagos proporcionales)
    aguinaldo_proporcional = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    vacaciones_proporcionales = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    indemnizacion_antiguedad = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Gran Total
    monto_total_liquidado = models.DecimalField(max_digits=12, decimal_places=2)
    
    fecha_emision = models.DateTimeField(auto_now_add=True)
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    contabilizado = models.BooleanField(default=False)

    def __str__(self):
        return f"Liquidación {self.empleado.nombres} - Total C$ {self.monto_total_liquidado}"
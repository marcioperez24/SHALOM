# configuracion/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


class Nivel(models.Model):
    NivelID = models.AutoField(primary_key=True)
    NombreNivel = models.CharField(max_length=255)
    Activo = models.BooleanField(default=True)

    def __str__(self):
        return self.NombreNivel

    class Meta:
        db_table = 'Niveles'
        verbose_name_plural = "Niveles"
        
class Seccion(models.Model):
    SeccionID = models.AutoField(primary_key=True)
    NivelID = models.ForeignKey(
        'Nivel',
        on_delete=models.CASCADE,
        db_column='NivelID'
    )
    NombreSeccion = models.CharField(max_length=50)
    CuposDisponibles = models.IntegerField()
    Activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'Secciones'
        verbose_name_plural = "Secciones"

    def __str__(self):
        return self.NombreSeccion

class TServicio(models.Model):
    TipoServicioID = models.AutoField(primary_key=True)
    TipoServicio = models.CharField(max_length=50)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.TipoServicio

    class Meta:
        db_table = 'TServicio'
        verbose_name_plural = "Tipos de Servicio"
        
class Servicios(models.Model):
    ServicioID = models.AutoField(primary_key=True)
    NombreServicio = models.CharField(max_length=50)
    Precio = models.DecimalField(max_digits=10, decimal_places=2)
    NivelID = models.ForeignKey(
        'Nivel',
        on_delete=models.CASCADE,
        db_column='NivelID'
    )
    TipoServicioID = models.ForeignKey(
        'TServicio',
        on_delete=models.CASCADE,
        db_column='TipoServicioID'
    )
    Anio = models.IntegerField(db_column='Año')
    FechaCreacion = models.DateTimeField(db_column='FechaCreacion')
    Activo = models.BooleanField(default=True)

    def __str__(self):
        return self.NombreServicio

    class Meta:
        db_table = 'Servicios'
        verbose_name_plural = "Servicios"
        
        

# Nuevo modelo para la tabla Materias
class Materias(models.Model):
    MateriaID = models.AutoField(primary_key=True)
    NombreMateria = models.CharField(max_length=50)
    NivelID = models.ForeignKey(
        'Nivel',
        on_delete=models.CASCADE,
        db_column='NivelID'
    )
    FechaRegistro = models.DateTimeField(db_column='FechaRegistro', auto_now_add=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.NombreMateria

    class Meta:
        db_table = 'Materias'
        verbose_name_plural = "Materias"


class TipoMatricula(models.Model):
    TipoMatriculaID = models.AutoField(primary_key=True)
    Descripcion = models.CharField(max_length=100)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.Descripcion

    class Meta:
        db_table = 'TipoMatricula'
        verbose_name_plural = "Tipos de Matrícula"
        
class Turno(models.Model):
    TurnoID = models.AutoField(primary_key=True)
    NombreTurno = models.CharField(max_length=50)
    Descripcion = models.CharField(max_length=255, blank=True, null=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.NombreTurno

    class Meta:
        db_table = 'Turno'
        verbose_name_plural = "Turnos"


class Modalidades(models.Model):
    ModalidadID = models.AutoField(primary_key=True)
    NombreModalidad = models.CharField(max_length=50)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.NombreModalidad

    class Meta:
        db_table = 'Modalidades'
        verbose_name_plural = "Modalidades"

class Semestres(models.Model):
    SemestreID = models.AutoField(primary_key=True)
    NombreSemestre = models.CharField(max_length=50)
    FechaRegistro = models.DateTimeField(auto_now_add=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.NombreSemestre

    class Meta:
        db_table = 'Semestres'
        verbose_name_plural = "Semestres"
        
class Semestres(models.Model):
    SemestreID = models.AutoField(primary_key=True)
    NombreSemestre = models.CharField(max_length=50)
    FechaRegistro = models.DateTimeField(auto_now_add=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.NombreSemestre

    class Meta:
        db_table = 'Semestres'
        verbose_name_plural = "Semestres"

class Cortes(models.Model):
    CorteID = models.AutoField(primary_key=True)
    NombreCorte = models.CharField(max_length=50)
    FechaRegistro = models.DateTimeField(auto_now_add=True)
    SemestreID = models.ForeignKey('Semestres', on_delete=models.CASCADE, db_column='SemestreID')
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.NombreCorte

    class Meta:
        db_table = 'Cortes'
        verbose_name_plural = "Cortes"

class TiposCambio(models.Model):
    TipoCambioID = models.AutoField(primary_key=True)
    VigenciaInicio = models.DateField()
    VigenciaFin = models.DateField()
    CambioCompra = models.DecimalField(max_digits=10, decimal_places=4)
    CambioVenta = models.DecimalField(max_digits=10, decimal_places=4)
    MonedaOrigen = models.CharField(max_length=3)
    MonedaDestino = models.CharField(max_length=3)
    FechaRegistro = models.DateTimeField(auto_now_add=True)
    UsuarioID = models.ForeignKey(User, on_delete=models.CASCADE, db_column='UsuarioID')

    def __str__(self):
        return f"Tipo de Cambio {self.TipoCambioID} ({self.MonedaOrigen}/{self.MonedaDestino})"

    class Meta:
        db_table = 'TiposCambio'
        verbose_name_plural = "Tipos de Cambio"

class Licencia(models.Model):
    """Modelo para gestionar la licencia del sistema."""
    
    # Campo para la clave de licencia (opcional, si quieres un sistema de claves más complejo)
    clave = models.CharField(max_length=100, unique=True, blank=True, null=True) 
    
    # Fecha de inicio de la licencia (cuando se activó o se creó)
    fecha_activacion = models.DateField(default=timezone.now)
    
    # Fecha CRÍTICA: la fecha después de la cual el sistema debe bloquearse
    fecha_caducidad = models.DateField() 
    
    activa = models.BooleanField(default=True)
    
    def __str__(self):
        return f"Licencia hasta {self.fecha_caducidad}"

    def es_valida(self):
        """Método para verificar si la licencia está dentro del período de validez."""
        # Se verifica que no haya caducado y que esté marcada como activa
        return self.activa and self.fecha_caducidad >= timezone.now().date()
    
    # Método estático para obtener la única instancia de la licencia
    @staticmethod
    def obtener_licencia_actual():
        """Obtiene o crea la única licencia en el sistema."""
        try:
            return Licencia.objects.get(pk=1)
        except Licencia.DoesNotExist:
            # Crea una licencia por defecto (ej. 30 días de prueba) si no existe
            return Licencia.objects.create(
                pk=1,
                fecha_caducidad=timezone.now().date() + timedelta(days=30),
                clave="DEMO_TRIAL"
            )

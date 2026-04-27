from django.db import models
from django.contrib.auth import get_user_model
from configuracion.models import Seccion, Nivel, TipoMatricula, Modalidades, Turno, Materias, Semestres, Cortes
from datetime import date
from django.utils import timezone

# Obtiene el modelo de usuario activo en el proyecto
User = get_user_model()

class Estudiantes_Nueva(models.Model):
    EstudianteID = models.AutoField(primary_key=True)
    Codigo_MINED = models.CharField(max_length=50, blank=True, null=True)
    NombreCompleto = models.CharField(max_length=100)
    Genero = models.CharField(max_length=1)
    FechaNacimiento = models.DateField()
    # Hacemos que el campo 'Edad' no sea obligatorio
    Edad = models.IntegerField(null=True, blank=True)
    Direccion = models.CharField(max_length=255)
    NombreMadre = models.CharField(max_length=100)
    CedulaMadre = models.CharField(max_length=20, blank=True, null=True)
    TelefonoMadre = models.CharField(max_length=15)
    OcupacionMadre = models.CharField(max_length=100)
    NombrePadre = models.CharField(max_length=100)
    CedulaPadre = models.CharField(max_length=20, blank=True, null=True)
    TelefonoPadre = models.CharField(max_length=15)
    OcupacionPadre = models.CharField(max_length=100)
    NombreTutor = models.CharField(max_length=100, blank=True, null=True)
    CedulaTutor = models.CharField(max_length=20, blank=True, null=True)
    TelefonoTutor = models.CharField(max_length=15, blank=True, null=True)
    OcupacionTutor = models.CharField(max_length=100, blank=True, null=True)
    ResponsableEP = models.CharField(max_length=100)
    FotoCarnet = models.ImageField(upload_to='fotocarnet/', null=True, blank=True)
    ColegioProcedencia = models.CharField(max_length=255, blank=True, null=True)
    FechaRegistro = models.DateTimeField(auto_now_add=True)
    UsuarioID = models.ForeignKey(User, on_delete=models.CASCADE, db_column='UsuarioID')
    FechaRetiro = models.DateField(blank=True, null=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.NombreCompleto

    class Meta:
        db_table = 'Estudiantes_Nueva'
        verbose_name_plural = "Estudiantes"

    # Este método se ejecuta antes de guardar el modelo
    def save(self, *args, **kwargs):
        # Calculamos la edad a partir de la fecha de nacimiento
        if self.FechaNacimiento:
            hoy = date.today()
            edad = hoy.year - self.FechaNacimiento.year - ((hoy.month, hoy.day) < (self.FechaNacimiento.month, self.FechaNacimiento.day))
            self.Edad = edad
        
        super(Estudiantes_Nueva, self).save(*args, **kwargs)

class Matricula(models.Model):
    MatriculaID = models.AutoField(primary_key=True)
    EstudianteID = models.ForeignKey(Estudiantes_Nueva, on_delete=models.CASCADE, db_column='EstudianteID')
    NivelID = models.ForeignKey(Nivel, on_delete=models.CASCADE, db_column='NivelID')
    SeccionID = models.ForeignKey(Seccion, on_delete=models.CASCADE, db_column='SeccionID')
    FechaRegistro = models.DateTimeField(auto_now_add=True)
    FechaMatricula = models.DateField()
    AñoMatricula = models.IntegerField()
    TipoMatriculaID = models.ForeignKey(TipoMatricula, on_delete=models.CASCADE, db_column='TipoMatriculaID')
    ModalidadID = models.ForeignKey(Modalidades, on_delete=models.CASCADE, db_column='ModalidadID')
    activo = models.BooleanField(default=True)
    UsuarioID = models.ForeignKey(User, on_delete=models.CASCADE, db_column='UsuarioID')
    TurnoID = models.ForeignKey(Turno, on_delete=models.CASCADE, db_column='TurnoID')

    def __str__(self):
        return f"Matrícula de {self.EstudianteID.NombreCompleto} - Año {self.AñoMatricula}"

    class Meta:
        db_table = 'Matricula'
        verbose_name_plural = "Matrículas"

class Inscripciones(models.Model):
    InscripcionID = models.AutoField(primary_key=True)
    MatriculaID = models.ForeignKey(Matricula, on_delete=models.CASCADE, db_column='MatriculaID')
    EstudianteID = models.ForeignKey(Estudiantes_Nueva, on_delete=models.CASCADE, db_column='EstudianteID')
    MateriaID = models.ForeignKey(Materias, on_delete=models.CASCADE, db_column='MateriaID')
    FechaRegistro = models.DateTimeField(auto_now_add=True)
    NivelID = models.ForeignKey(Nivel, on_delete=models.CASCADE, db_column='NivelID')
    SeccionID = models.ForeignKey(Seccion, on_delete=models.CASCADE, db_column='SeccionID')
    ModalidadID = models.ForeignKey(Modalidades, on_delete=models.CASCADE, db_column='ModalidadID')
    TurnoID = models.ForeignKey(Turno, on_delete=models.CASCADE, db_column='TurnoID')
    AñoMatricula = models.IntegerField()

    def __str__(self):
        return f"Inscripción de {self.EstudianteID.NombreCompleto} en {self.MateriaID.NombreMateria}"

    class Meta:
        db_table = 'Inscripciones'
        verbose_name_plural = "Inscripciones"
        
# Matricula/models.py

class Calificaciones(models.Model):
    """
    Almacena la nota (cuantitativa y cualitativa) de una inscripción
    en un corte de evaluación específico.
    """
    CalificacionID = models.AutoField(primary_key=True)
    InscripcionID = models.ForeignKey(
        Inscripciones, 
        on_delete=models.CASCADE, 
        verbose_name="Inscripción",
        db_column='InscripcionID',
        related_name='calificaciones_m_inscripcion'
    )
    SemestreID = models.ForeignKey(
        Semestres, 
        on_delete=models.CASCADE, 
        verbose_name="Semestre",
        db_column='SemestreID',
        related_name='calificaciones_m_semestre'
    )
    CorteID = models.ForeignKey(
        Cortes, 
        on_delete=models.CASCADE, 
        verbose_name="Corte de Evaluación",
        db_column='CorteID',
        related_name='calificaciones_m_corte'
    )
    NotaCuantitativa = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        null=True, 
        blank=True, 
        verbose_name="Nota (0.00 a 100.00)"
    )
    NotaCualitativa = models.CharField(
        max_length=100, 
        null=True, 
        blank=True, 
        verbose_name="Comentario o Nota Cualitativa"
    )
    FechaRegistro = models.DateTimeField(
        default=timezone.now,
        verbose_name="Fecha de Registro"
    )
    
    # --- CAMBIO 1 ---
    # El nombre del campo ahora es 'MateriaID' (con 'a')
    # y 'db_column' también es 'MateriaID' (con 'a')
    MateriaID = models.ForeignKey(
        Materias, 
        on_delete=models.CASCADE, 
        verbose_name="Materia",
        db_column='MateriaID', # <--- Asegúrate que este sea el nombre real
        related_name='calificaciones_m_materia'
    )
    
    # --- CAMBIO 2 ---
    # El nombre del campo sigue siendo 'AnioMatricula' (con 'n') para Django,
    # pero le decimos que en la BD se llama 'AñoMatricula' (con 'ñ')
    AnioMatricula = models.IntegerField(
        verbose_name="Año de Matrícula",
        default=timezone.now().year,
        db_column='AñoMatricula' # <--- ESTA ES LA CORRECCIÓN CLAVE
    )

    def __str__(self):
        return f"Nota de {self.InscripcionID} en {self.CorteID}: {self.NotaCuantitativa}"

    class Meta:
        db_table = 'Calificaciones' 
        verbose_name = "Calificación"
        verbose_name_plural = "Calificaciones"
        unique_together = ('InscripcionID', 'CorteID')
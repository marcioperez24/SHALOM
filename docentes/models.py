# docentes/models.py
from django.db import models
from configuracion.models import Materias, Seccion, Nivel

class Docente(models.Model):
    nombres = models.CharField(max_length=100, verbose_name="Nombres")
    apellidos = models.CharField(max_length=100, verbose_name="Apellidos")
    cedula = models.CharField(max_length=20, unique=True, verbose_name="Cédula") # Clave principal
    telefono = models.CharField(max_length=20, blank=True, null=True, verbose_name="Teléfono")
    email = models.EmailField(blank=True, null=True, verbose_name="Correo Electrónico")
    direccion = models.TextField(blank=True, verbose_name="Dirección")
    fecha_contratacion = models.DateField(verbose_name="Fecha de Contratación")
    activo = models.BooleanField(default=True, verbose_name="Activo")

    class Meta:
        verbose_name = "Docente"
        verbose_name_plural = "Docentes"

    def __str__(self):
        return f"{self.nombres} {self.apellidos}"

class DocumentoDocente(models.Model):
    docente = models.ForeignKey(Docente, on_delete=models.CASCADE, related_name='documentos')
    nombre_documento = models.CharField(max_length=100, verbose_name="Nombre del documento")
    archivo = models.FileField(upload_to='documentos_docentes/', verbose_name="Archivo")
    fecha_subida = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de subida")

    class Meta:
        verbose_name = "Documento del Docente"
        verbose_name_plural = "Documentos de Docentes"

    def __str__(self):
        return f"{self.nombre_documento} - {self.docente}"
    
    
class CargaAcademica(models.Model):
    docente = models.ForeignKey(Docente, on_delete=models.CASCADE, related_name='cargas_academicas')
    
    # --- NUEVO CAMPO PRIMORDIAL ---
    nivel = models.ForeignKey(Nivel, on_delete=models.CASCADE, verbose_name="Nivel Académico")
    # ------------------------------

    materia = models.ForeignKey(Materias, on_delete=models.CASCADE, verbose_name="Materia")
    seccion = models.ForeignKey(Seccion, on_delete=models.CASCADE, verbose_name="Sección / Grupo")
    anio_lectivo = models.IntegerField(default=2025, verbose_name="Año Lectivo")

    class Meta:
        verbose_name = "Carga Académica"
        verbose_name_plural = "Cargas Académicas"
        # Evita duplicados exactos
        unique_together = ('docente', 'nivel', 'materia', 'seccion', 'anio_lectivo') 

    def __str__(self):
        return f"{self.docente} - {self.materia.NombreMateria} ({self.nivel.NombreNivel})"
# En academico/models.py (o donde gestiones los cursos)
from django.db import models
from docentes.models import Docente
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Docente, CargaAcademica, DocumentoDocente
from .forms import DocenteForm
from django.core.paginator import Paginator
from django.db.models import Q, Prefetch
from .forms import DocenteForm, CargaAcademicaForm
from django.http import JsonResponse
from configuracion.models import Materias, Seccion, Semestres, Cortes
from Matricula.models import Inscripciones, Calificaciones
from django.utils import timezone
from decimal import Decimal
from django.template.loader import get_template
from io import BytesIO
from django.core.files.base import ContentFile
from xhtml2pdf import pisa # type: ignore
from django.urls import reverse
import os
from django.conf import settings
from django.contrib.staticfiles import finders
from .forms import DocumentoForm
from django.contrib.auth.decorators import login_required, permission_required
from datetime import datetime
# from otra_app.models import Grado, Seccion (Importa tus modelos de grado si existen)

@permission_required('docentes.ver_docentes', raise_exception=True)
def docentes_home(request):
    """Pagina principal del Portal de Docentes con menú de opciones"""
    return render(request, 'docentes/docentes_home.html')

@permission_required('docentes.crear_docentes', raise_exception=True)
def registrar_docente(request):
    """Vista para registrar un nuevo maestro en el sistema"""
    if request.method == 'POST':
        form = DocenteForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '¡Docente registrado exitosamente!')
            return redirect('docentes_home') # Regresa al panel principal al terminar
        else:
            messages.error(request, 'Por favor corrige los errores en el formulario.')
    else:
        form = DocenteForm()

    return render(request, 'docentes/registro.html', {'form': form}) 

@permission_required('docentes.ver_lista_docentes', raise_exception=True)
def lista_docentes(request):
    """Muestra la lista de docentes con búsqueda y paginación"""
    query = request.GET.get('q') # Obtiene lo que el usuario escribió en el buscador
    docentes_list = Docente.objects.all().order_by('-id') # Los más nuevos primero

    if query:
        # Filtra si el nombre, apellido O cédula contienen el texto
        docentes_list = docentes_list.filter(
            Q(nombres__icontains=query) | 
            Q(apellidos__icontains=query) |
            Q(cedula__icontains=query)
        )

    # Paginación: Mostrar 10 docentes por página
    paginator = Paginator(docentes_list, 10) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'query': query # Pasamos la búsqueda para no perderla al cambiar de página
    }
    return render(request, 'docentes/lista.html', context)


@permission_required('docentes.editar_docentes', raise_exception=True)
def editar_docente(request, id):
    """Vista para editar la información de un docente existente"""
    docente = get_object_or_404(Docente, id=id)

    if request.method == 'POST':
        form = DocenteForm(request.POST, instance=docente)
        if form.is_valid():
            form.save()
            messages.success(request, f'Datos de {docente.nombres} actualizados correctamente.')
            return redirect('lista_docentes')
    else:
        # Carga el formulario con los datos actuales del docente
        form = DocenteForm(instance=docente)

    return render(request, 'docentes/registro.html', {'form': form, 'editar': True})

@permission_required('docentes.eliminar_docentes', raise_exception=True)
def cambiar_estado_docente(request, id):
    """Cambia el estado de activo a inactivo y viceversa (Soft Delete)"""
    docente = get_object_or_404(Docente, id=id)
    
    # Cambiamos el estado al opuesto del que tiene actualmente
    if docente.activo:
        docente.activo = False
        messages.warning(request, f'El docente {docente.nombres} ha sido dado de baja.')
    else:
        docente.activo = True
        messages.success(request, f'El docente {docente.nombres} ha sido reactivado exitosamente.')
    
    docente.save()
    return redirect('lista_docentes')

def acceso_docente(request):
    """Vista para que el docente ingrese su cédula"""
    if request.method == "POST":
        cedula_ingresada = request.POST.get('cedula')
        
        try:
            # Buscamos al docente por cédula
            docente = Docente.objects.get(cedula=cedula_ingresada, activo=True)
            
            # Si existe, guardamos su ID en la sesión
            request.session['docente_id'] = docente.id
            
            # Redirigimos a su panel
            return redirect('panel_docente')
            
        except Docente.DoesNotExist:
            messages.error(request, "⚠️ Cédula no encontrada o docente inactivo.")
            
    return render(request, 'docentes/acceso.html')

@permission_required('docentes.ver_panel_docentes', raise_exception=True)
def panel_docente(request):
    """Vista que muestra las clases del docente con filtro de año lectivo"""
    docente_id = request.session.get('docente_id')
    
    if not docente_id:
        return redirect('acceso_docente')
    
    docente = get_object_or_404(Docente, id=docente_id)
    
    # 1. Obtener el año del filtro o usar el año actual por defecto
    anio_actual = str(datetime.now().year)
    anio_seleccionado = request.GET.get('anio', anio_actual)
    
    # 2. Obtener todos los años disponibles en la carga académica para el combo box
    # Esto evita que el docente seleccione años donde no hay nada registrado
    anios_disponibles = CargaAcademica.objects.filter(
        docente=docente
    ).values_list('anio_lectivo', flat=True).distinct().order_by('-anio_lectivo')
    
    # Si el año actual no está en la lista (porque es inicio de año), lo agregamos
    anios_lista = list(anios_disponibles)
    if anio_actual not in anios_lista:
        anios_lista.insert(0, anio_actual)

    # 3. Filtrar cargas por docente y el año seleccionado
    cargas = CargaAcademica.objects.filter(
        docente=docente, 
        anio_lectivo=anio_seleccionado
    )
    
    context = {
        'docente': docente,
        'cargas': cargas,
        'anios_disponibles': anios_lista,
        'anio_seleccionado': anio_seleccionado
    }
    return render(request, 'docentes/panel.html', context)

@permission_required('docentes.ver_cargaacademica', raise_exception=True)
def lista_cargas(request):
    query = request.GET.get('q')
    anio_actual = 2026 

    # 1. Traemos TODOS los docentes (sin filtros de búsqueda inicialmente)
    # Usamos prefetch_related normal para que el template acceda a todo el historial
    docentes_list = Docente.objects.all().prefetch_related('cargas_academicas').order_by('apellidos')

    # 2. SOLO si hay una búsqueda, filtramos
    if query:
        docentes_list = docentes_list.filter(
            Q(nombres__icontains=query) | 
            Q(apellidos__icontains=query) |
            Q(cargas_academicas__materia__NombreMateria__icontains=query)
        ).distinct()

    # Paginación
    paginator = Paginator(docentes_list, 6) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'query': query,
        'anio_actual': anio_actual
    }
    return render(request, 'docentes/lista_cargas.html', context)

@permission_required('docentes.eliminar_cargaacademica', raise_exception=True)
def eliminar_carga(request, id):
    """Elimina una asignación académica específica"""
    carga = get_object_or_404(CargaAcademica, id=id)
    
    nombre_materia = carga.materia.NombreMateria
    nombre_docente = carga.docente.nombres
    
    carga.delete()
    
    messages.warning(request, f"Se ha eliminado la asignación de '{nombre_materia}' al docente {nombre_docente}.")
    return redirect('lista_cargas')

@permission_required('docentes.crear_cargaacademica', raise_exception=True)
def asignar_carga(request):
    if request.method == 'POST':
        form = CargaAcademicaForm(request.POST)
        if form.is_valid():
            # Datos fijos para todas las materias seleccionadas
            docente = form.cleaned_data['docente']
            nivel = form.cleaned_data['nivel']
            seccion = form.cleaned_data['seccion']
            anio = form.cleaned_data['anio_lectivo']
            
            # LISTA de materias (Array)
            materias_seleccionadas = form.cleaned_data['materias']
            
            contador = 0
            
            # Recorremos la lista y guardamos una por una
            for materia in materias_seleccionadas:
                # Usamos get_or_create para evitar duplicados automáticamente
                obj, created = CargaAcademica.objects.get_or_create(
                    docente=docente,
                    nivel=nivel,
                    seccion=seccion,
                    materia=materia,
                    anio_lectivo=anio
                )
                if created:
                    contador += 1
            
            if contador > 0:
                messages.success(request, f"¡Listo! Se asignaron {contador} materias exitosamente.")
            else:
                messages.warning(request, "Las materias seleccionadas ya estaban asignadas a este docente.")
                
            return redirect('lista_cargas')
    else:
        form = CargaAcademicaForm()

    return render(request, 'docentes/asignar_carga.html', {'form': form})


def cargar_opciones_carga(request):
    nivel_id = request.GET.get('nivel_id')
    
    materias = []
    secciones = []

    if nivel_id:
        print(f"--- DEBUG AJAX: Buscando para Nivel ID: {nivel_id} ---")
        
        # INTENTO 1: Filtrar Secciones (Que dices que sí funciona)
        try:
            secciones = list(Seccion.objects.filter(NivelID_id=nivel_id, Activo=True).values('SeccionID', 'NombreSeccion'))
            print(f"Secciones encontradas: {len(secciones)}")
        except Exception as e:
            print(f"Error buscando secciones: {e}")

        # INTENTO 2: Filtrar Materias (Aquí está el problema)
        try:
            # Probamos primero con la forma estándar
            qs_materias = Materias.objects.filter(NivelID_id=nivel_id, activo=True)
            
            # Si no encuentra nada, probamos quitando el '_id' (a veces pasa con db_column)
            if not qs_materias.exists():
                print("Intento 1 vacío. Probando filtro alternativo...")
                qs_materias = Materias.objects.filter(NivelID=nivel_id, activo=True)

            materias = list(qs_materias.values('MateriaID', 'NombreMateria'))
            print(f"Materias encontradas: {len(materias)}")
            
        except Exception as e:
            print(f"Error buscando materias: {e}")
            # Intento de emergencia por si el nombre del campo activo está mal
            try:
                materias = list(Materias.objects.filter(NivelID_id=nivel_id).values('MateriaID', 'NombreMateria'))
                print(f"Materias encontradas (sin filtrar activo): {len(materias)}")
            except:
                pass

    return JsonResponse({'materias': materias, 'secciones': secciones})

def imprimir_carga_docente(request, docente_id):
    """Genera un reporte imprimible filtrado por el año seleccionado"""
    docente = get_object_or_404(Docente, id=docente_id)
    
    # 1. Obtenemos el año de la URL (ej: ?anio=2026). Si no hay, usamos el actual.
    anio_seleccionado = request.GET.get('anio')
    if not anio_seleccionado:
        anio_seleccionado = timezone.now().year
    
    # 2. Filtramos las cargas por ese año específico
    cargas = CargaAcademica.objects.filter(
        docente=docente, 
        anio_lectivo=anio_seleccionado
    ).order_by('nivel', 'seccion', 'materia')
    
    context = {
        'docente': docente,
        'cargas': cargas,
        'anio_reporte': anio_seleccionado, # Enviamos el año al template
        'fecha_impresion': timezone.now()
    }
    return render(request, 'docentes/imprimir_carga.html', context)

def gestion_notas(request, carga_id):
    # 1. Validar que la carga pertenezca al docente logueado
    docente_id = request.session.get('docente_id')
    if not docente_id:
        return redirect('acceso_docente')
    
    carga = get_object_or_404(CargaAcademica, id=carga_id, docente_id=docente_id)

    # 2. Filtros
    semestre_id = request.GET.get('semestre')
    corte_id = request.GET.get('corte')
    
    semestres = Semestres.objects.filter(activo=True)
    cortes = Cortes.objects.filter(activo=True)
    
    if semestre_id:
        cortes = cortes.filter(SemestreID_id=semestre_id)

    alumnos_notas = []
    
    # 3. Buscar alumnos
    if semestre_id and corte_id:
        inscripciones = Inscripciones.objects.filter(
            MateriaID=carga.materia,
            SeccionID=carga.seccion,
            AñoMatricula=carga.anio_lectivo,
            
            # --- FILTROS NUEVOS (El blindaje) ---
            MatriculaID__activo=True,   # <--- Solo matrículas vigentes (Esto elimina a la niña que se cambió)
            EstudianteID__activo=True   # <--- Solo estudiantes que no han sido dados de baja del colegio
            # ------------------------------------
            
        ).select_related('EstudianteID').order_by('EstudianteID__NombreCompleto')
        
        for inscripcion in inscripciones:
            nota = Calificaciones.objects.filter(
                InscripcionID=inscripcion,
                SemestreID_id=semestre_id,
                CorteID_id=corte_id,
                MateriaID=carga.materia
            ).first()
            
            alumnos_notas.append({
                'inscripcion': inscripcion,
                'nota': nota
            })

        # --- LOGICA DE GUARDADO (POST) ---
        if request.method == 'POST':
                    count = 0
                    for item in alumnos_notas:
                        inscripcion = item['inscripcion']
                        input_name = f"nota_{inscripcion.InscripcionID}"
                        # Nota: Ya no necesitamos leer la observación del POST si la vamos a calcular automática
                        # observacion_name = f"obs_{inscripcion.InscripcionID}" 
                        
                        valor_nota = request.POST.get(input_name)
                        # observacion = request.POST.get(observacion_name) 
                        
                        if valor_nota:
                            # --- AQUÍ USAMOS TU FUNCIÓN ---
                            nota_cualitativa_calc = get_nota_cualitativa(valor_nota)
                            # ------------------------------

                            calificacion, created = Calificaciones.objects.update_or_create(
                                InscripcionID=inscripcion,
                                SemestreID_id=semestre_id,
                                CorteID_id=corte_id,
                                MateriaID=carga.materia,
                                defaults={
                                    'NotaCuantitativa': valor_nota,
                                    'NotaCualitativa': nota_cualitativa_calc, # Guardamos la letra calculada (AA, AS, etc)
                                    'AnioMatricula': carga.anio_lectivo
                                }
                            )
                            count += 1
                    
                    messages.success(request, f"Se guardaron correctamente {count} calificaciones.")
                    return redirect(f"{request.path}?semestre={semestre_id}&corte={corte_id}")

    context = {
        'carga': carga,
        'semestres': semestres,
        'cortes': cortes,
        'semestre_seleccionado': int(semestre_id) if semestre_id else None,
        'corte_seleccionado': int(corte_id) if corte_id else None,
        'alumnos_notas': alumnos_notas
    }
    return render(request, 'docentes/ingreso_notas.html', context)

def get_nota_cualitativa(nota):
    """Convierte una nota cuantitativa (0-100) a su equivalente cualitativo."""
    if not nota:
        return ""
    try:
        valor = Decimal(nota) 
        if valor >= 90: return "AA" # Aprendizaje Avanzado
        if valor >= 76: return "AS" # Aprendizaje Satisfactorio
        if valor >= 60: return "AF" # Aprendizaje Fundamental
        if valor >= 0: return "AI"  # Aprendizaje Inicial
        return "" 
    except:
        return ""
    

def imprimir_acta_notas(request, carga_id):
    # Validamos docente
    docente_id = request.session.get('docente_id')
    if not docente_id: return redirect('acceso_docente')
    
    carga = get_object_or_404(CargaAcademica, id=carga_id, docente_id=docente_id)
    
    # Obtenemos semestre y corte de la URL (son obligatorios para imprimir)
    semestre_id = request.GET.get('semestre')
    corte_id = request.GET.get('corte')
    
    if not semestre_id or not corte_id:
        messages.error(request, "Debe seleccionar Semestre y Corte para imprimir.")
        return redirect('gestion_notas', carga_id=carga.id)

    # Recuperamos los nombres para el título
    semestre = get_object_or_404(Semestres, SemestreID=semestre_id)
    corte = get_object_or_404(Cortes, CorteID=corte_id)

    # Buscamos las notas ya guardadas
    # (Aquí filtramos directamente Calificaciones, no inscripciones, porque solo imprimimos lo que tiene nota)
    calificaciones = Calificaciones.objects.filter(
        MateriaID=carga.materia,
        SemestreID_id=semestre_id,
        CorteID_id=corte_id,
        AnioMatricula=carga.anio_lectivo
    ).select_related('InscripcionID__EstudianteID').order_by('InscripcionID__EstudianteID__NombreCompleto')

    context = {
        'carga': carga,
        'semestre': semestre,
        'corte': corte,
        'calificaciones': calificaciones,
        'fecha_impresion': timezone.now()
    }
    return render(request, 'docentes/imprimir_acta.html', context)


def link_callback(uri, rel):
    """
    Convierte URLs de static/media a rutas absolutas del sistema operativo
    para que xhtml2pdf pueda leer los archivos.
    """
    sUrl = settings.STATIC_URL  # Generalmente '/static/'
    mUrl = settings.MEDIA_URL   # Generalmente '/media/'
    mRoot = settings.MEDIA_ROOT
    sRoot = settings.STATIC_ROOT

    # 1. Si es un archivo MEDIA (subido por usuarios)
    if uri.startswith(mUrl):
        path = os.path.join(mRoot, uri.replace(mUrl, ""))

    # 2. Si es un archivo STATIC (logos, css, estilos)
    elif uri.startswith(sUrl):
        # Quitamos el prefijo '/static/' para que quede solo 'principal/img/logo.png'
        path = uri.replace(sUrl, "")
        
        # Usamos finders de Django para encontrar dónde está el archivo realmente
        absolute_path = finders.find(path)
        
        if absolute_path:
            path = absolute_path
        else:
            # Si finders falla, intentamos buscar en STATIC_ROOT (Producción)
            # o construimos la ruta manualmente en 'static' del proyecto
            if sRoot:
                path = os.path.join(sRoot, path)
            else:
                # Fallback para desarrollo si STATIC_ROOT no está configurado
                path = os.path.join(settings.BASE_DIR, 'static', path)

    else:
        return uri  # Si es una ruta local absoluta, la dejamos igual

    # Verificación final
    if not os.path.isfile(path):
        # Si no existe, devolvemos None para que no explote, 
        # aunque la imagen saldrá rota en el PDF.
        print(f"⚠️ Advertencia: No se encontró el archivo para el PDF: {path}")
        return None

    return path


# --- VISTA ACTUALIZADA: ARCHIVAR ACTA ---
def archivar_acta_digital(request, carga_id):
    # ... (Toda la lógica de obtener carga, semestre, calificaciones IGUAL QUE ANTES) ...
    docente_id = request.session.get('docente_id')
    if not docente_id: return redirect('acceso_docente')

    carga = get_object_or_404(CargaAcademica, id=carga_id, docente_id=docente_id)
    semestre_id = request.GET.get('semestre')
    corte_id = request.GET.get('corte')
    
    semestre = get_object_or_404(Semestres, SemestreID=semestre_id)
    corte = get_object_or_404(Cortes, CorteID=corte_id)
    
    calificaciones = Calificaciones.objects.filter(
        MateriaID=carga.materia, SemestreID_id=semestre_id, CorteID_id=corte_id, AnioMatricula=carga.anio_lectivo
    ).select_related('InscripcionID__EstudianteID').order_by('InscripcionID__EstudianteID__NombreCompleto')

    # Renderizar HTML
    template = get_template('docentes/pdf_acta.html')
    
    context = {
        'carga': carga, 'semestre': semestre, 'corte': corte,
        'calificaciones': calificaciones, 'fecha_impresion': timezone.now(),
        # Ya no necesitamos 'es_pdf' porque este archivo ES solo para PDF
    }
    html = template.render(context)

    # Convertir a PDF usando el link_callback
    result = BytesIO()
    
    # ---> AQUÍ ESTÁ EL CAMBIO CLAVE: agregamos link_callback <---
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result, link_callback=link_callback)

    if not pdf.err:
        nombre_archivo = f"Acta_{corte.NombreCorte}_{carga.materia.NombreMateria}_{carga.anio_lectivo}.pdf"
        titulo_doc = f"Acta: {carga.materia.NombreMateria} - {corte.NombreCorte}"
        
        # Lógica anti-duplicados (la que te di antes)
        DocumentoDocente.objects.filter(docente_id=docente_id, nombre_documento=titulo_doc).delete()

        DocumentoDocente.objects.create(
            docente_id=docente_id,
            nombre_documento=titulo_doc,
            archivo=ContentFile(result.getvalue(), nombre_archivo),
            fecha_subida=timezone.now()
        )
        messages.success(request, "✅ PDF generado con imágenes correctamente.")
    else:
        messages.error(request, "Error al generar PDF.")

    return redirect(f"{reverse('gestion_notas', args=[carga.id])}?semestre={semestre_id}&corte={corte_id}")

def validar_acceso_documentos(request):
    # --- BORRA O COMENTA ESTAS 2 LÍNEAS ---
    # if request.session.get('docente_id'):
    #     return redirect('lista_documentos')
    # --------------------------------------

    # El resto déjalo igual:
    if request.method == 'POST':
        cedula = request.POST.get('cedula')
        # Buscamos al docente (ignorando mayúsculas/minúsculas y espacios)
        try:
            docente = Docente.objects.get(cedula__iexact=cedula.strip())
            
            # Actualizamos la sesión (por seguridad) y dejamos pasar
            request.session['docente_id'] = docente.id
            return redirect('lista_documentos')
            
        except Docente.DoesNotExist:
            messages.error(request, "❌ Cédula no encontrada o no registrada.")
            
    return render(request, 'docentes/validar_documentos.html')

@permission_required('docentes.ver_docdocentes', raise_exception=True)
def lista_documentos(request):
    docente_id = request.session.get('docente_id')
    if not docente_id: return redirect('validar_acceso_documentos')

    docente = get_object_or_404(Docente, id=docente_id)
    
    # Obtenemos los documentos ordenados por el más reciente
    documentos = DocumentoDocente.objects.filter(docente=docente).order_by('-fecha_subida')

    return render(request, 'docentes/mis_documentos.html', {
        'docente': docente, 
        'documentos': documentos
    })

@permission_required('docentes.eliminar_docdocentes', raise_exception=True)
# --- VISTA 3: ELIMINAR DOCUMENTO ---
def eliminar_documento(request, doc_id):
    docente_id = request.session.get('docente_id')
    if not docente_id: return redirect('validar_acceso_documentos')

    documento = get_object_or_404(DocumentoDocente, id=doc_id, docente_id=docente_id)
    
    # Intentamos borrar el archivo físico del servidor para no ocupar espacio
    try:
        if documento.archivo:
            if os.path.isfile(documento.archivo.path):
                os.remove(documento.archivo.path)
    except Exception as e:
        print(f"Error borrando archivo: {e}")

    documento.delete()
    messages.success(request, "Documento eliminado correctamente.")
    return redirect('lista_documentos')

# --- VISTA 4: SUBIR DOCUMENTO MANUALMENTE ---
def subir_documento_manual(request):
    docente_id = request.session.get('docente_id')
    if not docente_id: return redirect('acceso_docente')
    
    if request.method == 'POST':
        docente = get_object_or_404(Docente, id=docente_id)
        
        form = DocumentoForm(request.POST, request.FILES)
        
        if form.is_valid():
            documento = form.save(commit=False)
            documento.docente = docente # Asignamos el docente de la sesión
            documento.save()
            
            messages.success(request, "✅ Documento subido exitosamente.")
        else:
            messages.error(request, "❌ Error al subir el archivo. Verifique el formato.")
            
    return redirect('lista_documentos')


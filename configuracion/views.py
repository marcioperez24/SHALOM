# configuracion/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.forms import UserCreationForm # Importa el formulario de creación de usuario
from django.contrib import messages # Para mostrar mensajes al usuario
from .forms import CustomUserCreationForm, CustomUserChangeForm
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.forms import UserChangeForm
from django.core.exceptions import ValidationError
from django.shortcuts import render, redirect, get_object_or_404
from .models import Nivel, Seccion, TServicio, Servicios, Materias, TipoMatricula, Turno
from .forms import NivelForm, SeccionForm, TServicioForm, ServiciosForm, MateriasForm, TipoMatriculaForm, TurnoForm, CustomUserChangeForm, RestablecerContrasenaAdminForm
from .models import Modalidades, Semestres, Cortes, TiposCambio
from .forms import ModalidadesForm, SemestresForm, CortesForm, TiposCambioForm
from django.core.paginator import Paginator
from .models import Licencia
from .forms import LicenciaAdminForm
from django.db.models import Q
import openpyxl
from django.http import HttpResponse
from openpyxl.worksheet.datavalidation import DataValidation
from django.utils import timezone


@login_required(login_url='/login/')
@permission_required('configuracion.ver_configuracion', raise_exception=True)
def configuracion_home(request):
    return render(request, 'configuracion/configuracion_home.html', {})

@login_required(login_url='/login/')
@permission_required('auth.ver_usuario', raise_exception=True)
def listar_usuarios(request):
    # Aquí traeremos la lista de usuarios más adelante
    return render(request, 'configuracion/listar_usuarios.html', {})

@login_required(login_url='/login/')
@permission_required('auth.crear_usuario', raise_exception=True)
def crear_usuario(request):
    # Aquí manejaremos el formulario de creación de usuario
    return render(request, 'configuracion/crear_usuario.html', {})


@login_required(login_url='/login/')
@permission_required('auth.crear_usuario', raise_exception=True)
def crear_usuario(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST) # <-- ¡Cambio aquí!
        if form.is_valid():
            form.save()
            messages.success(request, '¡Usuario creado exitosamente!')
            return redirect('configuracion:listar_usuarios')
        else:
            messages.error(request, 'Error al crear el usuario. Por favor, revisa los datos.')
    else:
        form = CustomUserCreationForm() # <-- ¡Cambio aquí!

    context = {
        'form': form
    }
    return render(request, 'configuracion/crear_usuario.html', context)

User = get_user_model()

@login_required(login_url='/login/')
@permission_required('auth.ver_usuario', raise_exception=True)
def listar_usuarios(request):
    query = request.GET.get('q', '')
    # Obtenemos todos los usuarios ordenados por nombre de usuario
    usuarios_list = User.objects.all().order_by('username')

    if query:
        usuarios_list = usuarios_list.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query)
        )

    # Configurado para mostrar exactamente 10 usuarios
    paginator = Paginator(usuarios_list, 10) 
    page_number = request.GET.get('page')
    usuarios = paginator.get_page(page_number)

    context = {
        'usuarios': usuarios,
        'query': query
    }
    return render(request, 'configuracion/listar_usuarios.html', context)


User = get_user_model()

@login_required(login_url='/login/')
@permission_required('auth.editar_usuario', raise_exception=True)
def editar_usuario(request, user_id):
    usuario = get_object_or_404(User, pk=user_id)
    
    # Inicializar formularios fuera del if/else principal para que estén disponibles en el contexto
    data_form = CustomUserChangeForm(instance=usuario)
    password_form = RestablecerContrasenaAdminForm() # Este formulario no necesita instancia

    if request.method == 'POST':
        action = request.POST.get('action') # Leemos el campo oculto 'action'
        
        if action == 'edit_data':
            # --- LÓGICA DE EDICIÓN DE DATOS ---
            data_form = CustomUserChangeForm(request.POST, instance=usuario)
            if data_form.is_valid():
                data_form.save()
                messages.success(request, f'¡Los datos del usuario {usuario.username} han sido actualizados exitosamente!')
                return redirect('configuracion:editar_usuario', user_id=usuario.pk) # Redirigir a la misma página
            
            # Si la validación falla, data_form tiene errores, pero password_form sigue limpio
            
        elif action == 'reset_password':
            # --- LÓGICA DE RESTABLECIMIENTO DE CONTRASEÑA ---
            password_form = RestablecerContrasenaAdminForm(request.POST)
            
            if password_form.is_valid():
                nueva_contrasena = password_form.cleaned_data['nueva_contrasena']
                
                # *** CÓDIGO CRÍTICO Y SEGURO PARA EL CAMBIO ***
                usuario.set_password(nueva_contrasena)
                usuario.save()
                
                # Si el administrador se está cambiando su propia contraseña, 
                # debemos actualizar su hash de sesión para evitar que se desloguee
                if request.user.pk == usuario.pk:
                     update_session_auth_hash(request, usuario)

                messages.success(request, f'¡La contraseña del usuario {usuario.username} ha sido restablecida exitosamente!')
                return redirect('configuracion:editar_usuario', user_id=usuario.pk) # Redirigir a la misma página
            
            # Si la validación falla, password_form tiene errores, pero data_form sigue limpio
            
        else:
             messages.error(request, 'Acción no reconocida.')


    context = {
        'data_form': data_form,        # Formulario de edición de datos
        'password_form': password_form,  # Formulario de cambio de contraseña
        'usuario': usuario,
    }
    return render(request, 'configuracion/editar_usuario.html', context)

@login_required(login_url='/login/')
@permission_required('auth.eliminar_usuario', raise_exception=True)
def deshabilitar_usuario(request, user_id):
    usuario = get_object_or_404(User, pk=user_id)
    if request.method == 'POST':
        # Tu lógica de soft delete:
        # 1. Cambiar is_active a False (0)
        # 2. Cambiar is_staff a False (0)
        usuario.is_active = False
        usuario.is_staff = False
        usuario.save()

        messages.info(request, f'El usuario {usuario.username} ha sido deshabilitado y ya no se muestra.')
        return redirect('configuracion:listar_usuarios')

    return render(request, 'configuracion/confirmar_deshabilitar.html', {'usuario': usuario})



# Vistas para la gestión de los Niveles
@login_required(login_url='/login/')
@permission_required('configuracion.ver_nivel', raise_exception=True)
def listar_niveles(request):
    Niveles = Nivel.objects.filter(Activo=True).order_by('NombreNivel')
    context = {
        'niveles': Niveles
    }
    return render(request, 'configuracion/niveles/listar_niveles.html', context)

@login_required(login_url='/login/')
@permission_required('configuracion.crear_nivel', raise_exception=True)
def crear_Nivel(request):
    if request.method == 'POST':
        form = NivelForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Nivel creado exitosamente.')
            return redirect('configuracion:listar_niveles')
    else:
        form = NivelForm()
    
    return render(request, 'configuracion/niveles/crear_nivel.html', {'form': form})

@login_required(login_url='/login/')
@permission_required('configuracion.editar_nivel', raise_exception=True)
def editar_Nivel(request, NivelID):
    # Cambiamos el nombre de la variable a 'nivel'
    nivel = get_object_or_404(Nivel, NivelID=NivelID)
    
    if request.method == 'POST':
        form = NivelForm(request.POST, instance=nivel)
        if form.is_valid():
            form.save()
            messages.success(request, 'Nivel actualizado exitosamente.')
            return redirect('configuracion:listar_niveles')
    else:
        form = NivelForm(instance=nivel)
    
    return render(request, 'configuracion/niveles/editar_Nivel.html', {'form': form, 'nivel': nivel})

@login_required(login_url='/login/')
@permission_required('configuracion.eliminar_nivel', raise_exception=True)
def eliminar_Nivel(request, NivelID):
    # Cambiamos el nombre de la variable a 'nivel'
    nivel = get_object_or_404(Nivel, NivelID=NivelID)
    
    if request.method == 'POST':
        # Usamos la variable 'nivel' para acceder al campo 'Activo'
        nivel.Activo = False
        nivel.save()
        messages.success(request, 'Nivel desactivado exitosamente.')
        return redirect('configuracion:listar_niveles')
    
    return render(request, 'configuracion/niveles/confirmar_eliminar_nivel.html', {'nivel': nivel})


# Vistas para la gestión de las Secciones
@login_required(login_url='/login/')
@permission_required('configuracion.ver_seccion', raise_exception=True)
def listar_secciones(request):
    secciones = Seccion.objects.filter(Activo=True).order_by('NombreSeccion')
    context = {
        'secciones': secciones
    }
    return render(request, 'configuracion/secciones/listar_secciones.html', context)

@login_required(login_url='/login/')
@permission_required('configuracion.crear_tservicio', raise_exception=True)
def crear_seccion(request):
    if request.method == 'POST':
        form = SeccionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Sección creada exitosamente.')
            return redirect('configuracion:listar_secciones')
    else:
        form = SeccionForm()
    
    return render(request, 'configuracion/secciones/crear_seccion.html', {'form': form})

@login_required(login_url='/login/')
@permission_required('configuracion.editar_tservicio', raise_exception=True)
def editar_seccion(request, SeccionID):
    seccion = get_object_or_404(Seccion, SeccionID=SeccionID)
    if request.method == 'POST':
        form = SeccionForm(request.POST, instance=seccion)
        if form.is_valid():
            form.save()
            messages.success(request, 'Sección actualizada exitosamente.')
            return redirect('configuracion:listar_secciones')
    else:
        form = SeccionForm(instance=seccion)
    
    return render(request, 'configuracion/secciones/editar_seccion.html', {'form': form, 'seccion': seccion})

@login_required(login_url='/login/')
@permission_required('configuracion.eliminar_tservicio', raise_exception=True)
def eliminar_seccion(request, SeccionID):
    seccion = get_object_or_404(Seccion, SeccionID=SeccionID)
    if request.method == 'POST':
        seccion.Activo = False
        seccion.save()
        messages.success(request, 'Sección desactivada exitosamente.')
        return redirect('configuracion:listar_secciones')
    
    return render(request, 'configuracion/secciones/confirmar_eliminar_seccion.html', {'seccion': seccion})


# Vistas para la gestión de Tipos de Servicio
@login_required(login_url='/login/')
@permission_required('configuracion.ver_tservicio', raise_exception=True)
def listar_tservicios(request):
    tservicios = TServicio.objects.filter(activo=True).order_by('TipoServicio')
    context = {
        'tservicios': tservicios
    }
    return render(request, 'configuracion/Tservicios/listar_tservicios.html', context)

@login_required(login_url='/login/')
@permission_required('configuracion.crear_tservicio', raise_exception=True)
def crear_tservicio(request):
    if request.method == 'POST':
        form = TServicioForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Tipo de servicio creado exitosamente.')
            return redirect('configuracion:listar_tservicios') # Cambiado
    else:
        form = TServicioForm()
    
    return render(request, 'configuracion/Tservicios/crear_tservicio.html', {'form': form})

@login_required(login_url='/login/')
@permission_required('configuracion.editar_tservicio', raise_exception=True)
def editar_tservicio(request, TipoServicioID):
    servicio = get_object_or_404(TServicio, TipoServicioID=TipoServicioID)
    if request.method == 'POST':
        form = TServicioForm(request.POST, instance=servicio)
        if form.is_valid():
            form.save()
            messages.success(request, 'Tipo de servicio actualizado exitosamente.')
            return redirect('configuracion:listar_tservicios') # Cambiado
    else:
        form = TServicioForm(instance=servicio)
    
    return render(request, 'configuracion/Tservicios/editar_tservicio.html', {'form': form, 'servicio': servicio})

@login_required(login_url='/login/')
@permission_required('configuracion.eliminar_tservicio', raise_exception=True)
def eliminar_tservicio(request, TipoServicioID):
    servicio = get_object_or_404(TServicio, TipoServicioID=TipoServicioID)
    if request.method == 'POST':
        servicio.activo = False
        servicio.save()
        messages.success(request, 'Tipo de servicio desactivado exitosamente.')
        return redirect('configuracion:listar_tservicios') # Cambiado
    
    return render(request, 'configuracion/Tservicios/confirmar_eliminar_tservicio.html', {'servicio': servicio})


# Vistas para la gestión de Servicios (Actualizada)
@login_required(login_url='/login/')
@permission_required('configuracion.ver_servicios', raise_exception=True)
def listar_servicios(request):
    # Usamos select_related para traer las relaciones de un solo golpe (más rápido)
    servicios_list = Servicios.objects.select_related('NivelID', 'TipoServicioID').all().order_by('-FechaCreacion')

    # Obtener los niveles y tipos de servicio activos para los filtros
    niveles_activos = Nivel.objects.filter(Activo=True)
    tservicios_activos = TServicio.objects.filter(activo=True)
    
    # Obtener los años disponibles de los servicios
    anios_disponibles = Servicios.objects.values_list('Anio', flat=True).distinct().order_by('-Anio')

    # Lógica del buscador y filtros
    query = request.GET.get('q')
    nivel_id = request.GET.get('nivel')
    tservicio_id = request.GET.get('tservicio')
    anio = request.GET.get('anio')

    if query:
        # Busca en nombre del servicio O en el nombre del tipo de servicio
        servicios_list = servicios_list.filter(
            Q(NombreServicio__icontains=query) | 
            Q(TipoServicioID__TipoServicio__icontains=query)
        )
    
    if nivel_id:
        servicios_list = servicios_list.filter(NivelID=nivel_id)
        
    if tservicio_id:
        servicios_list = servicios_list.filter(TipoServicioID=tservicio_id)
    
    if anio:
        servicios_list = servicios_list.filter(Anio=anio)

    # ✅ Paginación
    paginator = Paginator(servicios_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'servicios': page_obj, 
        'niveles_activos': niveles_activos,
        'tservicios_activos': tservicios_activos,
        'anios_disponibles': anios_disponibles,
        'query_value': query, 
        'nivel_id_value': nivel_id, 
        'tservicio_id_value': tservicio_id,
        'anio_value': anio
    }
    return render(request, 'configuracion/servicios/listar_servicios.html', context)

# 1. DESCARGAR PLANTILLA CON COMBOS (Basado en tus tablas)
def descargar_plantilla_servicios(request):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Plantilla de Servicios"

    # Obtener datos usando el nombre exacto del campo: 'activo'
    niveles = [n.NombreNivel for n in Nivel.objects.filter(Activo=True)]
    tipos = [t.TipoServicio for t in TServicio.objects.filter(activo=True)]

    # Hoja oculta para los datos de los combos
    ws_data = wb.create_sheet(title="DataLists")
    ws_data.sheet_state = 'veryHidden'

    for i, nombre in enumerate(niveles, 1):
        ws_data.cell(row=i, column=1, value=nombre)
    for i, nombre in enumerate(tipos, 1):
        ws_data.cell(row=i, column=2, value=nombre)

    # Cabeceras
    headers = ['Nombre del Servicio', 'Precio', 'Nivel', 'Tipo de Servicio', 'Año']
    ws.append(headers)

    # Configurar validaciones (Combos)
    rango_niveles = f'=DataLists!$A$1:$A${len(niveles) if niveles else 1}'
    rango_tipos = f'=DataLists!$B$1:$B${len(tipos) if tipos else 1}'

    dv_nivel = DataValidation(type="list", formula1=rango_niveles, allow_blank=True)
    dv_tipo = DataValidation(type="list", formula1=rango_tipos, allow_blank=True)

    # Aplicar a las columnas C (Nivel) y D (Tipo)
    ws.add_data_validation(dv_nivel)
    dv_nivel.add('C2:C1000')
    ws.add_data_validation(dv_tipo)
    dv_tipo.add('D2:D1000')

    # Diseño básico
    for col in ['A', 'B', 'C', 'D', 'E']:
        ws.column_dimensions[col].width = 25

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=plantilla_servicios_shalom.xlsx'
    wb.save(response)
    return response

# 2. IMPORTAR DESDE EXCEL
def importar_servicios_excel(request):
    if request.method == 'POST':
        if 'archivo_excel' not in request.FILES:
            messages.error(request, "No se seleccionó ningún archivo.")
            return redirect('configuracion:listar_servicios')

        excel_file = request.FILES['archivo_excel']
        wb = openpyxl.load_workbook(excel_file, data_only=True)
        sheet = wb.active
        rows = list(sheet.iter_rows(min_row=2, values_only=True))
        
        servicios_creados = 0
        servicios_actualizados = 0
        ahora = timezone.now()

        for i, row in enumerate(rows, start=2):
            nombre = str(row[0]).strip() if row[0] else None
            precio = row[1]
            txt_nivel = str(row[2]).strip() if row[2] else None
            txt_tipo = str(row[3]).strip() if row[3] else None
            anio = row[4] or 2026

            if not nombre or nombre == "None" or precio is None:
                continue

            nivel_obj = Nivel.objects.filter(NombreNivel__iexact=txt_nivel).first()
            tipo_obj = TServicio.objects.filter(TipoServicio__iexact=txt_tipo).first()

            if nivel_obj and tipo_obj:
                # update_or_create evita el IntegrityError de duplicados
                obj, created = Servicios.objects.update_or_create(
                    NombreServicio=nombre,
                    NivelID=nivel_obj,
                    Anio=anio,
                    defaults={
                        'Precio': precio,
                        'TipoServicioID': tipo_obj,
                        'Activo': True,
                        'FechaCreacion': ahora if not Servicios.objects.filter(NombreServicio=nombre, NivelID=nivel_obj, Anio=anio).exists() else ahora
                    }
                )
                
                if created:
                    servicios_creados += 1
                else:
                    servicios_actualizados += 1
            else:
                messages.warning(request, f"Fila {i}: No se encontró Nivel '{txt_nivel}' o Tipo '{txt_tipo}'")

        # Mensajes de éxito informando qué pasó con los duplicados
        if servicios_creados > 0 or servicios_actualizados > 0:
            msg = f"Proceso terminado. Creados: {servicios_creados}. "
            if servicios_actualizados > 0:
                msg += f"Omitidos/Actualizados por ya existir: {servicios_actualizados}."
            messages.success(request, msg)

    return redirect('configuracion:listar_servicios')

@login_required(login_url='/login/')
@permission_required('configuracion.crear_servicios', raise_exception=True)
def crear_servicio(request):
    if request.method == 'POST':
        form = ServiciosForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Servicio creado exitosamente.')
            return redirect('configuracion:listar_servicios')
    else:
        form = ServiciosForm()
    
    return render(request, 'configuracion/servicios/crear_servicio.html', {'form': form})



@login_required(login_url='/login/')
@permission_required('configuracion.editar_servicios', raise_exception=True)
def editar_servicio(request, ServicioID):
    servicio = get_object_or_404(Servicios, ServicioID=ServicioID)
    if request.method == 'POST':
        form = ServiciosForm(request.POST, instance=servicio)
        if form.is_valid():
            form.save()
            messages.success(request, 'Servicio actualizado exitosamente.')
            return redirect('configuracion:listar_servicios')
    else:
        form = ServiciosForm(instance=servicio)
    
    return render(request, 'configuracion/servicios/editar_servicio.html', {'form': form, 'servicio': servicio})



@login_required(login_url='/login/')
@permission_required('configuracion.eliminar_servicios', raise_exception=True)
def eliminar_servicio(request, ServicioID):
    servicio = get_object_or_404(Servicios, ServicioID=ServicioID)
    if request.method == 'POST':
        servicio.Activo = False
        servicio.save()
        messages.success(request, 'Servicio desactivado exitosamente.')
        return redirect('configuracion:listar_servicios')
    
    return render(request, 'configuracion/servicios/confirmar_eliminar_servicio.html', {'servicio': servicio})


# Vistas para la gestión de Materias (con paginación e indicador)
@login_required(login_url='/login/')
@permission_required('configuracion.ver_materias', raise_exception=True)
def listar_materias(request):
    materias_base = Materias.objects.all().order_by('NombreMateria')
    niveles_activos = Nivel.objects.filter(Activo=True)

    # Filtros
    query = request.GET.get('q', '').strip()
    nivel_id = request.GET.get('nivel', '')

    if query:
        materias_base = materias_base.filter(NombreMateria__icontains=query)
    if nivel_id:
        materias_base = materias_base.filter(NivelID=nivel_id)

    # Paginación (15 registros por página)
    paginator = Paginator(materias_base, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'materias': page_obj,
        'niveles_activos': niveles_activos,
        'query_value': query,
        'nivel_id_value': nivel_id,
        'start_index': page_obj.start_index() if page_obj.object_list else 0,
        'total_materias': Materias.objects.count(),
        'materias_activas': Materias.objects.filter(activo=True).count(),
        'materias_inactivas': Materias.objects.filter(activo=False).count(),
    }
    return render(request, 'configuracion/materias/listar_materias.html', context)


@login_required(login_url='/login/')
@permission_required('configuracion.crear_materias', raise_exception=True)
def crear_materia(request):
    if request.method == 'POST':
        form = MateriasForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Materia creada exitosamente.')
            return redirect('configuracion:listar_materias')
        else:
            # Manejar errores de campo
            for field_name, error_list in form.errors.items():
                for error in error_list:
                    if field_name == '__all__':
                        # Errores que no están asociados a un campo específico (globales)
                        messages.error(request, error)
                    else:
                        # Errores asociados a un campo
                        messages.error(request, f"Error en el campo '{form.fields[field_name].label}': {error}")

    else:
        form = MateriasForm()
    
    return render(request, 'configuracion/materias/crear_materia.html', {'form': form})

@login_required(login_url='/login/')
@permission_required('configuracion.editar_materias', raise_exception=True)
def editar_materia(request, MateriaID):
    materia = get_object_or_404(Materias, MateriaID=MateriaID)
    if request.method == 'POST':
        form = MateriasForm(request.POST, instance=materia)
        if form.is_valid():
            form.save()
            messages.success(request, 'Materia actualizada exitosamente.')
            return redirect('configuracion:listar_materias')
    else:
        form = MateriasForm(instance=materia)
    
    return render(request, 'configuracion/materias/editar_materia.html', {'form': form, 'materia': materia})

@login_required(login_url='/login/')
@permission_required('configuracion.eliminar_materias', raise_exception=True)
def eliminar_materia(request, MateriaID):
    materia = get_object_or_404(Materias, MateriaID=MateriaID)
    if request.method == 'POST':
        materia.activo = False
        materia.save()
        messages.success(request, 'Materia desactivada exitosamente.')
        return redirect('configuracion:listar_materias')
    
    return render(request, 'configuracion/materias/confirmar_eliminar_materia.html', {'materia': materia})


# Vistas para la gestión de TipoMatricula
@login_required(login_url='/login/')
@permission_required('configuracion.ver_tipomatricula', raise_exception=True)
def listar_tipomatricula(request):
    tipos_matricula = TipoMatricula.objects.all().order_by('Descripcion')
    context = {'tipos_matricula': tipos_matricula}
    return render(request, 'configuracion/tipomatricula/listar_tipomatricula.html', context)

@login_required(login_url='/login/')
@permission_required('configuracion.crear_tipomatricula', raise_exception=True)
def crear_tipomatricula(request):
    if request.method == 'POST':
        form = TipoMatriculaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Tipo de matrícula creado exitosamente.')
            return redirect('configuracion:listar_tipomatricula')
    else:
        form = TipoMatriculaForm()
    
    return render(request, 'configuracion/tipomatricula/crear_tipomatricula.html', {'form': form})

@login_required(login_url='/login/')
@permission_required('configuracion.editar_tipomatricula', raise_exception=True)
def editar_tipomatricula(request, TipoMatriculaID):
    tipo_matricula = get_object_or_404(TipoMatricula, TipoMatriculaID=TipoMatriculaID)
    if request.method == 'POST':
        form = TipoMatriculaForm(request.POST, instance=tipo_matricula)
        if form.is_valid():
            form.save()
            messages.success(request, 'Tipo de matrícula actualizado exitosamente.')
            return redirect('configuracion:listar_tipomatricula')
    else:
        form = TipoMatriculaForm(instance=tipo_matricula)
    
    return render(request, 'configuracion/tipomatricula/editar_tipomatricula.html', {'form': form})

@login_required(login_url='/login/')
@permission_required('configuracion.eliminar_tipomatricula', raise_exception=True)
def eliminar_tipomatricula(request, TipoMatriculaID):
    tipo_matricula = get_object_or_404(TipoMatricula, TipoMatriculaID=TipoMatriculaID)
    if request.method == 'POST':
        tipo_matricula.activo = False
        tipo_matricula.save()
        messages.success(request, 'Tipo de matrícula desactivado exitosamente.')
        return redirect('configuracion:listar_tipomatricula')
    
    return render(request, 'configuracion/tipomatricula/confirmar_eliminar_tipomatricula.html', {'tipo_matricula': tipo_matricula})

# Vistas para la gestión de Turnos
@login_required(login_url='/login/')
@permission_required('configuracion.ver_turno', raise_exception=True)
def listar_turnos(request):
    turnos = Turno.objects.all().order_by('NombreTurno')
    context = {'turnos': turnos}
    return render(request, 'configuracion/turnos/listar_turnos.html', context)

@login_required(login_url='/login/')
@permission_required('configuracion.crear_turno', raise_exception=True)
def crear_turno(request):
    if request.method == 'POST':
        form = TurnoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Turno creado exitosamente.')
            return redirect('configuracion:listar_turnos')
    else:
        form = TurnoForm()
    
    return render(request, 'configuracion/turnos/crear_turno.html', {'form': form})

@login_required(login_url='/login/')
@permission_required('configuracion.editar_turno', raise_exception=True)
def editar_turno(request, TurnoID):
    turno = get_object_or_404(Turno, TurnoID=TurnoID)
    if request.method == 'POST':
        form = TurnoForm(request.POST, instance=turno)
        if form.is_valid():
            form.save()
            messages.success(request, 'Turno actualizado exitosamente.')
            return redirect('configuracion:listar_turnos')
    else:
        form = TurnoForm(instance=turno)
    
    return render(request, 'configuracion/turnos/editar_turno.html', {'form': form})

@login_required(login_url='/login/')
@permission_required('configuracion.eliminar_turno', raise_exception=True)
def eliminar_turno(request, TurnoID):
    turno = get_object_or_404(Turno, TurnoID=TurnoID)
    if request.method == 'POST':
        turno.activo = False
        turno.save()
        messages.success(request, 'Turno desactivado exitosamente.')
        return redirect('configuracion:listar_turnos')
    
    return render(request, 'configuracion/turnos/confirmar_eliminar_turno.html', {'turno': turno})

# Vistas para la gestión de Modalidades
@login_required(login_url='/login/')
@permission_required('configuracion.ver_modalidades', raise_exception=True)
def listar_modalidades(request):
    modalidades = Modalidades.objects.all().order_by('NombreModalidad')
    context = {'modalidades': modalidades}
    return render(request, 'configuracion/modalidades/listar_modalidades.html', context)

@login_required(login_url='/login/')
@permission_required('configuracion.crear_modalidades', raise_exception=True)
def crear_modalidad(request):
    if request.method == 'POST':
        form = ModalidadesForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Modalidad creada exitosamente.')
            return redirect('configuracion:listar_modalidades')
    else:
        form = ModalidadesForm()
    
    return render(request, 'configuracion/modalidades/crear_modalidad.html', {'form': form})

@login_required(login_url='/login/')
@permission_required('configuracion.editar_modalidades', raise_exception=True)
def editar_modalidad(request, ModalidadID):
    modalidad = get_object_or_404(Modalidades, ModalidadID=ModalidadID)
    if request.method == 'POST':
        form = ModalidadesForm(request.POST, instance=modalidad)
        if form.is_valid():
            form.save()
            messages.success(request, 'Modalidad actualizada exitosamente.')
            return redirect('configuracion:listar_modalidades')
    else:
        form = ModalidadesForm(instance=modalidad)
    
    return render(request, 'configuracion/modalidades/editar_modalidad.html', {'form': form})

@login_required(login_url='/login/')
@permission_required('configuracion.eliminar_modalidades', raise_exception=True)
def eliminar_modalidad(request, ModalidadID):
    modalidad = get_object_or_404(Modalidades, ModalidadID=ModalidadID)
    if request.method == 'POST':
        modalidad.activo = False
        modalidad.save()
        messages.success(request, 'Modalidad desactivada exitosamente.')
        return redirect('configuracion:listar_modalidades')
    
    return render(request, 'configuracion/modalidades/confirmar_eliminar_modalidad.html', {'modalidad': modalidad})

# Vistas para la gestión de Semestres
@login_required(login_url='/login/')
@permission_required('configuracion.ver_semestres', raise_exception=True)
def listar_semestres(request):
    semestres = Semestres.objects.all().order_by('NombreSemestre')
    context = {'semestres': semestres}
    return render(request, 'configuracion/semestres/listar_semestres.html', context)

@login_required(login_url='/login/')
@permission_required('configuracion.crear_semestres', raise_exception=True)
def crear_semestre(request):
    if request.method == 'POST':
        form = SemestresForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Semestre creado exitosamente.')
            return redirect('configuracion:listar_semestres')
    else:
        form = SemestresForm()
    
    return render(request, 'configuracion/semestres/crear_semestre.html', {'form': form})

@login_required(login_url='/login/')
@permission_required('configuracion.editar_semestres', raise_exception=True)
def editar_semestre(request, SemestreID):
    semestre = get_object_or_404(Semestres, SemestreID=SemestreID)
    if request.method == 'POST':
        form = SemestresForm(request.POST, instance=semestre)
        if form.is_valid():
            form.save()
            messages.success(request, 'Semestre actualizado exitosamente.')
            return redirect('configuracion:listar_semestres')
    else:
        form = SemestresForm(instance=semestre)
    
    return render(request, 'configuracion/semestres/editar_semestre.html', {'form': form})

@login_required(login_url='/login/')
@permission_required('configuracion.eliminar_semestres', raise_exception=True)
def eliminar_semestre(request, SemestreID):
    semestre = get_object_or_404(Semestres, SemestreID=SemestreID)
    if request.method == 'POST':
        semestre.activo = False
        semestre.save()
        messages.success(request, 'Semestre desactivado exitosamente.')
        return redirect('configuracion:listar_semestres')
    
    return render(request, 'configuracion/semestres/confirmar_eliminar_semestre.html', {'semestre': semestre})

# Vistas para la gestión de Cortes
@login_required(login_url='/login/')
@permission_required('configuracion.ver_cortes', raise_exception=True)
def listar_cortes(request):
    cortes = Cortes.objects.all().order_by('NombreCorte')
    context = {'cortes': cortes}
    return render(request, 'configuracion/cortes/listar_cortes.html', context)

@login_required(login_url='/login/')
@permission_required('configuracion.crear_cortes', raise_exception=True)
def crear_corte(request):
    if request.method == 'POST':
        form = CortesForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Corte creado exitosamente.')
            return redirect('configuracion:listar_cortes')
    else:
        form = CortesForm()
    
    return render(request, 'configuracion/cortes/crear_corte.html', {'form': form})

@login_required(login_url='/login/')
@permission_required('configuracion.editar_cortes', raise_exception=True)
def editar_corte(request, CorteID):
    corte = get_object_or_404(Cortes, CorteID=CorteID)
    if request.method == 'POST':
        form = CortesForm(request.POST, instance=corte)
        if form.is_valid():
            form.save()
            messages.success(request, 'Corte actualizado exitosamente.')
            return redirect('configuracion:listar_cortes')
    else:
        form = CortesForm(instance=corte)
    
    return render(request, 'configuracion/cortes/editar_corte.html', {'form': form})

@login_required(login_url='/login/')
@permission_required('configuracion.eliminar_cortes', raise_exception=True)
def eliminar_corte(request, CorteID):
    corte = get_object_or_404(Cortes, CorteID=CorteID)
    if request.method == 'POST':
        corte.activo = False
        corte.save()
        messages.success(request, 'Corte desactivado exitosamente.')
        return redirect('configuracion:listar_cortes')
    
    return render(request, 'configuracion/cortes/confirmar_eliminar_corte.html', {'corte': corte})

# Vistas para la gestión de Tipos de Cambio
@login_required(login_url='/login/')
@permission_required('configuracion.ver_tiposcambio', raise_exception=True)
def listar_tipos_cambio(request):
    tipos_cambio = TiposCambio.objects.all().order_by('-FechaRegistro')
    context = {'tipos_cambio': tipos_cambio}
    return render(request, 'configuracion/tiposcambio/listar_tipos_cambio.html', context)

@login_required(login_url='/login/')
@permission_required('configuracion.crear_tiposcambio', raise_exception=True)
def crear_tipo_cambio(request):
    if request.method == 'POST':
        form = TiposCambioForm(request.POST)
        if form.is_valid():
            tipo_cambio = form.save(commit=False)
            tipo_cambio.UsuarioID = request.user
            tipo_cambio.save()
            messages.success(request, 'Tipo de cambio creado exitosamente.')
            return redirect('configuracion:listar_tipos_cambio')
    else:
        form = TiposCambioForm()
    
    return render(request, 'configuracion/tiposcambio/crear_tipo_cambio.html', {'form': form})

@login_required(login_url='/login/')
@permission_required('configuracion.editar_tiposcambio', raise_exception=True)
def editar_tipo_cambio(request, TipoCambioID):
    tipo_cambio = get_object_or_404(TiposCambio, TipoCambioID=TipoCambioID)
    if request.method == 'POST':
        form = TiposCambioForm(request.POST, instance=tipo_cambio)
        if form.is_valid():
            form.save()
            messages.success(request, 'Tipo de cambio actualizado exitosamente.')
            return redirect('configuracion:listar_tipos_cambio')
    else:
        form = TiposCambioForm(instance=tipo_cambio)
    
    return render(request, 'configuracion/tiposcambio/editar_tipo_cambio.html', {'form': form})
    
@login_required(login_url='/login/')
@permission_required('configuracion.eliminar_tiposcambio', raise_exception=True)
def eliminar_tipo_cambio(request, TipoCambioID):
    tipo_cambio = get_object_or_404(TiposCambio, TipoCambioID=TipoCambioID)
    # Aquí puedes implementar una lógica de desactivación si fuera necesario, pero la tabla no tiene un campo 'activo'
    # Así que la eliminación será directa o puedes decidir no ofrecer esta funcionalidad.
    if request.method == 'POST':
        tipo_cambio.delete()
        messages.success(request, 'Tipo de cambio eliminado exitosamente.')
        return redirect('configuracion:listar_tipos_cambio')
    
    return render(request, 'configuracion/tiposcambio/confirmar_eliminar_tipo_cambio.html', {'tipo_cambio': tipo_cambio})


def licencia_vencida_view(request):
    """Pantalla que se muestra cuando el sistema está bloqueado por licencia caducada."""
    licencia = Licencia.obtener_licencia_actual()
    
    return render(request, 'configuracion/licencia_vencida.html', {
        'licencia': licencia
    })
    
    
@login_required(login_url='/login/')
@permission_required('configuracion.ver_licencia', raise_exception=True) 
def administrar_licencia_view(request):
    licencia = Licencia.obtener_licencia_actual()

    if request.method == 'POST':
        # Al enviar el formulario, lo llenamos con los datos del POST y la instancia actual
        form = LicenciaAdminForm(request.POST, instance=licencia)
        if form.is_valid():
            form.save()
            # La verificación de validez de la licencia se ejecuta después del save
            if not licencia.es_valida():
                 messages.warning(request, "Licencia actualizada, pero ¡aún está vencida! Revise la fecha.")
            else:
                 messages.success(request, "¡Licencia actualizada exitosamente!")
            
            return redirect('configuracion:administrar_licencia')
    else:
        # En el primer acceso (GET), llenamos el formulario con los datos de la licencia actual
        form = LicenciaAdminForm(instance=licencia)

    context = {
        'licencia': licencia,
        'titulo': 'Administración de Licencia',
        'is_licencia_valida': licencia.es_valida(),
        'form': form, # <-- Añadimos el formulario al contexto
    }
    
    return render(request, 'configuracion/administrar_licencia.html', context)

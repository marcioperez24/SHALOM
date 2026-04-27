from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import Group, Permission, User
from django.contrib.auth.decorators import permission_required
from .forms import GroupPermissionsForm
from django import forms

# Formulario para asignar usuarios a un grupo
class AssignUsersForm(forms.Form):
    users = forms.ModelMultipleChoiceField(
        queryset=User.objects.all().order_by('username'),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Seleccionar Usuarios"
    )

@permission_required('auth.ver_grupo', raise_exception=True)
def lista_grupos_view(request):
    """
    Vista para mostrar la lista de todos los grupos existentes.
    """
    groups = Group.objects.all()
    return render(request, 'gestion_permisos/lista_grupos.html', {'groups': groups})

@permission_required('auth.crear_grupo', raise_exception=True)
def crear_grupo_view(request):
    if request.method == 'POST':
        form = GroupPermissionsForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('lista_grupos')
    else:
        form = GroupPermissionsForm()
    
    permisos_agrupados = {}
    
    # Iteramos sobre las opciones del campo permissions
    for choice in form.fields['permissions'].choices:
        # IMPORTANTE: Extraemos el ID correctamente usando .value para evitar el TypeError
        perm_id = choice[0].value if hasattr(choice[0], 'value') else choice[0]
        
        try:
            permiso_obj = Permission.objects.get(id=perm_id)
            # Agrupamos por el nombre legible del tipo de contenido (Módulo)
            modulo = permiso_obj.content_type.name.upper()
            
            if modulo not in permisos_agrupados:
                permisos_agrupados[modulo] = []
            
            # Si el campo 'name' está vacío o es '-', usamos el codename para que no salga vacío en la UI
            nombre_mostrar = permiso_obj.name
            if not nombre_mostrar or nombre_mostrar == '-':
                nombre_mostrar = permiso_obj.codename.replace('_', ' ').title()

            permisos_agrupados[modulo].append({
                'id': perm_id,
                'name': nombre_mostrar,
                'codename': permiso_obj.codename
            })
        except Permission.DoesNotExist:
            continue

    context = {
        'form': form,
        'permisos_agrupados': permisos_agrupados
    }
    
    return render(request, 'gestion_permisos/crear_grupo.html', context)

@permission_required('auth.editar_grupo', raise_exception=True)
def editar_grupo_view(request, group_id): # <-- CAMBIADO A group_id para coincidir con URLS
    grupo = get_object_or_404(Group, id=group_id)
    
    if request.method == 'POST':
        form = GroupPermissionsForm(request.POST, instance=grupo)
        if form.is_valid():
            form.save()
            return redirect('lista_grupos')
    else:
        form = GroupPermissionsForm(instance=grupo)
    
    # --- LÓGICA DE AGRUPACIÓN ---
    permisos_agrupados = {}
    permisos_actuales_ids = list(grupo.permissions.values_list('id', flat=True))

    for choice in form.fields['permissions'].choices:
        # Extracción segura del ID para evitar el TypeError de tus capturas
        val = choice[0]
        perm_id = val.value if hasattr(val, 'value') else val
        
        try:
            permiso_obj = Permission.objects.get(id=perm_id)
            modulo = permiso_obj.content_type.name.upper()
            
            if modulo not in permisos_agrupados:
                permisos_agrupados[modulo] = []
            
            # Formatear el nombre si viene vacío o con guion (visto en tu base de datos)
            nombre = permiso_obj.name
            if not nombre or nombre == '-':
                nombre = permiso_obj.codename.replace('_', ' ').title()

            permisos_agrupados[modulo].append({
                'id': perm_id,
                'name': nombre,
                'codename': permiso_obj.codename,
                'checked': perm_id in permisos_actuales_ids
            })
        except Permission.DoesNotExist:
            continue

    return render(request, 'gestion_permisos/editar_grupo.html', {
        'form': form,
        'grupo': grupo,
        'permisos_agrupados': permisos_agrupados
    })

@permission_required('auth.asignar_grupo', raise_exception=True)
def asignar_usuario_a_grupo_view(request, group_id):
    """
    Vista para asignar usuarios a un grupo específico.
    """
    group = get_object_or_404(Group, pk=group_id)
    if request.method == 'POST':
        form = AssignUsersForm(request.POST)
        if form.is_valid():
            selected_users = form.cleaned_data['users']
            group.user_set.set(selected_users)
            return redirect('lista_grupos')
    else:
        # Preseleccionar los usuarios que ya están en el grupo
        current_users = group.user_set.all()
        form = AssignUsersForm(initial={'users': current_users})

    context = {
        'form': form,
        'group_name': group.name,
    }
    return render(request, 'gestion_permisos/asignar_usuarios_a_grupo.html', context)

@permission_required('auth.eliminar_grupo', raise_exception=True)
def eliminar_grupo_view(request, group_id):
    """
    Vista para eliminar un grupo.
    """
    group = get_object_or_404(Group, pk=group_id)
    if request.method == 'POST':
        group.delete()
        return redirect('lista_grupos')
    # Si la petición no es POST, redirige o muestra una página de confirmación
    return render(request, 'gestion_permisos/confirmar_eliminar.html', {'group': group})

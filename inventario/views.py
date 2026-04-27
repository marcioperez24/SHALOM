from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .models import Producto, VarianteProducto, CategoriaProducto, Proveedor, Compra, DetalleCompra
from .forms import ProductoForm
import json

@login_required
def lista_productos(request):
    productos = Producto.objects.all().order_by('-FechaRegistro')
    categorias = CategoriaProducto.objects.all()
    return render(request, 'inventario/lista_productos.html', {
        'productos': productos,
        'categorias': categorias,
        'titulo': 'Inventario de Productos'
    })

@login_required
def agregar_producto(request):
    categorias = CategoriaProducto.objects.all()
    if request.method == 'POST':
        # Almacenamiento custom para soportar Variantes
        form = ProductoForm(request.POST, request.FILES)
        if form.is_valid():
            producto = form.save()
            
            tiene_variantes = request.POST.get('TieneVariantes') == 'on' or request.POST.get('TieneVariantes') == 'True'
            producto.TieneVariantes = tiene_variantes
            producto.save()

            if tiene_variantes:
                # Leer variantes de arrays del form e.g., talla[], color[], stock[]
                tallas = request.POST.getlist('talla[]')
                colores = request.POST.getlist('color[]')
                stocks = request.POST.getlist('stock[]')
                
                for t, c, s in zip(tallas, colores, stocks):
                    stock_val = int(s) if s else 0
                    if t or c or stock_val >= 0:
                        VarianteProducto.objects.create(
                            Producto=producto,
                            Talla=t,
                            Color=c,
                            StockActual=stock_val
                        )
            else:
                # Si no tiene variantes, crear variante por defecto
                stock_unico = int(request.POST.get('stock_unico', 0))
                VarianteProducto.objects.create(
                    Producto=producto,
                    Talla=None,
                    Color=None,
                    StockActual=stock_unico
                )

            messages.success(request, 'Producto agregado exitosamente.')
            return redirect('inventario:lista_productos')
        else:
            messages.error(request, 'Error al guardar el producto. Verifica los campos.')

    else:
        form = ProductoForm()
    
    return render(request, 'inventario/form_producto.html', {
        'form': form,
        'categorias': categorias,
        'titulo': 'Agregar Nuevo Producto'
    })

@login_required
def editar_producto(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    categorias = CategoriaProducto.objects.all()
    variantes = producto.variantes.all()

    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES, instance=producto)
        if form.is_valid():
            prod = form.save()
            
            # Update stock for default if not variant
            if not prod.TieneVariantes:
                stock_unico = int(request.POST.get('stock_unico', 0))
                v = prod.variantes.first()
                if v:
                    v.StockActual = stock_unico
                    v.save()
            else:
                # Actualizar stocks de variantes
                for k, v in request.POST.items():
                    if k.startswith('var_stock_'):
                        var_id = k.split('_')[-1]
                        variante = VarianteProducto.objects.get(VarianteID=var_id)
                        variante.StockActual = int(v)
                        variante.save()

            messages.success(request, 'Producto actualizado exitosamente.')
            return redirect('inventario:lista_productos')
    else:
        form = ProductoForm(instance=producto)
        
    return render(request, 'inventario/form_producto.html', {
        'form': form,
        'producto': producto,
        'categorias': categorias,
        'variantes': variantes,
        'titulo': 'Editar Producto'
    })

@login_required
def eliminar_producto(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    if request.method == 'POST':
        producto.delete()
        messages.success(request, 'Producto eliminado exitosamente.')
        return redirect('inventario:lista_productos')
    
    return render(request, 'inventario/eliminar_producto.html', {
        'producto': producto,
        'titulo': 'Eliminar Producto'
    })

@login_required
def gestionar_categorias(request):
    categorias = CategoriaProducto.objects.all()
    
    if request.method == 'POST':
        if 'crear' in request.POST:
            nombre = request.POST.get('nombre')
            desc = request.POST.get('descripcion')
            if nombre:
                CategoriaProducto.objects.create(Nombre=nombre, Descripcion=desc)
                messages.success(request, 'Categoría creada con éxito.')
            return redirect('inventario:gestionar_categorias')
        
        elif 'eliminar' in request.POST:
            cat_id = request.POST.get('cat_id')
            cat = get_object_or_404(CategoriaProducto, pk=cat_id)
            cat.delete()
            messages.success(request, 'Categoría eliminada.')
            return redirect('inventario:gestionar_categorias')

    return render(request, 'inventario/gestionar_categorias.html', {
        'categorias': categorias,
        'titulo': 'Manejo de Categorías'
    })

from django.db import transaction

@login_required
def lista_compras_view(request):
    compras = Compra.objects.select_related('Proveedor').order_by('-FechaCompra')
    return render(request, 'inventario/lista_compras.html', {
        'compras': compras,
        'titulo': 'Historial de Compras'
    })

@login_required
def crear_compra_view(request):
    if request.method == 'POST':
        try:
            proveedor_id = request.POST.get('proveedor')
            fecha = request.POST.get('fecha')
            no_factura = request.POST.get('no_factura')
            observaciones = request.POST.get('observaciones')
            
            # Los items vienen en JSON (variante_id, cantidad, costo)
            detalles_json = request.POST.get('compras_json', '[]')
            detalles = json.loads(detalles_json)
            
            if not detalles:
                return JsonResponse({'success': False, 'error': 'No hay items en la compra.'})
            
            proveedor = Proveedor.objects.get(pk=proveedor_id) if proveedor_id else None
            
            with transaction.atomic():
                total_compra = 0
                compra = Compra.objects.create(
                    Proveedor=proveedor,
                    NoFactura=no_factura,
                    FechaCompra=fecha,
                    Observaciones=observaciones,
                    Estado='Completada'
                )
                
                for item in detalles:
                    variante = VarianteProducto.objects.get(pk=item['variante_id'])
                    cant = int(item['cantidad'])
                    costo = float(item['costo'])
                    subtotal = cant * costo
                    
                    DetalleCompra.objects.create(
                        Compra=compra,
                        VarianteProducto=variante,
                        Cantidad=cant,
                        PrecioCosto=costo,
                        Subtotal=subtotal
                    )
                    
                    # Actualizar Inventario sumando las unidades
                    variante.StockActual += cant
                    variante.save()
                    
                    total_compra += subtotal
                    
                compra.Total = total_compra
                compra.save()
                
                return JsonResponse({'success': True, 'message': 'Compra registrada exitosamente y stock actualizado correctamente.'})
                
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    proveedores = Proveedor.objects.filter(Activo=True)
    variantes = VarianteProducto.objects.filter(Activo=True).select_related('Producto')
    return render(request, 'inventario/nueva_compra.html', {
        'proveedores': proveedores,
        'variantes': variantes,
        'titulo': 'Registrar Nueva Compra'
    })

@login_required
def api_agregar_proveedor(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            p = Proveedor.objects.create(
                Nombre=data.get('nombre'),
                Telefono=data.get('telefono', ''),
                Contacto=data.get('contacto', ''),
                Direccion=data.get('direccion', '')
            )
            return JsonResponse({'success': True, 'id': p.ProveedorID, 'nombre': p.Nombre})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Método HTTP inválido.'})

@login_required
def anular_compra_view(request, compra_id):
    if request.method == 'POST':
        try:
            with transaction.atomic():
                compra = Compra.objects.get(pk=compra_id)
                if compra.Estado == 'Anulada':
                    return JsonResponse({'success': False, 'error': 'La compra ya había sido anulada previamente.'})
                
                # Revertir stock restando lo ingresado en esta compra
                for det in compra.detalles.all():
                    variante = det.VarianteProducto
                    # Restamos las existencias
                    variante.StockActual -= det.Cantidad
                    if variante.StockActual < 0:
                        variante.StockActual = 0 # Prevenir que quede num. negativo si ya se habían vendido
                    variante.save()
                
                compra.Estado = 'Anulada'
                compra.save()
                return JsonResponse({'success': True, 'message': 'La compra ha sido anulada con éxito y el inventario ha sido devuelto a su estado natural.'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Método no permitido.'})

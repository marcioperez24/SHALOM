#facturacion/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from .models import Facturas, DetalleFactura, Recibo, Estudiantes_Nueva, Arqueos, DetallesArqueo
from configuracion.models import Seccion, Nivel
from Matricula.models import Matricula, Estudiantes_Nueva
from configuracion.models import Servicios, TiposCambio, TServicio
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import permission_required
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.utils import timezone
from datetime import date
from django.db.models import Sum, Q, F, Count, Max
from django.utils.dateparse import parse_date
from decimal import Decimal, InvalidOperation
import json
from datetime import datetime, timedelta
from django.shortcuts import render
from django.db.models import F, Sum, Value,  CharField, DecimalField, OuterRef, Subquery  
from django.db.models.functions import Coalesce, Substr
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .models import Facturas
from configuracion.models import Servicios, TServicio, Nivel as Niveles # Renombramos Nivel a Niveles para no cambiar el código
from Matricula.models import Matricula
from inventario.models import Producto, VarianteProducto
import logging
import pandas as pd
from django.http import HttpResponse
from decimal import Decimal
from .models import Matricula, DetalleFactura
from django.core.paginator import Paginator
import openpyxl
from openpyxl.utils import get_column_letter
from openpyxl.styles import Font, Alignment, Border, Side
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

@login_required
@permission_required('facturacion.inicio_facturas', raise_exception=True)
def facturacion_home_view(request):
    """
    Vista principal para el dashboard de facturación.
    """
    context = {
        'titulo': 'Dashboard de Facturación'
    }
    return render(request, 'facturacion/facturacion_home.html', context)

@login_required
def lista_facturas_view(request):
    """
    Muestra la lista de todas las facturas con su saldo y el estado del arqueo activo, con paginación y búsqueda en el servidor.
    """
    # Inicialmente obtiene todas las facturas ordenadas por fecha descendente
    facturas_list = Facturas.objects.all().order_by('-Fecha','-FacturaID')

    # --- Lógica de Búsqueda ---
    query = request.GET.get('q')
    if query:
        # Filtra las facturas por múltiples campos (Estudiante, FacturaID, Estado)
        # __icontains permite buscar ignorando mayúsculas/minúsculas y buscando subcadenas
        facturas_list = facturas_list.filter(
            Q(EstudianteID__NombreCompleto__icontains=query) |
            Q(FacturaID__icontains=query) |
            Q(Estado__icontains=query)
        )

    # --- Lógica de Paginación ---
    paginator = Paginator(facturas_list, 15)  # Mostrar 15 facturas por página
    page_number = request.GET.get('page')
    facturas_con_saldo = paginator.get_page(page_number)

    # Verifica si hay un arqueo activo para el usuario en la fecha actual.
    arqueo_activo = Arqueos.objects.filter(UsuarioID=request.user, Activa=True, Fecha=timezone.now().date()).first()
    
    context = {
        'titulo': 'Lista de Facturas',
        'facturas': facturas_con_saldo,
        'arqueo_activo': arqueo_activo,
        'query': query, # Pasamos la búsqueda actual al template para mantenerla en el campo
    }
    return render(request, 'facturacion/lista_facturas.html', context)


@csrf_exempt
@login_required
@permission_required('facturacion.crear_facturas', raise_exception=True)
def crear_factura_view(request):
      
    """
    Vista para generar y guardar una nueva factura. También registra los datos
    en las tablas de Arqueos y DetallesArqueo, vinculando cada servicio.
    """
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # 1. Obtener los datos del formulario POST
                estudiante_id = request.POST.get('estudiante_id')
                fecha_str = request.POST.get('fecha')
                moneda = request.POST.get('moneda')
                servicios_json = request.POST.getlist('servicios_factura')
                
                if not estudiante_id or not fecha_str or not servicios_json:
                    return JsonResponse({'error': 'Faltan datos de la factura.'}, status=400)

                # 2. Obtener los objetos de la base de datos
                estudiante = get_object_or_404(Estudiantes_Nueva, EstudianteID=estudiante_id)
                matricula = Matricula.objects.filter(EstudianteID=estudiante, activo=True).first()
                tipo_cambio_actual = TiposCambio.objects.order_by('-FechaRegistro').first()

                if moneda == 'USD' and not tipo_cambio_actual:
                    return JsonResponse({'error': 'No se encontró un tipo de cambio para esta fecha.'}, status=400)
                
                # 3. Procesar los servicios y calcular los totales
                total_factura_bruta = Decimal(0)
                total_factura_neta = Decimal(0)
                total_a_pagar_inicialmente = Decimal(0)
                total_descuento_general = Decimal(0)
                detalles_factura_list = []

                for servicio_data in servicios_json:
                    try:
                        detalle = json.loads(servicio_data)
                        servicio_id = detalle['id']
                        cantidad = int(detalle.get('cantidad', 1))
                        precio_str = detalle.get('precio')
                        descuento_porcentaje_str = detalle.get('descuento', '0')
                        
                        tipo_item = detalle.get('tipo', 'servicio')
                        es_por_cuotas = detalle.get('pagar_cuotas', False)
                        monto_cuota_inicial_str = detalle.get('monto_cuota', '0')

                        if precio_str is None:
                            raise ValueError(f"Precio del ítem {servicio_id} no encontrado.")
                        
                        precio = Decimal(precio_str)
                        descuento_porcentaje = Decimal(descuento_porcentaje_str)
                        
                        subtotal = precio * cantidad
                        descuento_monto = subtotal * (descuento_porcentaje / Decimal(100))
                        total_servicio_con_descuento = subtotal - descuento_monto
                        
                        total_factura_bruta += subtotal
                        total_factura_neta += total_servicio_con_descuento
                        total_descuento_general += descuento_monto

                        if es_por_cuotas:
                            monto_cuota_inicial = Decimal(monto_cuota_inicial_str)
                            monto_inicial_a_pagar_servicio = monto_cuota_inicial
                            saldo_pendiente_servicio = total_servicio_con_descuento - monto_cuota_inicial
                        else:
                            monto_inicial_a_pagar_servicio = total_servicio_con_descuento
                            saldo_pendiente_servicio = Decimal(0)
                            
                        total_a_pagar_inicialmente += monto_inicial_a_pagar_servicio
                        
                        # Verify stock and subtract if product
                        producto_obj = None
                        if tipo_item == 'producto':
                            producto_obj = get_object_or_404(VarianteProducto, VarianteID=servicio_id)
                            if producto_obj.StockActual < cantidad:
                                return JsonResponse({'error': f'Stock insuficiente para el producto {producto_obj.Producto.Nombre}.'}, status=400)
                            producto_obj.StockActual -= cantidad
                            producto_obj.save()
                        
                        detalles_factura_list.append({
                            'id': servicio_id,
                            'tipo': tipo_item,
                            'cantidad': cantidad,
                            'precio': precio,
                            'descuento_porcentaje': descuento_porcentaje,
                            'subtotal': subtotal,
                            'descuento_monto': descuento_monto,
                            'total_servicio_con_descuento': total_servicio_con_descuento,
                            'es_por_cuotas': es_por_cuotas,
                            'monto_inicial_a_pagar_servicio': monto_inicial_a_pagar_servicio,
                            'saldo_pendiente_servicio': saldo_pendiente_servicio,
                            'producto_obj': producto_obj,
                        })

                    except (ValueError, TypeError, json.JSONDecodeError, InvalidOperation) as e:
                        print(f"Error al procesar el servicio del JSON: {e}")
                        return JsonResponse({'error': f'Datos de servicio inválidos: {e}.'}, status=400)
                
                if total_factura_bruta <= Decimal(0):
                    return JsonResponse({'error': 'El total de la factura debe ser mayor a cero.'}, status=400)
                
                saldo_inicial_factura = total_factura_neta - total_a_pagar_inicialmente

                # 4. Crear la factura principal
                factura = Facturas.objects.create(
                    Fecha=fecha_str,
                    Total=total_factura_bruta,
                    MontoPagado=total_a_pagar_inicialmente,
                    Saldo=saldo_inicial_factura,
                    Moneda=moneda,
                    TipoCambioID=tipo_cambio_actual,
                    UsuarioID=request.user if request.user.is_authenticated else None,
                    FechaRegistro=timezone.now(),
                    EsPorCuotas=any(d['es_por_cuotas'] for d in detalles_factura_list),
                    Activa=True,
                    Estado='Pagado' if saldo_inicial_factura <= Decimal(0) else 'Pendiente',
                    MatriculaID=matricula,
                    EstudianteID=estudiante,
                    Descuento=total_descuento_general,
                    DescuentoPorcentaje=0
                )

                # 5. Crear el primer recibo con el monto del pago inicial
                recibo = None
                if total_a_pagar_inicialmente > Decimal(0):
                    recibo_estado = 'Pagado' if factura.Saldo <= Decimal(0) else 'Pendiente'
                    recibo = Recibo.objects.create(
                        FacturaID=factura,
                        FechaPago=fecha_str,
                        MontoPagado=total_a_pagar_inicialmente,
                        Saldo=factura.Saldo,
                        Total=total_factura_neta,
                        FechaRegistro=timezone.now(),
                        Estado=recibo_estado,
                    )
                    
                    # 6. Obtener o crear el arqueo activo del usuario
                    arqueo_activo, created = Arqueos.objects.get_or_create(
                        UsuarioID=request.user,
                        Fecha=timezone.now().date(),
                        Activa=True,
                        defaults={
                            'FechaRegistro': timezone.now(),
                            'MontoDeclarado_Cordobas': Decimal('0.00'),
                            'MontoDeclarado_USD': Decimal('0.00'),
                            'MontoCalculado_Cordobas': Decimal('0.00'),
                            'MontoCalculado_USD': Decimal('0.00'),
                            'Diferencia_Cordobas': Decimal('0.00'),
                            'Diferencia_USD': Decimal('0.00'),
                            'Hora': timezone.now().time(),
                            'Observaciones': 'Arqueo automático por transacción.'
                        }
                    )
                    
                    # 7. Crear los detalles de la factura y los detalles del arqueo por cada servicio
                    for detalle_temp in detalles_factura_list:
                        servicio = None
                        producto = None
                        if detalle_temp['tipo'] == 'producto':
                            producto = detalle_temp['producto_obj']
                        else:
                            servicio = get_object_or_404(Servicios, ServicioID=detalle_temp['id'])
                            
                        monto_pagado_servicio = detalle_temp['monto_inicial_a_pagar_servicio']
                        
                        # Crear el DetalleFactura
                        DetalleFactura.objects.create(
                            FacturaID=factura,
                            ServicioID=servicio,
                            VarianteProductoID=producto,
                            Cantidad=detalle_temp['cantidad'],
                            PrecioUnitario=detalle_temp['precio'],
                            Subtotal=detalle_temp['subtotal'],
                            FechaRegistro=timezone.now(),
                            Activa=True,
                            Saldo=detalle_temp['saldo_pendiente_servicio'],
                            MontoPagado=monto_pagado_servicio,
                            Descuento=detalle_temp['descuento_monto'],
                            DescuentoPorcentaje=detalle_temp['descuento_porcentaje'],
                            ReciboID=recibo,
                        )

                        # Crear el DetallesArqueo correspondiente a este servicio
                        monto_cordobas = Decimal('0.00')
                        monto_usd = Decimal('0.00')

                        if factura.Moneda == 'CS':
                            monto_cordobas = monto_pagado_servicio
                            arqueo_activo.MontoCalculado_Cordobas += monto_pagado_servicio
                        elif factura.Moneda == 'USD':
                            monto_usd = monto_pagado_servicio
                            arqueo_activo.MontoCalculado_USD += monto_pagado_servicio

                        DetallesArqueo.objects.create(
                            ArqueoID=arqueo_activo,
                            ReciboID=recibo,
                            ServicioID=servicio,
                            VarianteProductoID=producto,
                            FacturaID=factura.FacturaID,
                            Monto=monto_pagado_servicio,
                            Anulada=False,
                            FechaRegistro=timezone.now(),
                            Activa=True,
                            MontoCordobas=monto_cordobas,
                            MontoUSD=monto_usd,
                            TipoPago="Efectivo",
                            Fecha=timezone.now().date(),
                        )
                    # Guardar la actualización del Arqueo después de haber sumado todos los servicios
                    arqueo_activo.save()

                else:
                    # Si no hay recibo (pago de $0), crear solo los detalles de la factura
                    for detalle_temp in detalles_factura_list:
                        servicio = None
                        producto = None
                        if detalle_temp['tipo'] == 'producto':
                            producto = detalle_temp['producto_obj']
                        else:
                            servicio = get_object_or_404(Servicios, ServicioID=detalle_temp['id'])
                            
                        DetalleFactura.objects.create(
                            FacturaID=factura,
                            ServicioID=servicio,
                            ProductoID=producto,
                            Cantidad=detalle_temp['cantidad'],
                            PrecioUnitario=detalle_temp['precio'],
                            Subtotal=detalle_temp['subtotal'],
                            FechaRegistro=timezone.now(),
                            Activa=True,
                            Saldo=detalle_temp['saldo_pendiente_servicio'],
                            MontoPagado=detalle_temp['monto_inicial_a_pagar_servicio'],
                            Descuento=detalle_temp['descuento_monto'],
                            DescuentoPorcentaje=detalle_temp['descuento_porcentaje'],
                            ReciboID=None,
                        )
            
                if recibo:
                    return JsonResponse({'success': True, 'factura_id': factura.FacturaID, 'recibo_id': recibo.ReciboID})
                else:
                    return JsonResponse({'success': True, 'factura_id': factura.FacturaID, 'recibo_id': None})
            
        except Exception as e:
            print(f"Error inesperado al crear la factura: {e}")
            return JsonResponse({'error': 'Ocurrió un error inesperado al procesar la factura.'}, status=500)
    
    # Lógica para la solicitud GET (renderizar el formulario)
    estudiantes = Estudiantes_Nueva.objects.all().order_by('NombreCompleto')
    anio_actual = timezone.now().date().year
    servicios = Servicios.objects.filter(Activo=True, Anio=anio_actual).order_by('NombreServicio')

    context = {
        'titulo': 'Generar Factura',
        'estudiantes': estudiantes,
        'servicios': servicios,
        'fecha_hoy': timezone.now().date(),
    }
    
    return render(request, 'facturacion/crear_factura.html', context)

@login_required
def generar_recibo_view(request, factura_id):
    """
    Vista para mostrar la página de generación de recibos y procesar el pago.
    """
    try:
        factura = get_object_or_404(Facturas, FacturaID=factura_id)
        
        # Obtenemos los recibos existentes de la factura
        recibos_existentes = Recibo.objects.filter(FacturaID=factura).order_by('FechaPago') 
        
        total_pagado_factura = recibos_existentes.aggregate(Sum('MontoPagado'))['MontoPagado__sum'] or Decimal(0)
        
        # Detalles de la factura con saldo pendiente (para mostrar en la vista GET)
        detalles_con_saldo_pendiente = DetalleFactura.objects.filter(
            FacturaID=factura,
            Saldo__gt=0
        )

        # ------------------ Lógica para el procesamiento POST ------------------
        if request.method == 'POST':
            monto_pagado_recibo = Decimal(request.POST.get('monto_a_pagar', '0').replace(',', ''))
            fecha_pago = request.POST.get('fecha_pago')

            saldo_pendiente_factura = factura.Total - total_pagado_factura

            if monto_pagado_recibo > 0 and monto_pagado_recibo <= saldo_pendiente_factura:
                with transaction.atomic():
                    # 1. Crear el nuevo recibo
                    recibo = Recibo.objects.create(
                        FacturaID=factura,
                        FechaPago=fecha_pago,
                        MontoPagado=monto_pagado_recibo,
                        Saldo=saldo_pendiente_factura - monto_pagado_recibo,
                        Total=factura.Total,
                        FechaRegistro=timezone.now(),
                        Estado='Pagado',
                    )
                    
                    # 2. Distribuir el monto del pago entre los servicios con saldo pendiente
                    monto_restante_a_pagar = monto_pagado_recibo
                    for detalle in detalles_con_saldo_pendiente:
                        if monto_restante_a_pagar > 0:
                            monto_a_aplicar_a_este_detalle = min(detalle.Saldo, monto_restante_a_pagar)
                            
                            # Actualizar el saldo del detalle de la factura original
                            detalle.Saldo -= monto_a_aplicar_a_este_detalle
                            
                            # Actualizar el monto pagado en el detalle de la factura original
                            detalle.MontoPagado += monto_a_aplicar_a_este_detalle
                            detalle.save()

                            # Recuperar el servicio original para obtener el precio
                            servicio_original = Servicios.objects.get(ServicioID=detalle.ServicioID_id)

                            # 3. Crear un registro en DetalleFactura para este pago específico en el recibo
                            # Se usa el precio original del servicio y solo se registra el monto del pago
                            DetalleFactura.objects.create(
                                FacturaID=factura,
                                ServicioID=detalle.ServicioID,
                                Cantidad=detalle.Cantidad, # Usa la cantidad original del detalle
                                PrecioUnitario=detalle.PrecioUnitario, # Usa el precio original del servicio
                                Subtotal=detalle.Subtotal, # Usa el subtotal original
                                MontoPagado=monto_a_aplicar_a_este_detalle,
                                Saldo=detalle.Saldo,
                                Descuento=detalle.Descuento,
                                DescuentoPorcentaje=detalle.DescuentoPorcentaje,
                                FechaRegistro=timezone.now(),
                                Activa=True,
                                ReciboID=recibo,
                            )
                            
                            monto_restante_a_pagar -= monto_a_aplicar_a_este_detalle
                    
                    # 4. Actualizar la factura principal
                    factura.MontoPagado = total_pagado_factura + monto_pagado_recibo
                    factura.Saldo = saldo_pendiente_factura - monto_pagado_recibo
                    
                    if factura.Saldo <= Decimal(0):
                        factura.Estado = 'Pagado'
                    
                    factura.save()
                    
                    return JsonResponse({'success': True, 'recibo_id': recibo.ReciboID, 'factura_id': factura.FacturaID})
            else:
                return JsonResponse({'error': 'El monto a pagar es inválido o excede el saldo pendiente.'}, status=400)
        
        # ... (Lógica para la renderización GET) ...
        saldo_pendiente_actualizado = factura.Total - total_pagado_factura
        
        context = {
            'titulo': f'Generar Recibo para Factura #{factura.FacturaID}',
            'factura': factura,
            'recibos_existentes': recibos_existentes,
            'total_pagado': total_pagado_factura,
            'saldo_pendiente': saldo_pendiente_actualizado,
            'detalles_con_saldo_pendiente': detalles_con_saldo_pendiente,
        }
        return render(request, 'facturacion/generar_recibo.html', context)
    
    except Exception as e:
        return JsonResponse({'error': f'Ocurrió un error inesperado: {e}'}, status=500)


@login_required
def conceptos_view(request):
    """
    Muestra la lista de conceptos de pago (Servicios).
    """
    servicios = Servicios.objects.filter(Activo=True).order_by('NombreServicio')
    context = {
        'titulo': 'Conceptos de Pago',
        'servicios': servicios
    }
    return render(request, 'facturacion/conceptos.html', context)

@login_required
def obtener_estudiante_info(request, estudiante_id):
    """
    Obtiene la información de un estudiante y los servicios correspondientes a su año de matrícula.
    Esta versión filtra los aranceles ya pagados por el estudiante.
    """
    try:
        # 1. Obtenemos el objeto Estudiante_Nueva por su ID
        estudiante = get_object_or_404(Estudiantes_Nueva, EstudianteID=estudiante_id)

        # 2. Obtenemos la última matrícula del estudiante
        try:
            matricula = Matricula.objects.filter(EstudianteID=estudiante).order_by('-AñoMatricula').first()
        except Matricula.DoesNotExist:
            matricula = None
        
        # 3. Obtenemos el Nivel y Año de Matrícula del estudiante
        nivel_id = matricula.NivelID.NivelID if matricula and matricula.NivelID else None
        año_matricula = matricula.AñoMatricula if matricula else None

        # 4. Obtenemos el ID del Tipo de Servicio "ARANCEL"
        try:
            tipo_arancel = TServicio.objects.get(TipoServicio='ARANCEL')
            tipo_arancel_id = tipo_arancel.TipoServicioID
        except TServicio.DoesNotExist:
            tipo_arancel_id = None

        # 5. Si tenemos el Nivel y el Año, procedemos a obtener los servicios
        servicios_a_mostrar = []
        if nivel_id and año_matricula:
            # Obtenemos todos los servicios que cumplen con el año y el nivel
            servicios_disponibles = Servicios.objects.filter(Anio=año_matricula, NivelID=nivel_id)
            
            # --- LÓGICA CLAVE: USANDO LOS MODELOS DE FACTURACIÓN ---
            # 6. Obtenemos los IDs de los servicios de tipo ARANCEL que ya han sido pagados
            # Se busca en DetallesFactura los registros que pertenecen a una Factura
            # del estudiante actual y que tienen el tipo de servicio "ARANCEL".
            aranceles_pagados_ids = DetalleFactura.objects.filter(
                FacturaID__EstudianteID=estudiante,
                ServicioID__TipoServicioID=tipo_arancel_id,
                Activa=True
            ).values_list('ServicioID', flat=True)
            

            # 7. Iteramos sobre los servicios disponibles para filtrar los aranceles pagados
            for servicio in servicios_disponibles:
                # Verificamos si es un arancel y si su ID no está en la lista de pagados
                if servicio.TipoServicioID.TipoServicioID == tipo_arancel_id:
                    if servicio.ServicioID not in aranceles_pagados_ids:
                        servicios_a_mostrar.append(servicio)
                else:
                    # Si no es un arancel, se añade directamente a la lista de servicios a mostrar
                    servicios_a_mostrar.append(servicio)

        facturas_pendientes_qs = Facturas.objects.filter(
            EstudianteID=estudiante,
            Saldo__gt=0
        ).order_by('Fecha')
        
        facturas_pendientes_data = [
            {
                'factura_id': factura.FacturaID,
                'fecha': factura.Fecha.strftime('%y-%m-%d'),
                'total': str(factura.Total),
                'saldo': str(factura.Saldo),
                'estado': factura.Estado
            } for factura in facturas_pendientes_qs
        ]

        # 8. Preparamos los datos de la respuesta
        servicios_data = [
            {
                'id': servicio.ServicioID,
                'nombre': servicio.NombreServicio,
                'precio': str(servicio.Precio),
                'Anio': servicio.Anio,
                'NivelID': servicio.NivelID.NivelID,
                'TipoServicio': servicio.TipoServicioID.TipoServicio,
                'tipo_item': 'servicio'
            } for servicio in servicios_a_mostrar
        ]
        
        # Productos de inventario (Variantes)
        variantes_disponibles = VarianteProducto.objects.filter(Activo=True, StockActual__gt=0, Producto__Activo=True)
        productos_data = [
            {
                'id': var.VarianteID,
                'nombre': str(var),
                'precio': str(var.Producto.PrecioVenta),
                'Anio': 'N/A',
                'NivelID': 'N/A',
                'TipoServicio': 'PRODUCTO',
                'Stock': var.StockActual,
                'tipo_item': 'producto',
                'foto_url': var.Producto.Foto.url if var.Producto.Foto else ''
            } for var in variantes_disponibles
        ]

        data = {
            'nombre_completo': estudiante.NombreCompleto,
            'grado': matricula.NivelID.NombreNivel if matricula and matricula.NivelID else 'N/A',
            'seccion': matricula.SeccionID.NombreSeccion if matricula and matricula.SeccionID else 'N/A',
            'modalidad': matricula.ModalidadID.NombreModalidad if matricula and matricula.ModalidadID else 'N/A',
            'turno': matricula.TurnoID.NombreTurno if matricula and matricula.TurnoID else 'N/A',
            'genero': estudiante.Genero,
            'edad': estudiante.Edad,
            'AñoMatricula': año_matricula,
            'servicios': servicios_data,
            'productos': productos_data,
            'facturas_pendientes': facturas_pendientes_data,
        }

        # 9. Devolvemos la respuesta JSON
        return JsonResponse(data)

    except Estudiantes_Nueva.DoesNotExist:
        return JsonResponse({'error': 'Estudiante no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)



def obtener_tipo_cambio(request):
    """
    Vista de API para obtener el tipo de cambio de compra del día.
    Espera un parámetro GET 'fecha' en formato YYYY-MM-DD.
    """
    fecha_str = request.GET.get('fecha', None)

    if not fecha_str:
        return JsonResponse({"error": "Parámetro 'fecha' no proporcionado"}, status=400)

    try:
        fecha_factura = parse_date(fecha_str)
        if not fecha_factura:
            raise ValueError("Formato de fecha inválido")
    except (ValueError, TypeError):
        return JsonResponse({"error": "Formato de fecha inválido. Use YYYY-MM-DD."}, status=400)

    # Buscar el tipo de cambio para la fecha de la factura
    try:
        # Nota: La lógica de búsqueda puede variar. Aquí se busca el tipo de cambio
        # donde la fecha de la factura está dentro del rango de vigencia.
        tipo_cambio_obj = TiposCambio.objects.filter(
            VigenciaInicio__lte=fecha_factura,
            VigenciaFin__gte=fecha_factura
        ).first()

        if tipo_cambio_obj:
            data = {
                "fecha": fecha_str,
                "cambiocompra": tipo_cambio_obj.CambioCompra,
            }
            return JsonResponse(data, status=200)
        else:
            return JsonResponse({"error": "Tipo de cambio no encontrado para la fecha."}, status=404)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
    

@login_required
def recibo_detalle_view(request, recibo_id):
    """
    Vista para mostrar los detalles de un recibo específico.
    """
    recibo = get_object_or_404(Recibo, ReciboID=recibo_id)
    
    # Obtenemos los detalles de la factura que corresponden a este recibo.
    # Esta es la lógica que habíamos modificado anteriormente y que causó el error.
    # La revertimos para que el recibo no aparezca vacío, aunque pueda mostrar servicios saldados.
    detalles_factura = DetalleFactura.objects.filter(FacturaID=recibo.FacturaID)
    
    context = {
        'titulo': f'Detalle de Recibo #{recibo.ReciboID}',
        'recibo': recibo,
        'detalles_factura': detalles_factura,
        'factura': recibo.FacturaID,
        'estudiante': recibo.FacturaID.EstudianteID,
    }
    return render(request, 'facturacion/recibo_detalle.html', context)


@login_required
def recibo_imprimir_view(request, recibo_id):
    """
    Vista para generar el recibo en un formato de impresión amigable,
    mostrando solo los detalles asociados a este recibo específico.
    """
    # 1. Obtener el recibo y su factura relacionada.
    recibo = get_object_or_404(Recibo, ReciboID=recibo_id)
    factura = recibo.FacturaID
    estudiante = factura.EstudianteID

    # Intentamos obtener la última matrícula del estudiante para detalles extra
    try:
        matricula = Matricula.objects.filter(EstudianteID=estudiante).latest('FechaMatricula')
    except Matricula.DoesNotExist:
        matricula = None
    
    # 2. Obtener los detalles de la factura que SOLO corresponden a este recibo.
    #    Esta es la clave para que no aparezcan los pagos anteriores.
    detalles_factura = DetalleFactura.objects.filter(ReciboID=recibo)

    context = {
        'recibo': recibo,
        'factura': factura,
        'estudiante': estudiante,
        'matricula': matricula,
        'detalles_factura': detalles_factura, # Ahora esta lista solo tiene los detalles del pago actual
        'now': timezone.now(),
        'request': request,
    }
    
    return render(request, 'facturacion/recibo_imprimir.html', context)

@csrf_exempt
def pagar_pendiente(request, factura_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            monto_pagado_float = data.get('monto_pagado')
            if monto_pagado_float is None:
                return JsonResponse({'error': 'Falta el monto a pagar.'}, status=400)
            
            monto_pagado = Decimal(str(monto_pagado_float))
            
            with transaction.atomic():
                factura = get_object_or_404(Facturas, FacturaID=factura_id, Activa=True)
                
                if monto_pagado > factura.Saldo:
                    return JsonResponse({'error': 'El monto a pagar no puede ser mayor que el saldo pendiente.'}, status=400)

                # Paso 1: Crear un nuevo recibo
                recibo = Recibo.objects.create(
                    FacturaID=factura,
                    FechaRegistro=timezone.now(),
                    FechaPago=timezone.now(),
                    MontoPagado=monto_pagado,
                    Saldo=factura.Saldo - monto_pagado,
                    Total=factura.Total,
                    Estado='Pagado' if (factura.Saldo - monto_pagado) <= 0 else 'Parcialmente Pagado'
                )
                
                # Paso 2: Crear un registro en DetallesFactura para el pago
                
                detalle_pendiente = DetalleFactura.objects.filter(
                    FacturaID=factura, 
                    Saldo__gt=0
                ).first()

                if not detalle_pendiente:
                    detalle_pendiente = DetalleFactura.objects.filter(FacturaID=factura).first()
                    if not detalle_pendiente:
                        return JsonResponse({'error': 'No se encontró el detalle de la factura para el pago.'}, status=404)

                servicio_pago = detalle_pendiente.ServicioID
                precio_unitario = detalle_pendiente.PrecioUnitario
                subtotal_original = detalle_pendiente.Subtotal
                
                detalle_pendiente.save()

                DetalleFactura.objects.create(
                    FacturaID=factura,
                    ServicioID=servicio_pago,
                    Cantidad=1,
                    PrecioUnitario=precio_unitario,
                    Subtotal=subtotal_original,
                    FechaRegistro=timezone.now(),
                    Activa=True,
                    MontoPagado=monto_pagado,
                    Saldo=detalle_pendiente.Saldo - monto_pagado,
                    Descuento=0,
                    DescuentoPorcentaje=0,
                    ReciboID=recibo
                )
                
                # ⚠️ INICIO DE LA LÓGICA AGREGADA ⚠️
                # Paso 3: Registrar el pago en DetallesArqueo
                arqueo_activo, created = Arqueos.objects.get_or_create(
                    UsuarioID=request.user,
                    Fecha=timezone.now().date(),
                    Activa=True,
                    defaults={
                        'FechaRegistro': timezone.now(),
                        'MontoDeclarado_Cordobas': Decimal('0.00'),
                        'MontoDeclarado_USD': Decimal('0.00'),
                        'MontoCalculado_Cordobas': Decimal('0.00'),
                        'MontoCalculado_USD': Decimal('0.00'),
                        'Diferencia_Cordobas': Decimal('0.00'),
                        'Diferencia_USD': Decimal('0.00'),
                        'Hora': timezone.now().time(),
                        'Observaciones': 'Arqueo automático del día'
                    }
                )

                # El monto que recibes del JavaScript ya está en córdobas (NIO)
                monto_cordobas = Decimal('0.00')
                monto_usd = Decimal('0.00')

                # Asignar el monto a la columna de moneda correspondiente
                if factura.Moneda == 'CS':
                    monto_cordobas = monto_pagado
                    arqueo_activo.MontoCalculado_Cordobas += monto_pagado
                elif factura.Moneda == 'USD':
                    # Si el JavaScript convierte a NIO, el monto_pagado ya está en NIO
                    # pero si quieres guardar el detalle en USD, necesitas la conversión
                    # si el JS envía el monto en la moneda original de la factura
                    
                    # Con la lógica de tu JS, el monto ya viene en NIO.
                    # Simplemente lo guardamos en el campo NIO del arqueo
                    monto_cordobas = monto_pagado
                    arqueo_activo.MontoCalculado_Cordobas += monto_pagado

                DetallesArqueo.objects.create(
                    ArqueoID=arqueo_activo,
                    ReciboID=recibo,
                    ServicioID=detalle_pendiente.ServicioID,
                    VarianteProductoID=detalle_pendiente.VarianteProductoID,
                    FacturaID=factura.FacturaID,
                    Monto=monto_pagado,
                    Anulada=False,
                    FechaRegistro=timezone.now(),
                    Activa=True,
                    MontoCordobas=monto_cordobas,
                    MontoUSD=monto_usd,
                    TipoPago="Efectivo",
                    Fecha=timezone.now().date(),
                )
                
                # Guardar el arqueo actualizado
                arqueo_activo.save()
                # ⚠️ FIN DE LA LÓGICA AGREGADA ⚠️

                # Paso 4: Actualizar la factura
                factura.Saldo -= monto_pagado
                factura.MontoPagado += monto_pagado
                if factura.Saldo <= 0:
                    factura.Estado = 'Pagado'
                else:
                    factura.Estado = 'Parcialmente Pagado'
                factura.save()

                return JsonResponse({
                    'success': True,
                    'message': 'Pago procesado y recibo generado.',
                    'recibo_id': recibo.ReciboID
                })

        except Facturas.DoesNotExist:
            return JsonResponse({'error': 'Factura no encontrada.'}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Cuerpo de la solicitud no es un JSON válido.'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Método no permitido.'}, status=405)

@login_required
def detalle_factura_view(request, factura_id):
    """
    Muestra los detalles de una factura específica, incluyendo los servicios
    facturados y el historial de pagos.
    """
    try:
        # Usamos .select_related() para optimizar las consultas
        factura = get_object_or_404(Facturas.objects.select_related('EstudianteID'), pk=factura_id)

        # Usamos .annotate() para calcular el total pagado hasta la fecha
        total_pagado = Recibo.objects.filter(FacturaID=factura).aggregate(Sum('MontoPagado'))['MontoPagado__sum'] or 0

        # Calculamos el saldo pendiente restando el total pagado al total de la factura
        saldo_pendiente = factura.Total - total_pagado

        detalles_base = DetalleFactura.objects.filter(FacturaID=factura).select_related('ServicioID', 'VarianteProductoID')
        servicios_unicos = {}
        for detalle in detalles_base:
            clave = f"serv_{detalle.ServicioID_id}" if detalle.ServicioID_id else f"prod_{detalle.VarianteProductoID_id}"
            if clave not in servicios_unicos:
                detalle.MontoPagadoAgrupado = detalle.MontoPagado
                servicios_unicos[clave] = detalle
            else:
                if detalle.MontoPagado:
                    servicios_unicos[clave].MontoPagadoAgrupado += detalle.MontoPagado
                
        detalles_servicios = list(servicios_unicos.values())
        for d in detalles_servicios:
            d.MontoPagado = d.MontoPagadoAgrupado
            d.Saldo = d.Subtotal - d.MontoPagado
        recibos = Recibo.objects.filter(FacturaID=factura).order_by('FechaPago')
        
        # ✅ Añadimos la lógica para obtener el arqueo activo
        arqueo_activo = Arqueos.objects.filter(
            UsuarioID=request.user, 
            Activa=True, 
            Fecha=timezone.now().date()
        ).first()

        context = {
            'factura': factura,
            'saldo_pendiente_factura': saldo_pendiente,
            'detalles_servicios': detalles_servicios,
            'recibos': recibos,
            'descuento_factura': factura,
            # ✅ Pasamos la variable arqueo_activo a la plantilla
            'arqueo_activo': arqueo_activo,
        }
        return render(request, 'facturacion/detalle_factura.html', context)
        
    except Facturas.DoesNotExist:
        # Asegúrate de que tienes una plantilla 404.html configurada
        return render(request, '404.html', {'message': 'Factura no encontrada.'}, status=404)
    
    except Exception as e:
        # En caso de cualquier otro error, puedes manejarlo aquí
        print(f"Error en detalle_factura_view: {e}")
        return render(request, 'error.html', {'message': 'Ocurrió un error inesperado.'}, status=500)


def historial_pagos_view(request, estudiante_id):
    """
    Muestra el historial de pagos y facturas de un estudiante específico.
    """
    estudiante = get_object_or_404(Estudiantes_Nueva, EstudianteID=estudiante_id)
    
    # Obtener todas las facturas del estudiante
    facturas = Facturas.objects.filter(EstudianteID=estudiante).order_by('-Fecha')
    
    # Preparamos una lista para almacenar los datos de cada factura y sus recibos
    historial_completo = []
    
    for factura in facturas:
        # Para cada factura, obtenemos sus detalles (servicios) y sus recibos
        detalles_factura = DetalleFactura.objects.filter(FacturaID=factura).select_related('ServicioID')
        recibos = Recibo.objects.filter(FacturaID=factura).order_by('FechaPago')
        
        # Calculamos el total pagado hasta la fecha
        total_pagado = recibos.aggregate(Sum('MontoPagado'))['MontoPagado__sum'] or 0

        historial_completo.append({
            'factura': factura,
            'detalles': detalles_factura,
            'recibos': recibos,
            'total_pagado': total_pagado,
        })
        
    context = {
        'titulo': f'Historial de Pagos de {estudiante.NombreCompleto}',
        'estudiante': estudiante,
        'historial_completo': historial_completo,
    }
    
    return render(request, 'facturacion/historial_pagos.html', context)

def pagos_view(request):
    """
    Muestra una lista de estudiantes paginada y con búsqueda para ver su historial de pagos.
    """
    # 1. Obtener el término de búsqueda (si existe)
    query = request.GET.get('q', '')

    # 2. Obtener el queryset base
    estudiantes_list = Estudiantes_Nueva.objects.all().order_by('NombreCompleto')

    # 3. Filtrar si hay búsqueda
    if query:
        estudiantes_list = estudiantes_list.filter(
            Q(NombreCompleto__icontains=query)
            # Puedes agregar más campos aquí con | Q(OtroCampo__icontains=query)
        )

    # 4. Configurar la paginación (10 estudiantes por página)
    paginator = Paginator(estudiantes_list, 10) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'titulo': 'Seleccionar Estudiante para Reportes',
        'estudiantes': page_obj, # Pasamos el objeto paginado en lugar de la lista completa
        'query': query, # Pasamos lo que se buscó para mantenerlo en la caja de texto
    }
    
    return render(request, 'facturacion/pagos.html', context)


@csrf_exempt
@login_required
@permission_required('facturacion.crear_arqueos', raise_exception=True)
def toggle_arqueo_view(request):
    """
    Vista para iniciar o cerrar un arqueo de caja.
    Si existe un arqueo activo, lo cierra.
    Si no existe, crea uno nuevo.
    """
    if request.method == 'POST':
        try:
            with transaction.atomic():
                usuario = request.user
                arqueo_activo = Arqueos.objects.filter(UsuarioID=usuario, Activa=True, Fecha=timezone.now().date()).first()

                if arqueo_activo:
                    # Si hay un arqueo activo, lo cerramos
                    arqueo_activo.Activa = False
                    arqueo_activo.save()
                    return JsonResponse({'success': True, 'message': 'Arqueo de caja cerrado con éxito.'})
                else:
                    # Si no hay un arqueo activo, creamos uno nuevo
                    now_local = timezone.localtime(timezone.now())
                    nuevo_arqueo = Arqueos.objects.create(
                        UsuarioID=usuario,
                        Fecha=timezone.now().date(),
                        Hora=timezone.now().time(),
                        Activa=True,
                        MontoDeclarado_Cordobas=Decimal('0.00'),
                        MontoDeclarado_USD=Decimal('0.00'),
                        MontoCalculado_Cordobas=Decimal('0.00'),
                        MontoCalculado_USD=Decimal('0.00'),
                        Diferencia_Cordobas=Decimal('0.00'),
                        Diferencia_USD=Decimal('0.00'),
                        FechaRegistro=timezone.now(),
                        Observaciones='Arqueo iniciado manualmente.'
                    )
                    return JsonResponse({'success': True, 'message': f'Nuevo arqueo de caja iniciado. ID: {nuevo_arqueo.ArqueoID}'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    return JsonResponse({'success': False, 'error': 'Método no permitido.'}, status=405)


@permission_required('facturacion.anular_recibo', raise_exception=True)
@login_required
@csrf_exempt
def anular_recibo_view(request, recibo_id):
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # 1. Obtener el recibo a anular
                recibo_a_anular = get_object_or_404(Recibo, pk=recibo_id)
                factura = recibo_a_anular.FacturaID
                
                # Verificar que el recibo no esté ya anulado
                if recibo_a_anular.Estado == 'Anulado':
                    return JsonResponse({'success': False, 'error': 'Este recibo ya ha sido anulado.'}, status=400)

                # 2. Revertir el monto en la Factura y recalcular su estado
                monto_anulado = recibo_a_anular.MontoPagado

                # Actualizar los campos de la factura
                factura.MontoPagado -= monto_anulado
                factura.Saldo += monto_anulado
                
                # Determinar el nuevo estado de la factura basado en el MontoPagado
                if factura.MontoPagado <= 0:
                    factura.Estado = 'Anulado'
                    factura.Activa = False
                    factura.Saldo = 0
                elif factura.MontoPagado < factura.Total:
                    factura.Estado = 'Pendiente'
                    factura.Activa = True
                else:
                    factura.Estado = 'Pagado'
                
                # La factura siempre se mantiene activa si no se anula por completo
                factura.save()
                
                # 3. Anular el recibo
                recibo_a_anular.Estado = 'Anulado'
                recibo_a_anular.Activo = False
                recibo_a_anular.save()
                
                detalles_del_recibo = DetalleFactura.objects.filter(ReciboID=recibo_a_anular)

                # Iterate to return stock if it's a product
                for detalle in detalles_del_recibo:
                    if detalle.VarianteProductoID:
                        detalle.VarianteProductoID.StockActual += detalle.Cantidad
                        detalle.VarianteProductoID.save()
                
                # Actualizamos los campos y desactivamos solo estos registros
                detalles_del_recibo.update(
                    Activa=False,
                    MontoPagado=0,
                    Descuento=0,
                    DescuentoPorcentaje=0,
                    Saldo=factura.Total
                )

                # 4. Anular los detalles del arqueo asociados
                detalles_arqueo = DetallesArqueo.objects.filter(ReciboID=recibo_a_anular)
                
                if detalles_arqueo.exists():
                    # Revertir el monto en el arqueo asociado
                    for detalle_arqueo in detalles_arqueo:
                        arqueo_activo = detalle_arqueo.ArqueoID
                        if arqueo_activo:
                            if factura.Moneda == 'CS':
                                arqueo_activo.MontoCalculado_Cordobas -= detalle_arqueo.Monto
                            elif factura.Moneda == 'USD':
                                arqueo_activo.MontoCalculado_USD -= detalle_arqueo.Monto
                            arqueo_activo.save()
                    
                    # Marcar los detalles del arqueo como anulados
                    detalles_arqueo.update(Anulada=True, Activa=False)

                return JsonResponse({'success': True, 'message': 'Recibo anulado correctamente.'})

        except Recibo.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'El recibo no fue encontrado.'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    return JsonResponse({'success': False, 'error': 'Método no permitido.'}, status=405)


@login_required
def lista_arqueos_view(request):
    """
    Vista para mostrar la lista paginada de arqueos de caja del usuario.
    """
    # --- CAMBIO AQUÍ ---
    # Añadimos '-ArqueoID' para asegurar un ordenamiento estable
    arqueos_list = Arqueos.objects.filter(UsuarioID=request.user).order_by('-Fecha', '-ArqueoID')
    
    # Configuración del Paginador
    paginator = Paginator(arqueos_list, 10) # 10 arqueos por página
    page_number = request.GET.get('page')
    
    try:
        arqueos_page = paginator.page(page_number)
    except PageNotAnInteger:
        arqueos_page = paginator.page(1)
    except EmptyPage:
        arqueos_page = paginator.page(paginator.num_pages)

    # --- Lógica para el rango de páginas ---
    num_pages_to_show = 5
    start_page = max(1, arqueos_page.number - (num_pages_to_show // 2))
    end_page = min(paginator.num_pages, start_page + num_pages_to_show - 1)
    
    if end_page - start_page < num_pages_to_show - 1:
        start_page = max(1, end_page - num_pages_to_show + 1)
    
    paginator_range = range(start_page, end_page + 1)
    # --- Fin lógica rango ---

    context = {
        'titulo': 'Historial de Arqueos',
        'arqueos_page': arqueos_page, 
        'paginator_range': paginator_range, 
    }
    return render(request, 'facturacion/lista_arqueos.html', context)


@login_required
def detalle_arqueo_view(request, arqueo_id):
    """
    Vista para mostrar los detalles de un arqueo de caja específico.
    """
    arqueo = get_object_or_404(Arqueos, ArqueoID=arqueo_id, UsuarioID=request.user)
    
    # Obtener los detalles de los recibos asociados a este arqueo.
    # Usamos select_related para seguir la ruta de relaciones:
    # DetallesArqueo -> Recibo -> Facturas -> Estudiantes_Nueva
    detalles = DetallesArqueo.objects.filter(ArqueoID=arqueo).select_related(
        'ReciboID__FacturaID__EstudianteID'
    ).order_by('ReciboID')
    
    context = {
        'titulo': f'Detalle de Arqueo #{arqueo.ArqueoID}',
        'arqueo': arqueo,
        'detalles': detalles,
    }
    return render(request, 'facturacion/detalle_arqueo.html', context)


@login_required
def imprimir_arqueo_view(request, arqueo_id):
    """
    Vista para generar la página de impresión de un arqueo.
    """
    arqueo = get_object_or_404(Arqueos, ArqueoID=arqueo_id, UsuarioID=request.user)
    
    # Excluir los recibos anulados y usar select_related para el rendimiento.
    detalles = DetallesArqueo.objects.filter(ArqueoID=arqueo).select_related(
        'ReciboID__FacturaID__EstudianteID'
    ).order_by('ReciboID')
    
    # Calcular los totales para mostrar en el reporte, excluyendo los anulados
    total_cordobas = sum(d.MontoCordobas for d in detalles if d.MontoCordobas is not None and not d.Anulada)
    total_usd = sum(d.MontoUSD for d in detalles if d.MontoUSD is not None and not d.Anulada)
    
    context = {
        'arqueo': arqueo,
        'detalles': detalles,
        'total_cordobas': total_cordobas,
        'total_usd': total_usd,
    }
    return render(request, 'facturacion/imprimir_arqueo.html', context)


def _generar_informe_aranceles(selected_nivel_id, selected_anio, selected_servicio_id, selected_estado):
    """Genera la lista de datos del informe y devuelve también el nombre del servicio."""
    
    reporte_aranceles = []
    selected_servicio_nombre = None
    TOLERANCIA = Decimal('0.01') 

    if not (selected_nivel_id and selected_anio and selected_servicio_id):
        return reporte_aranceles, selected_servicio_nombre

    try:
        # 1. Obtener la información del servicio (monto y nombre)
        # NOTA: Debes importar el modelo Servicios
        servicio = Servicios.objects.get(ServicioID=selected_servicio_id)
        monto_servicio = Decimal(servicio.Precio) 
        nombre_servicio = servicio.NombreServicio
        selected_servicio_nombre = nombre_servicio
        
        # Paso 2.1: Encontrar las Matrículas que cumplen Nivel, Año y activo=True
        # NOTA: Debes importar el modelo Matricula
        matriculas_qs = Matricula.objects.filter(
            NivelID__NivelID=selected_nivel_id,
            AñoMatricula=selected_anio,
            activo=True 
        ).select_related('EstudianteID', 'NivelID')
        
        estudiantes_ids = matriculas_qs.values_list('EstudianteID__EstudianteID', flat=True)

        if not estudiantes_ids.exists():
            print("ADVERTENCIA: No hay estudiantes con matrículas activas para los filtros seleccionados.")
            return reporte_aranceles, selected_servicio_nombre
        
        # ----------------------------------------------------------------------------------
        # ** CONSULTA DE PAGOS Y SALDOS FINALES **
        # ----------------------------------------------------------------------------------
        
        # NOTA: Debes importar el modelo DetalleFactura
        pagos_agregados_qs = DetalleFactura.objects.filter(
            FacturaID__EstudianteID__in=estudiantes_ids, 
            ServicioID__ServicioID=selected_servicio_id,
            FacturaID__Estado__in=['Pagado', 'Pago Parcial', 'Activa'] 
        ).values(
            'FacturaID__EstudianteID', 
            'ServicioID'
        ).annotate(
            monto_pagado_total=Coalesce(
                Sum('MontoPagado', output_field=DecimalField()), 
                Value(Decimal('0.00'), output_field=DecimalField())
            ),
            saldo_pendiente_total=Coalesce(
                Sum('Saldo', output_field=DecimalField()),
                Value(Decimal('0.00'), output_field=DecimalField())
            ),
            fecha_pago=F('FacturaID__Fecha')
        ).order_by('FacturaID__EstudianteID')
        
        ESTUDIANTE_KEY = 'FacturaID__EstudianteID'
        
        matriculas_por_estudiante = {
            m.EstudianteID.EstudianteID: m for m in matriculas_qs
        }
        
        estudiantes_con_pago = set()

        for item in pagos_agregados_qs:
            estudiante_id = item[ESTUDIANTE_KEY]
            estudiantes_con_pago.add(estudiante_id)
            
            monto_pagado = item['monto_pagado_total']
            saldo_registrado_db = item['saldo_pendiente_total']
            matricula = matriculas_por_estudiante.get(estudiante_id)
            
            if not matricula: continue
            
            # CÁLCULO DE ESTADO BASADO EN SALDO REGISTRADO (Maneja Descuentos)
            if saldo_registrado_db <= TOLERANCIA:
                estado_pago = "Pagado"
                saldo_a_mostrar = Decimal('0.00')
            else:
                estado_pago = "Pendiente"
                saldo_a_mostrar = saldo_registrado_db 

            if abs(monto_pagado - monto_servicio) <= TOLERANCIA and monto_pagado > Decimal('0'):
                estado_pago = "Pagado"
                saldo_a_mostrar = Decimal('0.00')
            
            reporte_aranceles.append({
                'nombre_completo': matricula.EstudianteID.NombreCompleto, 
                'nivel': matricula.NivelID.NombreNivel, 
                'servicio': nombre_servicio,
                'monto_servicio': float(monto_servicio),
                'monto_pagado': float(monto_pagado),    
                'saldo_pendiente': float(saldo_a_mostrar),
                'estado_pago': estado_pago,
                'fecha_pago': item['fecha_pago'].strftime("%d/%m/%Y") if item['fecha_pago'] else 'N/A',
            })
        
        # Estudiantes SIN PAGO
        for matricula in matriculas_qs:
            estudiante_id = matricula.EstudianteID.EstudianteID
            if estudiante_id not in estudiantes_con_pago:
                reporte_aranceles.append({
                    'nombre_completo': matricula.EstudianteID.NombreCompleto, 
                    'nivel': matricula.NivelID.NombreNivel, 
                    'servicio': nombre_servicio,
                    'monto_servicio': float(monto_servicio), 
                    'monto_pagado': float(Decimal('0.00')), 
                    'saldo_pendiente': float(monto_servicio),
                    'estado_pago': "Pendiente",
                    'fecha_pago': 'N/A',
                })
        
        # Aplicar filtro de estado si está seleccionado
        if selected_estado and selected_estado != 'Todos':
            reporte_aranceles = [
                item for item in reporte_aranceles
                if item['estado_pago'] == selected_estado
            ]

        # Ordenar el informe alfabéticamente
        reporte_aranceles.sort(key=lambda x: x['nombre_completo'])

    except Servicios.DoesNotExist:
        print("ERROR: Servicio no encontrado.")
    except Exception as e:
        print(f"ERROR grave al generar informe: {e}")
    
    return reporte_aranceles, selected_servicio_nombre


def informe_aranceles_view(request):
    """Vista principal para generar el informe con filtros."""
    
    # NOTA: Debes importar el modelo Niveles
    niveles = Niveles.objects.filter(Activo=True).order_by('NivelID')
    
    años = Servicios.objects.filter(
        TipoServicioID__TipoServicio="ARANCEL" 
    ).values_list('Anio', flat=True).distinct().order_by('-Anio')
    
    selected_nivel_id = request.GET.get('nivel_id')
    selected_anio = request.GET.get('año')
    selected_servicio_id = request.GET.get('servicio_id')
    selected_estado = request.GET.get('estado')
    
    # Llamamos a la función auxiliar para obtener los datos
    reporte_aranceles, selected_servicio_nombre = _generar_informe_aranceles(
        selected_nivel_id, selected_anio, selected_servicio_id, selected_estado
    )

    context = {
        'niveles': niveles,
        'años': sorted(list(años), reverse=True),
        'selected_nivel_id': selected_nivel_id,
        'selected_anio': selected_anio,
        'selected_servicio_id': selected_servicio_id,
        'selected_estado': selected_estado,
        'selected_servicio_nombre': selected_servicio_nombre,
        'reporte_aranceles': reporte_aranceles,
    }

    return render(request, 'facturacion/informe_aranceles.html', context)


def informe_aranceles_imprimir_view(request):
    """NUEVA VISTA: Genera el informe en un formato simple para impresión directa."""
    
    selected_nivel_id = request.GET.get('nivel_id')
    selected_anio = request.GET.get('año')
    selected_servicio_id = request.GET.get('servicio_id')
    selected_estado = request.GET.get('estado')
    
    # Reutilizamos la lógica centralizada
    reporte_aranceles, selected_servicio_nombre = _generar_informe_aranceles(
        selected_nivel_id, selected_anio, selected_servicio_id, selected_estado
    )
    
    # Si no hay filtros o datos, devolvemos un template vacío para evitar errores
    if not selected_servicio_id or not reporte_aranceles:
        # Aquí puedes decidir si redirigir o mostrar un mensaje de error. 
        # Para impresión, un template vacío con mensaje es más seguro.
        context = {
            'reporte_aranceles': [],
            'selected_servicio_nombre': selected_servicio_nombre, # Puede ser None
        }
        return render(request, 'facturacion/informe_aranceles_print.html', context)


    context = {
        'selected_anio': selected_anio,
        'selected_estado': selected_estado,
        'selected_servicio_nombre': selected_servicio_nombre,
        'reporte_aranceles': reporte_aranceles,
    }
    
    # Renderizamos la nueva plantilla de impresión
    return render(request, 'facturacion/informe_aranceles_print.html', context)


# --- VISTA API PARA CARGA DINÁMICA DE ARANCELES (Se mantiene igual) ---

@require_http_methods(["GET"])
def api_obtener_servicios(request):
    """
    API para obtener servicios (aranceles) dinámicamente basados en el Nivel y el Año seleccionados.
    """
    
    nivel_id = request.GET.get('nivel_id')
    año = request.GET.get('año') 

    servicios_data = []

    if nivel_id and año:
        try:
            # NOTA: Debes importar el modelo Servicios
            servicios = Servicios.objects.filter(
                NivelID__NivelID=nivel_id,
                Anio=año, 
                TipoServicioID__TipoServicio="ARANCEL", 
                Activo=True
            ).order_by('NombreServicio').values('ServicioID', 'NombreServicio')
            
            servicios_data = list(servicios)

        except Exception as e:
            print(f"ERROR en api_obtener_servicios: {e}")
            return JsonResponse([], safe=False)
            
    return JsonResponse(servicios_data, safe=False)

@login_required
def exportar_arqueo_excel_view(request, arqueo_id):
    """
    Vista para exportar el detalle de un arqueo específico a un archivo de Excel (XLSX)
    con formato de encabezado y celdas combinadas.
    """
    arqueo = get_object_or_404(Arqueos, ArqueoID=arqueo_id, UsuarioID=request.user)
    
    detalles = DetallesArqueo.objects.filter(ArqueoID=arqueo).select_related(
        'ReciboID__FacturaID__EstudianteID', 
        'ServicioID' 
    ).order_by('ReciboID')
    
    total_cordobas = sum(d.MontoCordobas for d in detalles if d.MontoCordobas is not None and not d.Anulada)
    total_usd = sum(d.MontoUSD for d in detalles if d.MontoUSD is not None and not d.Anulada)

    # 1. Configurar la respuesta HTTP para XLSX
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    filename = f"reporte_arqueo_{arqueo.ArqueoID}_{arqueo.Fecha.strftime('%Y%m%d')}.xlsx"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    # 2. Crear el libro de trabajo y la hoja
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    
    # ----------------------------------------------------
    # 3. CREACIÓN DEL ENCABEZADO COMBINADO
    # El reporte completo va desde la Columna B hasta la J (9 columnas)
    
    # Estilos
    bold_center = Alignment(horizontal='center', vertical='center')
    big_bold_font = Font(bold=True, size=16)
    normal_bold_font = Font(bold=True, size=12)

    # Fila 1: Nombre del Colegio
    sheet.merge_cells('B1:J1')
    sheet['B1'] = "Colegio Cristiano \"Jehová Shalom\""
    sheet['B1'].alignment = bold_center
    sheet['B1'].font = normal_bold_font

    # Fila 2: Título del Reporte
    sheet.merge_cells('B2:J2')
    sheet['B2'] = f"REPORTE DE ARQUEO DIARIO #{arqueo.ArqueoID}"
    sheet['B2'].alignment = bold_center
    sheet['B2'].font = big_bold_font

    # Fila 3: Fecha del Arqueo
    sheet.merge_cells('B3:J3')
    sheet['B3'] = f"Fecha de Arqueo: {arqueo.Fecha.strftime('%d/%m/%Y')}"
    sheet['B3'].alignment = bold_center
    sheet['B3'].font = normal_bold_font
    
    # Fila 4: Cajero
    sheet.merge_cells('B4:J4')
    sheet['B4'] = f"Cajero: {arqueo.UsuarioID.username}"
    sheet['B4'].alignment = bold_center
    sheet['B4'].font = normal_bold_font
    
    # ----------------------------------------------------

    # --- Tabla de Datos (Empieza en Fila 6) ---
    row_num = 6
    
    # 4. Definir y escribir la fila de encabezado de la tabla (en Fila 6)
    headers = [
        'Factura', 'Fecha', 'Recibo', 'Estudiante', 'Concepto', 
        'Monto (C$)', 'Monto (USD)', 'Tipo Pago', 'Cajero', 'Estado'
    ]
    # Escribir los encabezados de la tabla a partir de la columna B (usando row_num=6)
    for col_num, header in enumerate(headers, 2):  # Inicia en la columna 2 (B)
        cell = sheet.cell(row=row_num, column=col_num, value=header)
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='center')
        cell.border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))


    # 5. Escribir las filas de datos (a partir de Fila 7)
    for detalle in detalles:
        row_num += 1
        
        row_data = [
            detalle.ReciboID.FacturaID.FacturaID if detalle.ReciboID and detalle.ReciboID.FacturaID else '', 
            detalle.Fecha, 
            detalle.ReciboID.ReciboID,
            detalle.ReciboID.FacturaID.EstudianteID.NombreCompleto if detalle.ReciboID and detalle.ReciboID.FacturaID and detalle.ReciboID.FacturaID.EstudianteID else '',
            detalle.ServicioID.NombreServicio if detalle.ServicioID else (str(detalle.VarianteProductoID) if getattr(detalle, 'VarianteProductoID', None) else 'Variante/Producto'),
            detalle.MontoCordobas,
            detalle.MontoUSD,
            detalle.TipoPago,
            detalle.ArqueoID.UsuarioID.username,
            'Anulada' if detalle.Anulada else 'Activa',
        ]
        
        # Escribir los datos en la fila actual, empezando en la columna B (2)
        for col_num, value in enumerate(row_data, 2):
            cell = sheet.cell(row=row_num, column=col_num, value=value)
            # Añadir bordes a todas las celdas de datos
            cell.border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))

            # Aplicar formato de Anulada (texto rojo) y Centrado para Estado
            if detalle.Anulada:
                cell.font = Font(color="FF0000") # Rojo
            if col_num == 11: # Columna 'Estado' (J)
                cell.alignment = Alignment(horizontal='center')

            # Aplicar formato numérico a las monedas
            if col_num in [6, 7]: # Columnas Monto (C$) y Monto (USD)
                 cell.number_format = '#,##0.00'
                 
    # ----------------------------------------------------
    # 6. Fila de TOTALES (Combina y Formatea)
    
    total_row = sheet.max_row + 3
    
    # Combinar celdas de la etiqueta "TOTAL" (Columnas B a E)
    sheet.merge_cells(start_row=total_row, start_column=2, end_row=total_row, end_column=6)
    total_label_cell = sheet.cell(row=total_row, column=2, value='TOTAL')
    total_label_cell.font = Font(bold=True)
    total_label_cell.alignment = Alignment(horizontal='right')
    
    # Monto (C$) - Columna F (6)
    total_cordobas_cell = sheet.cell(row=total_row, column=7, value=total_cordobas)
    total_cordobas_cell.font = Font(bold=True)
    total_cordobas_cell.number_format = '#,##0.00'

    # Monto (USD) - Columna G (7)
    total_usd_cell = sheet.cell(row=total_row, column=8, value=total_usd)
    total_usd_cell.font = Font(bold=True)
    total_usd_cell.number_format = '#,##0.00'

    # ----------------------------------------------------
    # 7. Ajustar Ancho de Columnas (Recomendado para visibilidad)

    column_widths = {
        'B': 10,  # Factura
        'C': 12,  # Fecha
        'D': 10,  # Recibo
        'E': 30,  # Estudiante
        'F': 20,  # Concepto
        'G': 15,  # Monto (C$)
        'H': 15,  # Monto (USD)
        'I': 15,  # Tipo Pago
        'J': 15,  # Cajero
        'K': 12,  # Estado
    }
    
    for col, width in column_widths.items():
        sheet.column_dimensions[col].width = width

    # 8. Guardar el libro de trabajo
    workbook.save(response)

    return response


def informe_aranceles_exportar_view(request):
    """
    Vista que exporta los datos del informe de aranceles a un archivo Excel (XLSX).
    """
    selected_nivel_id = request.GET.get('nivel_id')
    selected_anio = request.GET.get('año')
    selected_servicio_id = request.GET.get('servicio_id')
    selected_estado = request.GET.get('estado')

    # Reutilizamos la lógica centralizada para obtener los datos
    # NOTA: Asume que _generar_informe_aranceles devuelve una lista de diccionarios
    reporte_aranceles, selected_servicio_nombre = _generar_informe_aranceles(
        selected_nivel_id, selected_anio, selected_servicio_id, selected_estado
    )

    # Si no hay filtros aplicados o datos, redirigir al informe base o mostrar mensaje
    if not reporte_aranceles:
        # Se puede redirigir a la vista principal con un mensaje de error si se desea, 
        # pero para una API de exportación, un status 204 o 400 es más apropiado.
        return HttpResponse("No hay datos para exportar con los filtros seleccionados.", status=204)

    # --- Configuración de Respuesta y Excel ---
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    # Nombre del archivo para la descarga
    nombre_arancel = selected_servicio_nombre.replace(' ', '_').replace('/', '-') if selected_servicio_nombre else "informe"
    filename = f"informe_aranceles_{nombre_arancel}_{selected_anio}.xlsx"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = 'Informe Aranceles'

    # --- Estilos ---
    bold_font = Font(bold=True)
    center_alignment = Alignment(horizontal='center', vertical='center')
    money_format = '#,##0.00'
    thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), 
                         top=Side(style='thin'), bottom=Side(style='thin'))
    
    # --- Encabezado del Reporte (Combinación de Celdas) ---
    
    # Fila 1: Título Principal
    sheet.merge_cells('A1:H1')
    sheet['A1'] = "INFORME DE ESTADO DE PAGOS DE ARANCELES"
    sheet['A1'].font = Font(bold=True, size=16)
    sheet['A1'].alignment = center_alignment

    # Fila 2: Filtros Aplicados
    sheet.merge_cells('A2:H2')
    filtros = f"Arancel: {selected_servicio_nombre or 'N/A'} | Año: {selected_anio or 'N/A'} | Estado: {selected_estado or 'Todos'}"
    sheet['A2'] = filtros
    sheet['A2'].font = Font(bold=True, size=12)
    sheet['A2'].alignment = center_alignment
    
    # --- Encabezados de la Tabla (Fila 4) ---
    headers = [
        'Estudiante', 'Nivel', 'Arancel', 'Monto Servicio (C$)', 
        'Monto Pagado (C$)', 'Saldo Pendiente (C$)', 'Estado', 'Fecha Último Pago'
    ]
    row_num = 4
    for col_num, header in enumerate(headers, 1):
        cell = sheet.cell(row=row_num, column=col_num, value=header)
        cell.font = bold_font
        cell.alignment = center_alignment
        cell.border = thin_border
        
    # --- Datos de las Filas (A partir de Fila 5) ---
    for item in reporte_aranceles:
        row_num += 1
        
        # CORRECCIÓN CLAVE: Acceder a los datos usando notación de diccionario ['clave']
        estado = item['estado_pago'] 
        monto_pagado = item.get('monto_pagado', 0) # Usar .get() para valores numéricos es más seguro

        if monto_pagado > 0 and estado == "Pendiente":
            estado = "Parcial"

        row_data = [
            item.get('nombre_completo', ''),
            item.get('nivel', ''),
            item.get('servicio', ''),
            item.get('monto_servicio', 0),
            monto_pagado,
            item.get('saldo_pendiente', 0),
            estado,
            item.get('fecha_pago', ''),
        ]
        
        for col_num, value in enumerate(row_data, 1):
            cell = sheet.cell(row=row_num, column=col_num, value=value)
            cell.border = thin_border # Aplicar borde a todas las celdas
            
            # Formato de Moneda para Montos (Columnas 4, 5, 6)
            if col_num in [4, 5, 6]:
                cell.number_format = money_format
                cell.alignment = Alignment(horizontal='right')
                
            # Colorear el estado (Columna 7)
            if col_num == 7: 
                cell.alignment = Alignment(horizontal='center')
                if estado == "Pendiente":
                    cell.font = Font(color="FF0000", bold=True) # Rojo
                elif estado == "Parcial":
                    cell.font = Font(color="FF9900", bold=True) # Naranja/Amarillo
                elif estado == "Pagado":
                    cell.font = Font(color="008000", bold=True) # Verde


    # --- Ajuste de Ancho de Columnas ---
    column_widths = {
        'A': 40,  # Estudiante
        'B': 15,  # Nivel
        'C': 25,  # Arancel
        'D': 15,  # Monto Servicio
        'E': 15,  # Monto Pagado
        'F': 15,  # Saldo Pendiente
        'G': 12,  # Estado
        'H': 18,  # Fecha Pago
    }
    
    for col, width in column_widths.items():
        sheet.column_dimensions[col].width = width

    # --- Guardar y devolver la respuesta ---
    workbook.save(response)

    return response


def consulta_ingresos_view(request):
    """
    Genera una consulta de ingresos totales filtrada por la FECHA DE PAGO (Recibo).
    
    La consulta principal y la tabla de detalle ahora se basan en los DetallesArqueo
    para reflejar el ingreso real de caja en el período, no la fecha de la Factura.
    """
    hoy = date.today()
    
    fecha_inicio_str = request.GET.get('fecha_inicio')
    fecha_fin_str = request.GET.get('fecha_fin')

    try:
        fecha_inicio = date.fromisoformat(fecha_inicio_str) if fecha_inicio_str else hoy - timedelta(days=30)
        fecha_fin = date.fromisoformat(fecha_fin_str) if fecha_fin_str else hoy
    except ValueError:
        fecha_inicio = hoy - timedelta(days=30)
        fecha_fin = hoy
        
    if fecha_inicio > fecha_fin:
        fecha_inicio = fecha_fin

    # 1. Obtener los detalles de los pagos (DetallesArqueo) activos en el rango de FECHAS DE PAGO
    # Usamos DetallesArqueo porque es la tabla que registra el ingreso de caja por fecha.
    pagos_queryset = DetallesArqueo.objects.filter(
        Activa=True,
        Anulada=False, # Excluir recibos anulados
        Fecha__range=[fecha_inicio, fecha_fin]
    ).select_related(
        'ReciboID__FacturaID__EstudianteID' # Trae la factura y el estudiante
    ).order_by('-Fecha', '-ReciboID__ReciboID')
    
    
    # 2. Inicializar totales
    total_cordobas = Decimal('0.00')
    total_dolares = Decimal('0.00')
    tipo_cambio = Decimal('1.00')

    # 3. Obtener el Tipo de Cambio más reciente
    tipo_cambio_obj = TiposCambio.objects.order_by('-FechaRegistro').first()
    if tipo_cambio_obj:
        tipo_cambio = tipo_cambio_obj.CambioCompra

    # 4. Calcular Ingresos Totales Globales (Suma de los montos en DetallesArqueo)
    
    # Sumar todos los pagos en Córdobas y Dólares por separado:
    
    # Total de Córdobas
    total_cordobas_aggr = pagos_queryset.aggregate(
        total=Coalesce(Sum('MontoCordobas'), Value(Decimal('0.00')))
    )['total']
    total_cordobas = total_cordobas_aggr

    # Total de Dólares
    total_dolares_aggr = pagos_queryset.aggregate(
        total=Coalesce(Sum('MontoUSD'), Value(Decimal('0.00')))
    )['total']
    total_dolares = total_dolares_aggr

    # 5. Cantidad de Recibos procesados (No facturas, sino transacciones de pago)
    # Contamos los ReciboIDs únicos dentro del queryset de pagos
    total_recibos = pagos_queryset.values('ReciboID').distinct().count()

    # 6. PAGINACIÓN para el detalle (basada en el queryset de pagos)
    paginator = Paginator(pagos_queryset, 20)  # 20 pagos por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # 7. Contexto
    context = {
        'titulo': 'Consulta de Ingresos por Período (Según Fecha de Pago)',
        'page_obj': page_obj,
        
        # Variables alineadas con el reporte de impresión:
        'total_cordobas': total_cordobas,        
        'total_dolares': total_dolares,          
        'tipo_cambio': tipo_cambio,
        
        'total_facturas': total_recibos, # Renombramos la variable en el template para ser más preciso.
        'fecha_inicio': fecha_inicio.isoformat(), 
        'fecha_fin': fecha_fin.isoformat(),       
        
        # Nueva variable para el detalle de la tabla, que ahora es DetallesArqueo
        'detalles_pagos': page_obj, 
    }
    
    return render(request, 'facturacion/consulta_ingresos.html', context)


# ----------------------------------------------------------------------
# VISTA DE IMPRESIÓN (MODIFICADA PARA USAR DETALLESARQUEO)
# ----------------------------------------------------------------------

def consulta_ingresos_imprimir_view(request):
    """
    Vista para imprimir el resumen consolidado de ingresos, agrupado por FECHA DE PAGO (DetallesArqueo).
    Asegura que las fechas de inicio, fin y generación sean objetos válidos para el filtro |date.
    """
    hoy = date.today()
    
    fecha_inicio_str = request.GET.get('fecha_inicio')
    fecha_fin_str = request.GET.get('fecha_fin')
    
    incluir_facturas = request.GET.get('incluir_facturas', 'false').lower() == 'true'

    # CONVERSIÓN CRÍTICA: Aseguramos que las variables sean objetos date/datetime
    try:
        # Aquí convertimos las cadenas a objetos date de Python
        fecha_inicio = date.fromisoformat(fecha_inicio_str) if fecha_inicio_str else hoy - timedelta(days=30)
        fecha_fin = date.fromisoformat(fecha_fin_str) if fecha_fin_str else hoy
    except ValueError:
        # En caso de error, usamos valores predeterminados (como ya lo tenías)
        fecha_inicio = hoy - timedelta(days=30)
        fecha_fin = hoy
        
    if fecha_inicio > fecha_fin:
        fecha_inicio = fecha_fin

    # La fecha actual se obtiene como un objeto timezone consciente (datetime)
    fecha_generacion = timezone.now()


    # 1. Agrupación y Suma de Ingresos por Fecha y Moneda (Resumen Diario)
    ingresos_agrupados = DetallesArqueo.objects.filter(
        Activa=True,
        Anulada=False,
        Fecha__range=[fecha_inicio, fecha_fin]
    ).values(
        'Fecha'
    ).annotate(
        total_cordobas_dia=Coalesce(Sum('MontoCordobas'), Value(Decimal('0.00'))),
        total_dolares_dia=Coalesce(Sum('MontoUSD'), Value(Decimal('0.00'))),
    ).order_by('Fecha')
    
    
    # Reestructurar datos para el resumen
    resumen_list = []
    total_global_cordobas = Decimal('0.00')
    total_global_dolares = Decimal('0.00')

    for item in ingresos_agrupados:
        cordobas = item['total_cordobas_dia']
        dolares = item['total_dolares_dia']
        
        resumen_list.append({
            'fecha': item['Fecha'], # Esto ya es un objeto date/datetime del queryset
            'cordobas': cordobas,
            'dolares': dolares,
        })
        
        total_global_cordobas += cordobas
        total_global_dolares += dolares


    # 2. Obtener el Detalle de Pagos (DetallesArqueo) (SOLO si se solicita)
    pagos_detalle = None
    if incluir_facturas:
        pagos_detalle = DetallesArqueo.objects.filter(
            Activa=True,
            Anulada=False,
            Fecha__range=[fecha_inicio, fecha_fin]
        ).select_related(
            'ReciboID__FacturaID__EstudianteID', 
            'ServicioID'
        ).order_by('Fecha', 'ReciboID__ReciboID')


    # 3. Contexto
    context = {
        'titulo': 'Resumen Diario de Ingresos por Período (Según Fecha de Pago)',
        'fecha_inicio': fecha_inicio, # Pasa el objeto date
        'fecha_fin': fecha_fin,       # Pasa el objeto date
        'fecha_generacion': fecha_generacion, # Pasa el objeto datetime
        'resumen_list': resumen_list,
        'total_global_cordobas': total_global_cordobas,
        'total_global_dolares': total_global_dolares,
        'incluir_facturas': incluir_facturas,          
        'pagos_detalle': pagos_detalle,                
    }
    
    return render(request, 'facturacion/consulta_ingresos_imprimir.html', context)

@require_http_methods(["GET"])
def api_servicios_por_nivel_y_anio(request):
    """
    API para obtener servicios filtrados por NivelID y Año.
    Devuelve NombreServicio, ServicioID y Precio.
    """
    nivel_id = request.GET.get('nivel_id')
    anio = request.GET.get('anio') 
    
    if not nivel_id or not anio:
        return JsonResponse([], safe=False)

    try:
        servicios = Servicios.objects.filter(
            NivelID__NivelID=nivel_id,
            Anio=anio,
            Activo=True
        ).order_by('NombreServicio').values('ServicioID', 'NombreServicio', 'Precio')
        
        servicios_data = [
            {
                'ServicioID': s['ServicioID'],
                'NombreServicio': s['NombreServicio'],
                # Aseguramos que el precio sea una cadena para el JS
                'Precio': str(s['Precio']) 
            } for s in servicios
        ]
        return JsonResponse(servicios_data, safe=False)

    except Exception as e:
        print(f"Error en api_servicios_por_nivel_y_anio: {e}")
        return JsonResponse([], safe=False)


@login_required
def consulta_saldos_view(request):
    """
    Genera el informe de saldos pendientes por concepto de servicio, nivel y año lectivo.
    
    CORRECCIÓN FINAL: El saldo se calcula restando (Monto Pagado + Descuento) del 
    Monto Facturado Bruto, asegurando que los servicios con descuento salgan en C$ 0.00.
    """
    # Filtros
    selected_anio = request.GET.get('anio_lectivo')
    selected_nivel_id = request.GET.get('nivel_id')
    selected_servicio_id = request.GET.get('servicio_id')
    
    # Inicialización de variables de contexto
    reporte_saldos = []
    total_saldo_global = Decimal(0)
    total_facturado_global = Decimal(0)
    selected_servicio_nombre = "N/A"
    selected_nivel_nombre = "N/A"
    servicios_seleccionados = []


    # Obtener opciones para los filtros
    anios_disponibles = Matricula.objects.values_list('AñoMatricula', flat=True).distinct().order_by('-AñoMatricula')
    niveles = Nivel.objects.filter(Activo=True).order_by('NivelID')
    
    
    if selected_anio and selected_nivel_id and selected_servicio_id:
        
        # 1. Obtener datos de nombres para los títulos
        try:
            servicio = Servicios.objects.get(ServicioID=selected_servicio_id)
            selected_servicio_nombre = servicio.NombreServicio
            nivel = Nivel.objects.get(NivelID=selected_nivel_id)
            selected_nivel_nombre = nivel.NombreNivel
        except (Servicios.DoesNotExist, Nivel.DoesNotExist):
            pass 

        # 2. CONSULTA FINAL: Agregamos el Monto Pagado, el Descuento, y el Monto Bruto Facturado por Servicio.
        
        facturas_qs = Facturas.objects.filter(
            Activa=True,
            MatriculaID__AñoMatricula=selected_anio,
            MatriculaID__NivelID__NivelID=selected_nivel_id,
        ).annotate(
            # 1. Monto Pagado ESPECÍFICO (Dinero recibido)
            monto_pagado_servicio=Coalesce(
                Sum('detallefactura__MontoPagado', filter=Q(detallefactura__ServicioID__ServicioID=selected_servicio_id)),
                Decimal(0),
                output_field=DecimalField()
            ),
            # 2. Monto de Descuento ESPECÍFICO (Dinero perdonado)
            monto_descuento_servicio=Coalesce(
                Sum('detallefactura__Descuento', filter=Q(detallefactura__ServicioID__ServicioID=selected_servicio_id)),
                Decimal(0),
                output_field=DecimalField()
            ),
            # 3. Monto Facturado BRUTO (Precio Original, usando MAX de Subtotal para evitar duplicados)
            monto_facturado_servicio=Coalesce(
                Max('detallefactura__Subtotal', filter=Q(detallefactura__ServicioID__ServicioID=selected_servicio_id)),
                Decimal(0),
                output_field=DecimalField()
            )
        ).filter(
            # Solo incluimos facturas donde el servicio haya sido facturado (Monto Facturado > 0)
            monto_facturado_servicio__gt=Decimal(0) 
        ).values(
            'EstudianteID__NombreCompleto',
            'FacturaID',
            'Moneda',
            'monto_facturado_servicio',
            'monto_pagado_servicio',
            'monto_descuento_servicio' # Incluimos el descuento en el .values()
        ).order_by('EstudianteID__NombreCompleto')
        
        
        # 3. Procesar resultados y calcular el saldo específico en Python
        
        for item in facturas_qs:
            monto_facturado = item['monto_facturado_servicio']
            monto_pagado = item['monto_pagado_servicio']
            monto_descuento = item['monto_descuento_servicio']
            
            # Monto Cubierto = Pagado + Descuento
            monto_cubierto = monto_pagado + monto_descuento
            
            # Saldo Pendiente ESPECÍFICO = Monto Facturado Bruto - Monto Cubierto
            saldo_especifico = monto_facturado - monto_cubierto
            
            # Nos aseguramos de que el saldo no sea negativo (por si acaso)
            if saldo_especifico < Decimal(0):
                saldo_especifico = Decimal(0)
            
            # Solo incluimos a quienes deben o han facturado algo de este servicio.
            if saldo_especifico > Decimal(0) or monto_pagado > Decimal(0) or monto_descuento > Decimal(0):
                
                reporte_saldos.append({
                    'nombre_completo': item['EstudianteID__NombreCompleto'],
                    'servicio': selected_servicio_nombre, 
                    'moneda': item['Moneda'],
                    'monto_servicio': monto_facturado,          # Monto Facturado BRUTO (ej: C$1650.00)
                    'monto_pagado': monto_pagado,               # Dinero en caja (ej: C$1402.50)
                    'monto_descuento': monto_descuento,         # Descuento (ej: C$247.50)
                    'saldo_pendiente': saldo_especifico,        # Saldo Final (ej: C$0.00)
                    'factura_id': item['FacturaID']
                })
                total_saldo_global += saldo_especifico
                
                # Sumamos el monto facturado bruto del servicio
                total_facturado_global += monto_facturado
                
        # Solo mostramos a quienes tienen saldo pendiente > 0 y ordenamos
        # Se incluye una pequeña tolerancia para asegurar que saldos de 0.00001 no aparezcan
        TOLERANCIA = Decimal('0.001')
        reporte_saldos = [r for r in reporte_saldos if r['saldo_pendiente'] > TOLERANCIA]
        reporte_saldos.sort(key=lambda x: x['saldo_pendiente'], reverse=True)
        
        # Precargar los servicios para que se muestren en el dropdown después del submit
        servicios_seleccionados = Servicios.objects.filter(
            NivelID__NivelID=selected_nivel_id, 
            Anio=selected_anio, 
            Activo=True
        )


    context = {
        'titulo': 'Informe de Saldos Pendientes',
        'niveles': niveles,
        'anios_disponibles': anios_disponibles,
        'servicios_seleccionados': servicios_seleccionados,
        
        'selected_anio': selected_anio,
        'selected_nivel_id': selected_nivel_id,
        'selected_servicio_id': selected_servicio_id,
        
        'selected_servicio_nombre': selected_servicio_nombre,
        'selected_nivel_nombre': selected_nivel_nombre,
        
        'reporte_saldos': reporte_saldos,
        'total_saldo_global': total_saldo_global,
        'total_facturado_global': total_facturado_global,
    }

    return render(request, 'facturacion/consulta_saldos_pendientes.html', context)

@login_required
def consulta_facturas_pendientes_view(request):
    """
    Muestra todas las facturas que tienen un saldo pendiente (Saldo > 0).
    Permite filtrar por año y nivel, e implementa paginación.
    """
    from decimal import Decimal
    from django.db.models import Sum
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger # 👈 Importar Paginator
    
    selected_anio = request.GET.get('anio_lectivo')
    selected_nivel_id = request.GET.get('nivel_id')
    page = request.GET.get('page', 1) # 👈 Obtener el número de página, por defecto 1
    
    # Consulta base: Facturas activas con saldo mayor a cero
    # Nota: El 'facturas_pendientes_qs' sigue siendo el queryset completo para calcular el total
    facturas_pendientes_qs = Facturas.objects.filter(
        Activa=True, 
        Saldo__gt=Decimal('0.001') # Usar una pequeña tolerancia para asegurar Saldo > 0
    ).select_related(
        'EstudianteID', 
        'MatriculaID__NivelID'
    ).order_by(
        'Fecha', 
        'EstudianteID__NombreCompleto'
    )
    
    # Aplicar filtros si están presentes
    if selected_anio:
        facturas_pendientes_qs = facturas_pendientes_qs.filter(
            MatriculaID__AñoMatricula=selected_anio
        )
    
    if selected_nivel_id:
        facturas_pendientes_qs = facturas_pendientes_qs.filter(
            MatriculaID__NivelID__NivelID=selected_nivel_id
        )

    # Calcular el total global de saldo pendiente
    total_facturas_pendientes = facturas_pendientes_qs.aggregate(
        total_saldo=Sum('Saldo')
    )['total_saldo'] or Decimal(0)
    
    # --- Lógica de Paginación ---
    
    # 1. Crear el objeto Paginator con 10 elementos por página
    paginator = Paginator(facturas_pendientes_qs, 10) # Mostrar 10 facturas por página
    
    try:
        # 2. Obtener los objetos de la página solicitada
        facturas_pendientes_page = paginator.page(page)
    except PageNotAnInteger:
        # Si la página no es un entero, entregar la primera página.
        facturas_pendientes_page = paginator.page(1)
    except EmptyPage:
        # Si la página está fuera de rango (ej. 9999), entregar la última página de resultados.
        facturas_pendientes_page = paginator.page(paginator.num_pages)

    # Construir la cadena de parámetros de búsqueda para la navegación
    search_params = request.GET.copy()
    if 'page' in search_params:
        del search_params['page']
    search_params = search_params.urlencode()
    
    # --- Fin Lógica de Paginación ---

    # Opciones de filtro (deben seguir como están)
    anios_disponibles = Matricula.objects.values_list('AñoMatricula', flat=True).distinct().order_by('-AñoMatricula')
    niveles = Nivel.objects.filter(Activo=True).order_by('NivelID')

    context = {
        'titulo': 'Facturas Pendientes de Pago',
        # Usar el objeto de página en lugar del queryset completo
        'facturas_pendientes': facturas_pendientes_page, 
        'total_facturas_pendientes': total_facturas_pendientes,
        'anios_disponibles': anios_disponibles,
        'niveles': niveles,
        'selected_anio': selected_anio,
        'selected_nivel_id': selected_nivel_id,
        'search_params': search_params, # 👈 Parámetros de búsqueda para la paginación
    }

    return render(request, 'facturacion/consulta_facturas_pendientes.html', context)


@login_required
def consulta_facturas_pendientes_imprimir_view(request):
    """
    Genera el reporte de facturas pendientes en un formato limpio para impresión.
    """
    from decimal import Decimal
    
    selected_anio = request.GET.get('anio_lectivo')
    selected_nivel_id = request.GET.get('nivel_id')
    
    # Consulta base: Facturas activas con saldo mayor a cero
    facturas_pendientes_qs = Facturas.objects.filter(
        Activa=True, 
        Saldo__gt=Decimal('0.001')
    ).select_related(
        'EstudianteID', 
        'MatriculaID__NivelID'
    ).order_by(
        'Fecha', 
        'EstudianteID__NombreCompleto'
    )
    
    # Aplicar filtros si están presentes
    if selected_anio:
        facturas_pendientes_qs = facturas_pendientes_qs.filter(
            MatriculaID__AñoMatricula=selected_anio
        )
    
    if selected_nivel_id:
        facturas_pendientes_qs = facturas_pendientes_qs.filter(
            MatriculaID__NivelID__NivelID=selected_nivel_id
        )

    # Calcular el total global de saldo pendiente
    total_facturas_pendientes = facturas_pendientes_qs.aggregate(
        total_saldo=Sum('Saldo')
    )['total_saldo'] or Decimal(0)
    
    # Determinar los nombres de los filtros seleccionados para el encabezado
    nivel_nombre = Nivel.objects.get(NivelID=selected_nivel_id).NombreNivel if selected_nivel_id else "Todos"
    
    context = {
        'titulo': 'REPORTE DE COBRANZA: FACTURAS PENDIENTES',
        'facturas_pendientes': facturas_pendientes_qs,
        'total_facturas_pendientes': total_facturas_pendientes,
        'selected_anio': selected_anio if selected_anio else "Todos",
        'selected_nivel_nombre': nivel_nombre,
        'fecha_generacion': timezone.now(),
    }
    
    return render(request, 'facturacion/consulta_facturas_pendientes_imprimir.html', context)

@login_required
def consulta_saldos_pendientes_imprimir_view(request):
    """
    Genera el reporte de saldos pendientes por concepto para impresión.
    Reutiliza la lógica de consulta principal para garantizar consistencia.
    """

    # Filtros (igual que la vista de consulta)
    selected_anio = request.GET.get('anio_lectivo')
    selected_nivel_id = request.GET.get('nivel_id')
    selected_servicio_id = request.GET.get('servicio_id')
    
    reporte_saldos = []
    total_saldo_global = Decimal(0)
    total_facturado_global = Decimal(0)
    selected_servicio_nombre = "N/A"
    selected_nivel_nombre = "N/A"

    if selected_anio and selected_nivel_id and selected_servicio_id:
        
        try:
            servicio = Servicios.objects.get(ServicioID=selected_servicio_id)
            selected_servicio_nombre = servicio.NombreServicio
            nivel = Nivel.objects.get(NivelID=selected_nivel_id)
            selected_nivel_nombre = nivel.NombreNivel
        except (Servicios.DoesNotExist, Nivel.DoesNotExist):
            pass 

        facturas_qs = Facturas.objects.filter(
            Activa=True,
            MatriculaID__AñoMatricula=selected_anio,
            MatriculaID__NivelID__NivelID=selected_nivel_id,
        ).annotate(
            monto_pagado_servicio=Coalesce(
                Sum('detallefactura__MontoPagado', filter=Q(detallefactura__ServicioID__ServicioID=selected_servicio_id)),
                Decimal(0), output_field=DecimalField()
            ),
            monto_descuento_servicio=Coalesce(
                Sum('detallefactura__Descuento', filter=Q(detallefactura__ServicioID__ServicioID=selected_servicio_id)),
                Decimal(0), output_field=DecimalField()
            ),
            monto_facturado_servicio=Coalesce(
                Max('detallefactura__Subtotal', filter=Q(detallefactura__ServicioID__ServicioID=selected_servicio_id)),
                Decimal(0), output_field=DecimalField()
            )
        ).filter(
            monto_facturado_servicio__gt=Decimal(0) 
        ).values(
            'EstudianteID__NombreCompleto',
            'FacturaID',
            'Moneda',
            'monto_facturado_servicio',
            'monto_pagado_servicio',
            'monto_descuento_servicio'
        ).order_by('EstudianteID__NombreCompleto')
        
        
        TOLERANCIA = Decimal('0.001')
        
        for item in facturas_qs:
            monto_facturado = item['monto_facturado_servicio']
            monto_pagado = item['monto_pagado_servicio']
            monto_descuento = item['monto_descuento_servicio']
            
            monto_cubierto = monto_pagado + monto_descuento
            saldo_especifico = monto_facturado - monto_cubierto
            
            if saldo_especifico < Decimal(0):
                saldo_especifico = Decimal(0)
            
            if saldo_especifico > TOLERANCIA or monto_pagado > Decimal(0) or monto_descuento > Decimal(0):
                
                reporte_saldos.append({
                    'nombre_completo': item['EstudianteID__NombreCompleto'],
                    'moneda': item['Moneda'],
                    'monto_servicio': monto_facturado,
                    'monto_pagado': monto_pagado,
                    'monto_descuento': monto_descuento,
                    'saldo_pendiente': saldo_especifico,
                })
                total_saldo_global += saldo_especifico
                total_facturado_global += monto_facturado
                
        reporte_saldos = [r for r in reporte_saldos if r['saldo_pendiente'] > TOLERANCIA]
        reporte_saldos.sort(key=lambda x: x['saldo_pendiente'], reverse=True)


    context = {
        'titulo': f'REPORTE DE SALDOS PENDIENTES: {selected_servicio_nombre}',
        'selected_anio': selected_anio,
        'selected_nivel_nombre': selected_nivel_nombre,
        'selected_servicio_nombre': selected_servicio_nombre,
        'reporte_saldos': reporte_saldos,
        'total_saldo_global': total_saldo_global,
        'total_facturado_global': total_facturado_global,
        'fecha_generacion': timezone.now(),
    }

    return render(request, 'facturacion/consulta_saldos_pendientes_imprimir.html', context)

@login_required
def estado_cuenta_estudiante_view(request):
    nombre_estudiante = request.GET.get('nombre_estudiante', '').strip()
    anio = request.GET.get('anio')
    
    # Lista para sugerencias (Datalist)
    todos_estudiantes = Estudiantes_Nueva.objects.all().values_list('NombreCompleto', flat=True)
    anios_disponibles = Servicios.objects.values_list('Anio', flat=True).distinct().order_by('-Anio')
    
    reporte_agrupado = {}
    estudiante_encontrado = None
    info_academica = {"nivel": "N/A", "seccion": "N/A"}
    total_pagado_general = Decimal('0.00')
    total_saldo_general = Decimal('0.00')

    if nombre_estudiante and anio:
        estudiante_encontrado = Estudiantes_Nueva.objects.filter(NombreCompleto__iexact=nombre_estudiante).first()

        if estudiante_encontrado:
            detalles = DetalleFactura.objects.filter(
                FacturaID__EstudianteID=estudiante_encontrado,
                FacturaID__MatriculaID__AñoMatricula=anio,
                FacturaID__Activa=True
            ).select_related('ServicioID', 'FacturaID', 'FacturaID__MatriculaID__NivelID', 'FacturaID__MatriculaID__SeccionID')

            for d in detalles:
                # Capturamos Nivel y Sección de la matrícula de ese año específico
                if d.FacturaID.MatriculaID:
                    info_academica["nivel"] = d.FacturaID.MatriculaID.NivelID.NombreNivel
                    info_academica["seccion"] = d.FacturaID.MatriculaID.SeccionID.NombreSeccion

                key = f"{d.FacturaID.FacturaID}-{d.ServicioID.ServicioID}"
                if key not in reporte_agrupado:
                    reporte_agrupado[key] = {
                        'fecha': d.FacturaID.Fecha,
                        'factura_id': d.FacturaID.FacturaID,
                        'servicio': d.ServicioID.NombreServicio,
                        'monto_original': d.Subtotal,
                        'descuento': d.Descuento,
                        'pagado': Decimal('0.00'),
                        'recibos': []
                    }
                reporte_agrupado[key]['pagado'] += d.MontoPagado
                if d.ReciboID:
                    reporte_agrupado[key]['recibos'].append(f"R-{d.ReciboID.ReciboID}")

            for data in reporte_agrupado.values():
                data['saldo'] = data['monto_original'] - data['descuento'] - data['pagado']
                if data['saldo'] < 0.01: data['saldo'] = Decimal('0.00')
                total_pagado_general += data['pagado']
                total_saldo_general += data['saldo']

    context = {
        'titulo': 'Estado de Cuenta Individual',
        'anios': anios_disponibles,
        'todos_estudiantes': todos_estudiantes, # Para el Datalist
        'reporte': reporte_agrupado.values(),
        'estudiante_sel': estudiante_encontrado,
        'academico': info_academica,
        'nombre_buscado': nombre_estudiante,
        'anio_sel': anio,
        'total_pagado': total_pagado_general,
        'total_saldo': total_saldo_general,
    }
    return render(request, 'facturacion/reporte_estado_cuenta.html', context)

@login_required
def estado_cuenta_imprimir_view(request):
    """
    Vista optimizada para la impresión del Estado de Cuenta Individual.
    """
    nombre_estudiante = request.GET.get('nombre_estudiante', '').strip()
    anio = request.GET.get('anio')
    
    reporte_agrupado = {}
    estudiante_encontrado = None
    info_academica = {"nivel": "N/A", "seccion": "N/A"}
    total_pagado_general = Decimal('0.00')
    total_saldo_general = Decimal('0.00')

    if nombre_estudiante and anio:
        estudiante_encontrado = Estudiantes_Nueva.objects.filter(NombreCompleto__iexact=nombre_estudiante).first()

        if estudiante_encontrado:
            detalles = DetalleFactura.objects.filter(
                FacturaID__EstudianteID=estudiante_encontrado,
                FacturaID__MatriculaID__AñoMatricula=anio,
                FacturaID__Activa=True
            ).select_related('ServicioID', 'FacturaID', 'FacturaID__MatriculaID__NivelID', 'FacturaID__MatriculaID__SeccionID')

            for d in detalles:
                if d.FacturaID.MatriculaID:
                    info_academica["nivel"] = d.FacturaID.MatriculaID.NivelID.NombreNivel
                    info_academica["seccion"] = d.FacturaID.MatriculaID.SeccionID.NombreSeccion

                key = f"{d.FacturaID.FacturaID}-{d.ServicioID.ServicioID}"
                if key not in reporte_agrupado:
                    reporte_agrupado[key] = {
                        'fecha': d.FacturaID.Fecha,
                        'factura_id': d.FacturaID.FacturaID,
                        'servicio': d.ServicioID.NombreServicio,
                        'monto_original': d.Subtotal,
                        'descuento': d.Descuento,
                        'pagado': Decimal('0.00'),
                    }
                reporte_agrupado[key]['pagado'] += d.MontoPagado

            for data in reporte_agrupado.values():
                data['saldo'] = data['monto_original'] - data['descuento'] - data['pagado']
                if data['saldo'] < 0.01: data['saldo'] = Decimal('0.00')
                total_pagado_general += data['pagado']
                total_saldo_general += data['saldo']

    context = {
        'reporte': reporte_agrupado.values(),
        'estudiante_sel': estudiante_encontrado,
        'academico': info_academica,
        'anio_sel': anio,
        'total_pagado': total_pagado_general,
        'total_saldo': total_saldo_general,
        'fecha_generacion': timezone.now(),
    }
    return render(request, 'facturacion/estado_cuenta_imprimir.html', context)
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Empleado, ContratoLaboral, RegistroPlanilla, RegistroLiquidacion, HorarioEmpleado, DiaFeriado, RegistroAsistencia
from .forms import EmpleadoForm, ContratoForm, HorarioForm, DiaFeriadoForm
from contabilidad.models import MovimientoCaja, CategoriaMovimiento
from .utils import calcular_nomina_nicaragua
import datetime
from decimal import Decimal
from django.db.models import Sum
from django.http import JsonResponse
from django.db.models import Sum
from django.contrib.auth.decorators import login_required, permission_required

# 1. PANTALLA PRINCIPAL DEL MÓDULO
@login_required(login_url='/login/')
@permission_required ('recursos_humanos.ver_modulo_recursos_humanos', raise_exception=True)
def rrhh_home(request):
    total_empleados = Empleado.objects.filter(activo=True).count()
    context = {
        'total_empleados': total_empleados,
    }
    return render(request, 'recursos_humanos/rrhh_home.html', context)

# 2. LISTADO DE EMPLEADOS
def lista_empleados(request):
    hoy = datetime.date.today()
    mes_filtro = int(request.GET.get('mes', hoy.month))
    anio_filtro = int(request.GET.get('anio', hoy.year))
    
    empleados = Empleado.objects.all()
    
    # Marcamos a cada empleado si ya tiene pago este mes y año específico
    for emp in empleados:
        emp.ya_pagado = RegistroPlanilla.objects.filter(
            empleado=emp, mes=mes_filtro, anio=anio_filtro
        ).exists()
    
    return render(request, 'recursos_humanos/empleado_list.html', {
        'empleados': empleados,
        'mes_filtro': mes_filtro,
        'anio_filtro': anio_filtro,
    })


# VISTA: CREAR EMPLEADO
def crear_empleado(request):
    if request.method == 'POST':
        form_emp = EmpleadoForm(request.POST, request.FILES)
        form_con = ContratoForm(request.POST)
        
        if form_emp.is_valid() and form_con.is_valid():
            empleado = form_emp.save(commit=False)
            empleado.activo = True # Aseguramos estado activo
            empleado.save()
            
            contrato = form_con.save(commit=False)
            contrato.empleado = empleado
            contrato.save()
            
            messages.success(request, f"¡Éxito! {empleado} registrado correctamente.")
            return redirect('recursos_humanos:lista_empleados')
        else:
            messages.error(request, "Error de validación. Revise los datos (Cédula o INSS duplicados).")
    else:
        form_emp = EmpleadoForm()
        form_con = ContratoForm()
        
    return render(request, 'recursos_humanos/empleado_form.html', {
        'form_emp': form_emp, 'form_con': form_con, 'editando': False
    })

# VISTA: EDITAR EMPLEADO
def editar_empleado(request, pk):
    empleado = get_object_or_404(Empleado, pk=pk)
    contrato, created = ContratoLaboral.objects.get_or_create(empleado=empleado)

    if request.method == 'POST':
        form_emp = EmpleadoForm(request.POST, request.FILES, instance=empleado)
        form_con = ContratoForm(request.POST, instance=contrato)
        
        if form_emp.is_valid() and form_con.is_valid():
            obj_emp = form_emp.save(commit=False)
            
            # Lógica para eliminar documentos físicamente si se marcó el checkbox
            if request.POST.get('eliminar_cv') == 'on':
                obj_emp.curriculum.delete(save=False) # Borra el archivo del disco
                obj_emp.curriculum = None             # Limpia el campo en DB
                
            if request.POST.get('eliminar_diplomas') == 'on':
                obj_emp.diplomas.delete(save=False)
                obj_emp.diplomas = None
            
            obj_emp.activo = True 
            obj_emp.save()
            form_con.save()
            
            messages.success(request, f"Datos de {empleado} actualizados correctamente.")
            return redirect('recursos_humanos:lista_empleados')
        else:
            messages.error(request, "Error al actualizar. Verifique los campos.")
    else:
        form_emp = EmpleadoForm(instance=empleado)
        form_con = ContratoForm(instance=contrato)
        
    return render(request, 'recursos_humanos/empleado_form.html', {
        'form_emp': form_emp, 'form_con': form_con, 'editando': True
    })
    
def verificar_duplicados(request):
    valor = request.GET.get('valor', None)
    tipo = request.GET.get('tipo', None) # 'cedula' o 'inss'
    empleado_id = request.GET.get('empleado_id', None)

    if not valor or not tipo:
        return JsonResponse({'existe': False})

    # Buscamos en el modelo Empleado
    if tipo == 'cedula':
        queryset = Empleado.objects.filter(cedula=valor)
    else:
        queryset = Empleado.objects.filter(numero_inss=valor)

    # Si estamos editando, excluimos al empleado actual
    if empleado_id:
        queryset = queryset.exclude(pk=empleado_id)

    return JsonResponse({'existe': queryset.exists()})

# VISTA PARA VER EXPEDIENTE (SOLO LECTURA)
def expediente_empleado(request, pk):
    empleado = get_object_or_404(Empleado, pk=pk)
    return render(request, 'recursos_humanos/empleado_expediente.html', {
        'empleado': empleado
    })
    
    
def imprimir_contrato(request, pk):
    """
    Vista para visualizar el contrato legal en formato de impresión.
    """
    empleado = get_object_or_404(Empleado, pk=pk)
    # Verificamos que tenga datos salariales configurados
    contrato = getattr(empleado, 'contrato', None)
    
    if not contrato:
        messages.error(request, "Este empleado no tiene información salarial configurada.")
        return redirect('recursos_humanos:expediente_empleado', pk=pk)

    return render(request, 'recursos_humanos/contrato_imprimible.html', {
        'empleado': empleado,
        'contrato': contrato,
        'fecha_hoy': datetime.date.today() # Necesitarás importar datetime
    })
    

def generar_pago_mes(request, empleado_id):
    empleado = get_object_or_404(Empleado, pk=empleado_id)
    contrato = empleado.contrato
    hoy = datetime.date.today()
    
    # Período seleccionado
    mes = int(request.GET.get('mes', hoy.month))
    anio = int(request.GET.get('anio', hoy.year))

    # Bloqueo de seguridad: No se puede pagar a alguien Inactivo si no tiene ya un pago guardado en ese mes
    pago_existente = RegistroPlanilla.objects.filter(
        empleado=empleado, mes=mes, anio=anio
    ).first()

    if not empleado.activo and not pago_existente:
        messages.error(request, f"Error: {empleado} se encuentra INACTIVO. No se puede generar nueva planilla.")
        return redirect('recursos_humanos:lista_empleados')

    # Parámetro para saltar la colilla y mostrar el formulario de edición
    forzar_edicion = request.GET.get('forzar_edicion') == '1'

    # Si ya existe el pago y NO pedimos editar, mostramos la colilla
    if pago_existente and request.method == 'GET' and not forzar_edicion:
        return render(request, 'recursos_humanos/detalle_pago.html', {'pago': pago_existente})

    if request.method == 'POST':
        # 1. Capturar datos del formulario
        cant_horas = Decimal(request.POST.get('horas_extras_cantidad', '0') or '0')
        valor_hora_input = Decimal(request.POST.get('horas_extras_valor_pago', '0') or '0')
        otras_deducciones_input = Decimal(request.POST.get('otras_deducciones', '0') or '0')
        tipo_periodo_input = request.POST.get('tipo_periodo', 'MENSUAL')
        dias_trabajados_input = Decimal(request.POST.get('dias_trabajados', '30.0') or '30.0')
        mes_input = int(request.POST.get('mes_pago', mes))
        anio_input = int(request.POST.get('anio_pago', anio))

        # 1.5 Obtener Multas de Asistencia acumuladas en el periodo
        # Si el periodo es mensual, buscamos todo el mes.
        total_multas_asistencia = RegistroAsistencia.objects.filter(
            empleado=empleado, 
            fecha__month=mes_input, 
            fecha__year=anio_input
        ).aggregate(total=Sum('multa_monto'))['total'] or Decimal('0')
        
        # 2. Cálculos base (Prorrateo)
        valor_dia = contrato.salario_base / Decimal('30')
        salario_proporcional = valor_dia * dias_trabajados_input
        
        monto_extras = cant_horas * valor_hora_input
        antiguedad_monto = salario_proporcional * (Decimal(contrato.porcentaje_antiguedad or 0) / 100)
        
        # 3. Calcular el Total Devengado
        total_devengado = salario_proporcional + antiguedad_monto + monto_extras
        
        # 4. Calcular deducciones de ley (INSS e IR acorde al periodo)
        calculos = calcular_nomina_nicaragua(
            salario_bruto=total_devengado,
            incluye_inss=contrato.paga_inss,
            incluye_ir=contrato.paga_ir,
            tipo_periodo=tipo_periodo_input
        )
        
        # 5. Guardar o Actualizar
        pago, created = RegistroPlanilla.objects.update_or_create(
            empleado=empleado, 
            mes=mes_input, 
            anio=anio_input,
            defaults={
                'tipo_periodo': tipo_periodo_input,
                'dias_trabajados': dias_trabajados_input,
                'salario_basico': salario_proporcional,
                'horas_extras_cantidad': cant_horas,
                'horas_extras_valor_pago': valor_hora_input,
                'horas_extras_monto': monto_extras,
                'monto_antiguedad': antiguedad_monto,
                'total_devengado': total_devengado, # <--- Fix del error
                'inss_laboral': calculos['inss_laboral'],
                'ir_mensual': calculos['ir_mensual'],
                'otras_deducciones': otras_deducciones_input,
                'inss_patronal': calculos['inss_patronal'],
                'inatec': calculos['inatec'],
                'total_a_pagar': calculos['salario_neto'] - otras_deducciones_input - total_multas_asistencia,
                'creado_por': request.user
            }
        )
        # Una vez guardado, mostramos el comprobante con un mensaje de éxito
        return render(request, 'recursos_humanos/detalle_pago.html', {
            'pago': pago,
            'editado': True if not created else False
        })

    # Lógica para GET (Formulario de entrada)
    valor_hora_ley = (contrato.salario_base / Decimal('30') / Decimal('8')) * Decimal('2')
    
    context = {
        'empleado': empleado,
        'mes_filtro': mes,
        'anio_filtro': anio,
        'valor_hora_ley': round(valor_hora_ley, 2),
        'pago_actual': pago_existente # Para cargar valores previos si estamos editando
    }

    return render(request, 'recursos_humanos/ingresar_extras.html', context)

def nomina_general_mes(request):
    hoy = datetime.date.today()
    # Capturar mes y año de los filtros GET, o usar el actual por defecto
    mes = int(request.GET.get('mes', hoy.month))
    anio = int(request.GET.get('anio', hoy.year))
    
    # Obtenemos todos los registros de planilla ya generados para este mes/año
    nominas = RegistroPlanilla.objects.filter(mes=mes, anio=anio).select_related('empleado')
    
    # Calculamos los totales generales para el resumen al pie de tabla
    totales = nominas.aggregate(
        total_devengado=Sum('total_devengado'),
        total_inss=Sum('inss_laboral'),
        total_ir=Sum('ir_mensual'),
        total_neto=Sum('total_a_pagar')
    )
    
    return render(request, 'recursos_humanos/nomina_general.html', {
        'nominas': nominas,
        'mes_actual': mes,
        'anio_actual': anio,
        'totales': totales,
        'meses_lista': [
            (1, 'Enero'), (2, 'Febrero'), (3, 'Marzo'), (4, 'Abril'),
            (5, 'Mayo'), (6, 'Junio'), (7, 'Julio'), (8, 'Agosto'),
            (9, 'Septiembre'), (10, 'Octubre'), (11, 'Noviembre'), (12, 'Diciembre')
        ],
        'anios_lista': range(hoy.year - 2, hoy.year + 2)
    })

# ==============================================================
#                 CONTROL DE ASISTENCIA (KIOSKO)
# ==============================================================
@login_required
def imprimir_nomina_general(request):
    hoy = datetime.date.today()
    mes = int(request.GET.get('mes', hoy.month))
    anio = int(request.GET.get('anio', hoy.year))
    
    nominas = RegistroPlanilla.objects.filter(mes=mes, anio=anio).select_related('empleado')
    totales = nominas.aggregate(
        total_devengado=Sum('total_devengado'),
        total_inss=Sum('inss_laboral'),
        total_ir=Sum('ir_mensual'),
        total_neto=Sum('total_a_pagar')
    )
    
    # Obtener nombre del mes
    meses_nombres = {
        1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril', 5: 'Mayo', 6: 'Junio',
        7: 'Julio', 8: 'Agosto', 9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
    }
    
    return render(request, 'recursos_humanos/nomina_general_print.html', {
        'nominas': nominas,
        'mes_nombre': meses_nombres.get(mes),
        'anio': anio,
        'totales': totales,
        'hoy': hoy
    })

@login_required
def kiosko_asistencia_view(request):
    """
    Vista de pantalla completa para dejar corriendo en recepción/portería.
    Muestra la hora y escucha silenciosamente al escaner de código de barras.
    """
    return render(request, 'recursos_humanos/kiosko_asistencia.html', {
        'titulo': 'Control de Asistencia Biométrico'
    })

import re
from django.db.models import Q
from django.utils import timezone
from .models import RegistroAsistencia

@login_required
def api_marcar_asistencia(request):
    if request.method == 'POST':
        raw_code = request.POST.get('raw_code', '').strip()
        if not raw_code:
            return JsonResponse({"success": False, "error": "Código vacío."})

        # Extraer cédula nicaragüense (PDF-417 y variantes en MRZ)
        # Buscar 3 digitos, 6 digitos, 4 digitos y 1 letra.
        match = re.search(r'(\d{3})[-<]*(\d{6})[-<]*(\d{4}[A-Za-z])', raw_code)
        if not match:
            return JsonResponse({
                "success": False, 
                "error": "El formato del código no contiene una Cédula Nicaragüense válida."
            })

        # Reconstruir hipotéticos guardados en la BD (con guiones y plano)
        c_p1, c_p2, c_p3 = match.group(1), match.group(2), match.group(3)
        cedula_format = f"{c_p1}-{c_p2}-{c_p3}".upper()
        cedula_flat = f"{c_p1}{c_p2}{c_p3}".upper()
        
        empleado = Empleado.objects.filter(
            Q(cedula__iexact=cedula_format) | Q(cedula__iexact=cedula_flat)
        ).first()

        if not empleado:
            return JsonResponse({
                "success": False, 
                "error": f"Cédula {cedula_format} leída correctamente, pero no existe en el sistema."
            })

        if not empleado.activo:
            return JsonResponse({
                "success": False, 
                "error": f"El empleado {empleado.nombres} está inactivo."
            })

        hoy = timezone.now().date()
        ahora = timezone.now().time()
        
        # Obtener horario del empleado
        horario = getattr(empleado, 'horario', None)
        
        registro, created = RegistroAsistencia.objects.get_or_create(
            empleado=empleado,
            fecha=hoy,
            defaults={'hora_entrada': ahora}
        )

        accion = ""
        hora_str = ahora.strftime('%I:%M %p')
        extra_info = ""

        if created:
            # --- Lógica de Entrada (Tardanzas) ---
            accion = "ENTRADA"
            msg = f"Entrada marcada a las {hora_str}"
            
            if horario:
                # Convertir a datetime para poder restar
                dt_ahora = datetime.datetime.combine(hoy, ahora)
                dt_entrada_esperada = datetime.datetime.combine(hoy, horario.entrada_esperada)
                
                # Sumar margen de tolerancia
                dt_limite = dt_entrada_esperada + datetime.timedelta(minutes=horario.minutos_tolerancia)
                
                if dt_ahora > dt_limite and not horario.es_flexible:
                    tardanza_delta = dt_ahora - dt_entrada_esperada
                    minutos_tarde = int(tardanza_delta.total_seconds() / 60)
                    registro.minutos_tarde = minutos_tarde
                    registro.save()
                    extra_info = f" (Tardanza: {minutos_tarde} min)"
                    msg += extra_info
                elif horario.es_flexible:
                    extra_info = " (Horario Flexible)"
                    msg += extra_info
        else:
            # --- Lógica de Salida (Salidas Tempranas) ---
            if not registro.hora_salida:
                registro.hora_salida = ahora
                
                if horario:
                    dt_ahora = datetime.datetime.combine(hoy, ahora)
                    dt_salida_esperada = datetime.datetime.combine(hoy, horario.salida_esperada)
                    
                    if dt_ahora < dt_salida_esperada:
                        temprano_delta = dt_salida_esperada - dt_ahora
                        minutos_temprano = int(temprano_delta.total_seconds() / 60)
                        registro.minutos_temprano = minutos_temprano
                        extra_info = f" (Salida Anticipada: {minutos_temprano} min)"
                
                registro.save()
                accion = "SALIDA"
                msg = f"Salida marcada a las {hora_str}{extra_info}"
            else:
                accion = "ERROR"
                msg = f"Ya registraste tu Entrada y Salida hoy."

        # Retornamos el JSON para la animación frontend
        return JsonResponse({
            "success": accion != "ERROR",
            "accion": accion,
            "message": msg,
            "empleado": f"{empleado.nombres} {empleado.apellidos}",
            "cargo": empleado.cargo,
        })
    
    return JsonResponse({"success": False, "error": "Método no permitido."})

# --- Integración con Contabilidad ---

@login_required
def contabilizar_pago_planilla(request, pk):
    pago = get_object_or_404(RegistroPlanilla, pk=pk)
    if pago.contabilizado:
        messages.warning(request, "Este pago ya fue registrado en contabilidad.")
        return redirect('recursos_humanos:nomina_general')

    # 1. Obtener o crear la categoría de egreso
    categoria, created = CategoriaMovimiento.objects.get_or_create(
        nombre='PAGO DE PLANILLA',
        defaults={'tipo': 'EGRESO', 'activo': True}
    )

    # 2. Crear el movimiento de caja
    MovimientoCaja.objects.create(
        categoria=categoria,
        descripcion=f"Pago de Planilla {pago.mes}/{pago.anio} - {pago.empleado}",
        monto=pago.total_a_pagar,
        comprobante=f"PLN-{pago.pk}",
        usuario=request.user
    )

    # 3. Marcar como contabilizado
    pago.contabilizado = True
    pago.save()

    messages.success(request, f"Pago de {pago.empleado} contabilizado exitosamente.")
    return redirect('recursos_humanos:nomina_general')

@login_required
def contabilizar_liquidacion(request, pk):
    empleado = get_object_or_404(Empleado, pk=pk)
    try:
        liquidacion = empleado.registroliquidacion
    except RegistroLiquidacion.DoesNotExist:
        messages.error(request, "No se encontró la liquidación.")
        return redirect('recursos_humanos:expediente_empleado', pk=empleado.pk)

    if liquidacion.contabilizado:
        messages.warning(request, "Esta liquidación ya fue registrada en contabilidad.")
        return redirect('recursos_humanos:expediente_empleado', pk=empleado.pk)

    # 1. Obtener o crear la categoría de egreso
    categoria, created = CategoriaMovimiento.objects.get_or_create(
        nombre='LIQUIDACIONES LABORALES',
        defaults={'tipo': 'EGRESO', 'activo': True}
    )

    # 2. Crear el movimiento de caja
    MovimientoCaja.objects.create(
        categoria=categoria,
        descripcion=f"Liquidación Final - {empleado}",
        monto=liquidacion.monto_total_liquidado,
        comprobante=f"LIQ-{liquidacion.pk}",
        usuario=request.user
    )

    # 3. Marcar como contabilizado
    liquidacion.contabilizado = True
    liquidacion.save()

    messages.success(request, f"Liquidación de {empleado} contabilizada exitosamente.")
    return redirect('recursos_humanos:expediente_empleado', pk=empleado.pk)

# --- Gestión de Asistencia y Horarios ---

@login_required
def gestion_asistencia(request):
    hoy = timezone.now().date()
    # Estadísticas básicas
    total_empleados = Empleado.objects.filter(activo=True).count()
    presentes_hoy = RegistroAsistencia.objects.filter(fecha=hoy).count()
    tardanzas_hoy = RegistroAsistencia.objects.filter(fecha=hoy, minutos_tarde__gt=0).count()
    
    # Listados
    asistencias_hoy = RegistroAsistencia.objects.filter(fecha=hoy).order_by('-hora_entrada')
    feriados = DiaFeriado.objects.all().order_by('-fecha')[:10]
    
    return render(request, 'recursos_humanos/gestion_asistencia.html', {
        'asistencias': asistencias_hoy,
        'feriados': feriados,
        'stats': {
            'total': total_empleados,
            'presentes': presentes_hoy,
            'tardanzas': tardanzas_hoy,
            'ausentes': total_empleados - presentes_hoy
        }
    })

@login_required
def configurar_horario(request, pk):
    empleado = get_object_or_404(Empleado, pk=pk)
    horario, created = HorarioEmpleado.objects.get_or_create(empleado=empleado)
    
    if request.method == 'POST':
        form = HorarioForm(request.POST, instance=horario)
        if form.is_valid():
            form.save()
            messages.success(request, f"Horario actualizado para {empleado}")
            return redirect('recursos_humanos:expediente_empleado', pk=pk)
    else:
        form = HorarioForm(instance=horario)
        
    return render(request, 'recursos_humanos/configurar_horario.html', {
        'form': form,
        'empleado': empleado
    })

@login_required
def registrar_feriado(request):
    if request.method == 'POST':
        form = DiaFeriadoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Día feriado registrado correctamente.")
    return redirect('recursos_humanos:gestion_asistencia')

@login_required
def eliminar_feriado(request, pk):
    feriado = get_object_or_404(DiaFeriado, pk=pk)
    feriado.delete()
    messages.success(request, "Feriado eliminado.")
    return redirect('recursos_humanos:gestion_asistencia')

@login_required
def aplicar_multa(request, pk):
    """Aplica un castigo manual a un registro de asistencia."""
    registro = get_object_or_404(RegistroAsistencia, pk=pk)
    if request.method == 'POST':
        monto = Decimal(request.POST.get('monto', '0'))
        nota = request.POST.get('observaciones', '')
        
        registro.multa_monto = monto
        if nota:
            registro.observaciones = (registro.observaciones or "") + f" | Castigo: {nota}"
        registro.save()
        messages.success(request, f"Castigo de C$ {monto} aplicado a {registro.empleado}.")
    
    return redirect('recursos_humanos:gestion_asistencia')

# ==============================================================
#                  MÓDULO DE LIQUIDACIONES (FINIQUITOS)
# ==============================================================
from .models import RegistroLiquidacion
from .utils import calcular_liquidacion_nicaragua

@login_required(login_url='/login/')
@permission_required('recursos_humanos.ver_modulo_recursos_humanos', raise_exception=True)
def liquidar_empleado(request, pk):
    empleado = get_object_or_404(Empleado, pk=pk)
    
    # Redirigir si ya fue liquidado
    if hasattr(empleado, 'registroliquidacion') or not empleado.activo:
        messages.warning(request, "Este empleado ya fue liquidado/inactivado.")
        return redirect('recursos_humanos:expediente_empleado', pk=empleado.pk)

    if request.method == 'POST':
        fecha_salida_str = request.POST.get('fecha_salida')
        motivo = request.POST.get('motivo')
        salario_base = Decimal(request.POST.get('salario_base_calculo', '0'))
        
        anos_antiguedad = Decimal(request.POST.get('anos_antiguedad', '0'))
        meses_vacaciones = Decimal(request.POST.get('meses_vacaciones', '0'))
        meses_aguinaldo = Decimal(request.POST.get('meses_aguinaldo', '0'))
        
        fecha_salida = datetime.datetime.strptime(fecha_salida_str, "%Y-%m-%d").date()
        pierde_indemnizacion = (motivo == 'RENUNCIA_INMEDIATA')

        # 1. Enviar al motor contable (utils.py)
        resultados = calcular_liquidacion_nicaragua(
            salario_mensual=salario_base,
            anos_antiguedad=anos_antiguedad,
            meses_vacaciones=meses_vacaciones,
            meses_aguinaldo=meses_aguinaldo,
            pierde_indemnizacion=pierde_indemnizacion
        )
        
        # 2. Guardar el Registro de Liquidación en la Base de Datos
        liquidacion = RegistroLiquidacion.objects.create(
            empleado=empleado,
            fecha_salida=fecha_salida,
            motivo=motivo,
            salario_base_calculo=salario_base,
            aguinaldo_proporcional=resultados['aguinaldo'],
            vacaciones_proporcionales=resultados['vacaciones'],
            indemnizacion_antiguedad=resultados['indemnizacion'],
            monto_total_liquidado=resultados['total'],
            creado_por=request.user
        )
        
        # 3. Desactivar al Empleado formalmente (Cesantía)
        empleado.activo = False
        empleado.save()
        
        messages.success(request, f"¡Liquidación procesada! {empleado.nombres} ha sido dado de baja.")
        return redirect('recursos_humanos:imprimir_finiquito', pk=empleado.pk)

    # Lógica GET: Pre-cálculos sugeridos para ayudar a RRHH
    # a. Años de Antigüedad
    hoy = datetime.date.today()
    delta = hoy - empleado.fecha_contratacion
    anos_sugeridos = round(delta.days / 365.25, 2)
    if anos_sugeridos < 0: anos_sugeridos = 0
    
    # b. Meses desde su último Diciembre para el Aguinaldo
    ultimo_diciembre = datetime.date(hoy.year - 1 if hoy.month < 12 else hoy.year, 12, 1)
    if empleado.fecha_contratacion > ultimo_diciembre:
        ultimo_diciembre = empleado.fecha_contratacion
    meses_aguinaldo_sugeridos = round((hoy - ultimo_diciembre).days / 30.4, 2)
    if meses_aguinaldo_sugeridos < 0: meses_aguinaldo_sugeridos = 0
        
    context = {
        'empleado': empleado,
        'salario_base': empleado.contrato.salario_base if hasattr(empleado, 'contrato') else 0,
        'hoy': hoy.strftime("%Y-%m-%d"),
        'anos_sugeridos': anos_sugeridos,
        'meses_aguinaldo_sugeridos': meses_aguinaldo_sugeridos
    }
    
    return render(request, 'recursos_humanos/liquidar_empleado.html', context)

@login_required(login_url='/login/')
def imprimir_finiquito(request, pk):
    empleado = get_object_or_404(Empleado, pk=pk)
    
    try:
        liquidacion = empleado.registroliquidacion
    except RegistroLiquidacion.DoesNotExist:
        messages.error(request, "Este empleado no tiene una liquidación procesada.")
        return redirect('recursos_humanos:expediente_empleado', pk=empleado.pk)
        
    return render(request, 'recursos_humanos/imprimir_finiquito_print.html', {
        'empleado': empleado,
        'liquidacion': liquidacion,
        'hoy': datetime.date.today()
    })
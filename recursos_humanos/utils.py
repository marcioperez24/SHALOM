from decimal import Decimal

def calcular_ir_nicaragua(ingreso_anual_gravable):
    """
    Calcula el IR según la tabla de la DGI de Nicaragua.
    Ingreso gravable = (Total Devengado - INSS) * 12 meses.
    """
    # Escalas DGI
    if ingreso_anual_gravable <= 100000:
        return Decimal(0)
    elif ingreso_anual_gravable <= 200000:
        return (ingreso_anual_gravable - 100000) * Decimal('0.15')
    elif ingreso_anual_gravable <= 350000:
        return ((ingreso_anual_gravable - 200000) * Decimal('0.20')) + 15000
    elif ingreso_anual_gravable <= 500000:
        return ((ingreso_anual_gravable - 350000) * Decimal('0.25')) + 45000
    else:
        return ((ingreso_anual_gravable - 500000) * Decimal('0.30')) + 82500




def calcular_nomina_nicaragua(salario_bruto, incluye_inss=True, incluye_ir=True, tipo_periodo='MENSUAL'):
    """
    Realiza los cálculos de deducciones para un empleado en Nicaragua.
    Soporta periodos mensuales y quincenales.
    """
    res = {
        'inss_laboral': 0,
        'ir_mensual': 0,
        'total_deducciones': 0,
        'salario_neto': 0
    }
    
    monto_bruto = float(salario_bruto)
    
    # 1. INSS Laboral (7%)
    if incluye_inss:
        res['inss_laboral'] = round(monto_bruto * 0.07, 2)
    
    # 2. Base imponible para el IR (Bruto - INSS)
    base_imponible = monto_bruto - res['inss_laboral']
    
    # 3. Cálculo del IR (Progresivo DGI)
    if incluye_ir:
        # Multiplicador según el tipo de periodo de la nómina
        multiplicador = 24 if 'QUINCENA' in tipo_periodo else 12
        proyeccion_anual = base_imponible * multiplicador
        ir_anual = 0
        
        if proyeccion_anual <= 100000:
            ir_anual = 0
        elif proyeccion_anual <= 200000:
            ir_anual = (proyeccion_anual - 100000) * 0.15
        elif proyeccion_anual <= 350000:
            ir_anual = ((proyeccion_anual - 200000) * 0.20) + 15000
        elif proyeccion_anual <= 500000:
            ir_anual = ((proyeccion_anual - 350000) * 0.25) + 45000
        else:
            ir_anual = ((proyeccion_anual - 500000) * 0.30) + 82500
            
        res['ir_mensual'] = round(ir_anual / multiplicador, 2)
    
    # Aportes Patronales (Costos ocultos de la empresa)
    if incluye_inss:
        res['inss_patronal'] = round(monto_bruto * 0.225, 2)
        res['inatec'] = round(monto_bruto * 0.02, 2)
    else:
        res['inss_patronal'] = 0
        res['inatec'] = 0

    res['total_deducciones'] = round(res['inss_laboral'] + res['ir_mensual'], 2)
    res['salario_neto'] = round(monto_bruto - res['total_deducciones'], 2)
    
    return res

def calcular_liquidacion_nicaragua(salario_mensual, anos_antiguedad, meses_vacaciones, meses_aguinaldo, pierde_indemnizacion):
    """
    Calcula el finiquito laboral según los Artículos 44, 45, 76 y 93 del Código del Trabajo.
    """
    sal_mensual = Decimal(str(salario_mensual))
    anos = Decimal(str(anos_antiguedad))
    m_vac = Decimal(str(meses_vacaciones))
    m_agui = Decimal(str(meses_aguinaldo))
    
    salario_diario = sal_mensual / Decimal('30')
    
    # 1. Aguinaldo Proporcional (Treceavo Mes - Art. 93)
    # Se gana 1 doceavo del salario mensual por cada mes trabajado
    aguinaldo = (sal_mensual / Decimal('12')) * m_agui
    
    # 2. Vacaciones Proporcionales (Art. 76)
    # Son 2.5 días por mes => 30 días al año => Igual a 1 mes de salario al año
    vacaciones = (sal_mensual / Decimal('12')) * m_vac
    
    # 3. Indemnización por Años de Servicio (Art. 45 y Art. 44)
    indemnizacion = Decimal('0')
    if not pierde_indemnizacion:
        if anos <= Decimal('3'):
            # Primeros 3 años: 1 mes de salario por cada año
            indemnizacion = anos * sal_mensual
        elif anos <= Decimal('6'):
            # Del 4to al 6to año: 20 días por cada año adicional
            indemnizacion = (Decimal('3') * sal_mensual) + ((anos - Decimal('3')) * (Decimal('20') * salario_diario))
        else:
            # Tope máximo de ley: 5 meses (Salvo convenio diferente, pero por ley son 5)
            indemnizacion = Decimal('5') * sal_mensual

    return {
        'aguinaldo': round(aguinaldo, 2),
        'vacaciones': round(vacaciones, 2),
        'indemnizacion': round(indemnizacion, 2),
        'total': round(aguinaldo + vacaciones + indemnizacion, 2)
    }
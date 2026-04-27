from django.shortcuts import render
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import timedelta
from facturacion.models import Facturas, Recibo, Arqueos 
from Matricula.models import Estudiantes_Nueva, Matricula

def dashboard_indicadores(request):
    hoy = timezone.now().date()
    hace_una_semana = hoy - timedelta(days=6)
    
    # 1. KPIs Principales
    total_estudiantes = Estudiantes_Nueva.objects.filter(activo=True).count()
    
    # --- SOLUCIÓN PARA LA TARJETA VERDE ---
    # Usamos MontoCalculado_Cordobas de la tabla Arqueos
    ingresos_query = Arqueos.objects.filter(
        Fecha=hoy, 
        Activa=True
    ).aggregate(total=Sum('MontoCalculado_Cordobas'))['total']
    
    ingresos_hoy = ingresos_query if ingresos_query else 0.00
    # ---------------------------------------
    
    total_matriculas = Matricula.objects.filter(AñoMatricula=hoy.year).count()
    facturas_pendientes = Facturas.objects.filter(Activa=True, Estado='Pendiente').count()

    # --- GRÁFICOS (Volvemos a la lógica original que sí te funcionaba) ---
    estados_data = Facturas.objects.filter(Activa=True).values('Estado').annotate(total=Count('Estado'))
    
    grados_data = Matricula.objects.filter(AñoMatricula=hoy.year)\
        .values('NivelID__NombreNivel')\
        .annotate(total=Count('EstudianteID'))\
        .order_by('-total')

    # Gráfico 3: Volvemos a usar Recibo para no dañar el gráfico de líneas
    ingresos_semana = Recibo.objects.filter(
        FechaPago__range=[hace_una_semana, hoy],
        Estado='Pagado'
    ).values('FechaPago').annotate(total=Sum('MontoPagado')).order_by('FechaPago')

    # --- TABLAS RECIENTES ---
    ultimos_recibos = Recibo.objects.select_related('FacturaID__EstudianteID').order_by('-ReciboID')[:7]

    # Mantenemos la relación para que salga el Nivel en la lista
    estudiantes_recientes = Estudiantes_Nueva.objects.filter(activo=True).values(
        'NombreCompleto', 
        'Codigo_MINED', 
        'matricula__NivelID__NombreNivel' 
    ).order_by('-EstudianteID')[:7]

    context = {
        'total_estudiantes': total_estudiantes,
        'ingresos_hoy': ingresos_hoy,
        'total_matriculas': total_matriculas,
        'facturas_pendientes': facturas_pendientes,
        'ultimos_recibos': ultimos_recibos,
        'estudiantes_recientes': estudiantes_recientes,
        'estados_data': estados_data,
        'grados_data': grados_data,
        'ingresos_semana': ingresos_semana,
    }
    
    return render(request, 'dashboard/dashboard.html', context)
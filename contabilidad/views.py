from django.shortcuts import render, redirect
from django.contrib import messages
from .models import MovimientoCaja
from .forms import MovimientoForm  # Asegúrate de haber creado forms.py
from django.db.models import Sum
from django.contrib.auth.decorators import login_required, permission_required


@login_required(login_url='/login/')
@permission_required ('contabilidad.ver_modulo_Contabilidad', raise_exception=True)
def contabilidad_home(request):
    return render(request, 'contabilidad/contabilidad_home.html')

def listado_movimientos(request):
    movimientos = MovimientoCaja.objects.all().order_by('-fecha')
    
    total_ingresos = movimientos.filter(categoria__tipo='INGRESO').aggregate(Sum('monto'))['monto__sum'] or 0
    total_egresos = movimientos.filter(categoria__tipo='EGRESO').aggregate(Sum('monto'))['monto__sum'] or 0
    balance = total_ingresos - total_egresos

    context = {
        'movimientos': movimientos,
        'total_ingresos': total_ingresos,
        'total_egresos': total_egresos,
        'balance': balance,
    }
    return render(request, 'contabilidad/listado_movimientos.html', context)

def registrar_movimiento(request):
    """Vista para procesar el formulario de nuevo ingreso/egreso"""
    if request.method == 'POST':
        form = MovimientoForm(request.POST)
        if form.is_valid():
            movimiento = form.save(commit=False)
            movimiento.usuario = request.user # Registramos quién hizo el movimiento
            movimiento.save()
            messages.success(request, f"Se registró el movimiento: {movimiento.categoria.nombre}")
            return redirect('contabilidad:listado_movimientos')
    else:
        form = MovimientoForm()
    
    return render(request, 'contabilidad/form_movimiento.html', {'form': form})
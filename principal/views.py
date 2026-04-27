# principal/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def home_splash_view(request):
    """
    Función de entrada principal (ruta /). 
    Renderiza la página de bienvenida (splash_logo) para todos los usuarios.
    """
    return render(request, 'principal/splash_logo.html')
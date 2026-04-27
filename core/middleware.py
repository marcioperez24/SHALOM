from django.shortcuts import redirect
from django.urls import reverse
from configuracion.models import Licencia 
from django.conf import settings
from django.contrib import messages
from django.utils import timezone

class LicenciaMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # 1. Rutas críticas
        DASHBOARD_URL = reverse('dashboard') 
        ADMIN_LICENCIA_URL = reverse('configuracion:administrar_licencia')
        LICENCIA_VENCIDA_URL = reverse('configuracion:licencia_vencida') 
        
        # Rutas exceptuadas de revisión
        EXCLUIDAS_GENERAL = [reverse('login'), reverse('logout'), reverse('home'), LICENCIA_VENCIDA_URL]
        
        current_path = request.path
        if '?' in current_path:
            current_path = current_path.split('?')[0]

        # Omitir archivos estáticos, media y rutas de login
        if current_path.startswith(settings.STATIC_URL) or \
           current_path.startswith(settings.MEDIA_URL) or \
           current_path in EXCLUIDAS_GENERAL:
            return self.get_response(request)
        
        # Si no está autenticado, Django manejará el login normal
        if not request.user.is_authenticated:
            return self.get_response(request)

        # --- VERIFICACIÓN DE LICENCIA ---
        licencia = Licencia.obtener_licencia_actual()
        
        if not licencia.es_valida():
            # A. CASO SUPERUSUARIO: Solo puede estar en Administrar Licencia
            if request.user.is_superuser:
                if current_path == ADMIN_LICENCIA_URL:
                    return self.get_response(request)
                return redirect(ADMIN_LICENCIA_URL)
            
            # B. CASO USUARIO NORMAL: Puede ver el Dashboard, pero nada más
            else:
                # Permitimos que vea el Dashboard (Splash)
                if current_path == DASHBOARD_URL:
                    # Pasamos una variable de sesión para que el base.html sepa que debe bloquear botones
                    request.session['licencia_vencida_bloqueo'] = True
                    return self.get_response(request)
                
                # Si intenta ir a cualquier otra ruta (Matrícula, Facturación, etc.) -> Bloqueo
                return redirect(LICENCIA_VENCIDA_URL)

        # --- LICENCIA VÁLIDA ---
        # Limpiar banderas de bloqueo si la licencia ya es válida
        if 'licencia_vencida_bloqueo' in request.session:
            del request.session['licencia_vencida_bloqueo']

        # Aviso de caducidad (Solo una vez por sesión)
        if not request.session.get('licencia_avisada', False):
            dias_restantes = (licencia.fecha_caducidad - timezone.now().date()).days
            if 0 <= dias_restantes <= 7:
                messages.warning(request, f"¡AVISO! La licencia caducará en {dias_restantes} días.")
                request.session['licencia_avisada'] = True

        return self.get_response(request)
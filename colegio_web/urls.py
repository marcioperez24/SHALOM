"""
URL configuration for colegio_web project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from principal.views import home_splash_view 
# IMPORTAMOS LA VISTA REAL DEL DASHBOARD (dashboard_indicadores)
from dashboard.views import dashboard_indicadores 

urlpatterns = [
    path('', home_splash_view, name='home'), 
    path('admin/', admin.site.urls),
    path('login/', auth_views.LoginView.as_view(template_name='principal/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(template_name='principal/logged_out.html'), name='logout'),
    path('dashboard/', dashboard_indicadores, name='dashboard'), 
    path('configuracion/', include('configuracion.urls')), # Tu configuración en /configuracion/
    path('matricula/', include('Matricula.urls')),
    path('inventario/', include('inventario.urls')),
    path('reportes/', include('reportes.urls')), 
    path('facturacion/', include('facturacion.urls')),  
    path('gestion/', include('gestion_permisos.urls')),
    path('docentes/', include('docentes.urls')),
    path('contabilidad/', include('contabilidad.urls')),
    path('rrhh/', include('recursos_humanos.urls')),

]
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    

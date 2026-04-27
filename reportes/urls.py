# En el archivo 'reportes/urls.py'
from django.urls import path
from . import views

app_name = 'reportes'

urlpatterns = [
    path('', views.reportes_home, name='reportes_home'),
    path('estudiantes/', views.reporte_estudiantes_view, name='reporte_estudiantes'),
    
    # 🌟 NUEVA URL para la llamada AJAX que filtra las secciones
    path('ajax/get_secciones/', views.get_secciones_por_nivel, name='ajax_get_secciones'),
    
    # URL para imprimir un solo estudiante
    path('estudiantes/imprimir/<int:estudiante_id>/', views.imprimir_reporte_estudiante_view, name='imprimir_reporte_estudiante'),
    # URL para imprimir todos los estudiantes de la tabla filtrada
    path('estudiantes/imprimir/todos/', views.imprimir_reporte_completo_view, name='imprimir_reporte_completo'),
    # Nueva URL para exportar a Excel (CSV)
    path('estudiantes/exportar/', views.exportar_estudiantes_excel_view, name='exportar_estudiantes'),
]
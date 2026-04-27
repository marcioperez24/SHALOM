from django.urls import path
from . import views

urlpatterns = [
    path('', views.docentes_home, name='docentes_home'),
    path('acceso/', views.acceso_docente, name='acceso_docente'),
    path('panel/', views.panel_docente, name='panel_docente'),
    path('notas/ingresar/<int:carga_id>/', views.gestion_notas, name='gestion_notas'),
    path('notas/imprimir/<int:carga_id>/', views.imprimir_acta_notas, name='imprimir_acta_notas'),
    path('notas/archivar/<int:carga_id>/', views.archivar_acta_digital, name='archivar_acta_digital'),
    
    path('registrar/', views.registrar_docente, name='registrar_docente'),
    
    path('lista/', views.lista_docentes, name='lista_docentes'),
    path('editar/<int:id>/', views.editar_docente, name='editar_docente'),
    
    path('cambiar_estado/<int:id>/', views.cambiar_estado_docente, name='cambiar_estado_docente'),
    path('cargas/asignar/', views.asignar_carga, name='asignar_carga'),
    path('cargas/lista/', views.lista_cargas, name='lista_cargas'),
    path('cargas/eliminar/<int:id>/', views.eliminar_carga, name='eliminar_carga'),
    path('cargas/imprimir/<int:docente_id>/', views.imprimir_carga_docente, name='imprimir_carga_docente'),
    
    path('ajax/cargar-opciones/', views.cargar_opciones_carga, name='ajax_cargar_opciones'),
    
    
    path('documentos/acceso/', views.validar_acceso_documentos, name='validar_acceso_documentos'),
    path('documentos/lista/', views.lista_documentos, name='lista_documentos'),
    path('documentos/eliminar/<int:doc_id>/', views.eliminar_documento, name='eliminar_documento'),
    
    path('documentos/subir/', views.subir_documento_manual, name='subir_documento_manual'),
]
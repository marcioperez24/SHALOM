# matricula/urls.py
from django.urls import path
from . import views


app_name = 'Matricula'

urlpatterns = [
    path('', views.Matricula_home, name='Matricula_home'),
    path('crear/estudiante/', views.crear_estudiante, name='crear_estudiante'),
    path('crear/matricula/<int:estudiante_id>/', views.crear_matricula, name='crear_matricula'),
    path('get_secciones_por_nivel/', views.get_secciones_por_nivel, name='get_secciones_por_nivel'),
    path('crear/inscripciones/<int:matricula_id>/', views.crear_inscripciones, name='crear_inscripciones'),
    path('estudiante/desactivar/<int:pk>/', views.desactivar_estudiante, name='desactivar_estudiante'),
    path('estudiantes/inactivos/', views.listar_estudiantes_inactivos, name='listar_estudiantes_inactivos'),
    path('estudiante/reactivar/<int:pk>/', views.reactivar_estudiante, name='reactivar_estudiante'),
    path('estudiantes/', views.listar_estudiantes, name='listar_estudiantes'),
    path('matricula/hoja/<int:matricula_id>/', views.ver_hoja_matricula, name='ver_hoja_matricula'),
    path('estudiantes/editar/<int:estudiante_id>/', views.editar_estudiante, name='editar_estudiante'),
        # URL para la selección de filtros antes de ingresar notas
    path('notas/filtro/', views.ingreso_calificaciones_filtro, name='ingreso_calificaciones_filtro'),
    
    # URL para la selección de filtros (Página 1)
    path('notas/filtros/', views.ingreso_calificaciones_filtro, name='ingreso_calificaciones_filtro'),
    
    # API para cargar Secciones y Materias (en Página 1)
    path('api/filtros_dinamicos/', views.api_obtener_filtros_dinamicos, name='api_obtener_filtros_dinamicos'), 
    
    # --- ¡NUEVA RUTA API! ---
    # API para cargar Cortes (en Página 2)
    path('api/get_cortes_por_semestre/', views.api_get_cortes_por_semestre, name='api_get_cortes_por_semestre'),

    # --- ¡RUTA MODIFICADA! ---
    # Ruta para la tabla de ingreso de notas (Página 2)
    path('notas/ingresar/<int:nivel>/<int:seccion>/<int:materia>/', 
         views.ingreso_calificaciones, 
         name='ingreso_calificaciones'),
    
    # --- ¡NUEVAS RUTAS PARA EL REPORTE DE CALIFICACIONES! ---
    path('reportes/calificaciones/filtro/', 
         views.reporte_calificaciones_filtro, 
         name='reporte_calificaciones_filtro'),

    path('reportes/calificaciones/ver/<int:nivel_id>/<int:seccion_id>/', 
         views.ver_reporte_calificaciones, 
         name='ver_reporte_calificaciones'),
    
    path('reportes/calificaciones/exportar/<int:nivel_id>/<int:seccion_id>/', views.exportar_reporte_excel, name='exportar_reporte_excel'),
    
     # --- ¡NUEVAS RUTAS PARA BOLETÍN INDIVIDUAL! ---
    path('boletin/individual/filtro/', views.boletin_individual_filtro, name='boletin_individual_filtro'),
    # (Opcional: API para buscar estudiantes por nombre)
    path('api/buscar_estudiantes/', views.api_buscar_estudiantes, name='api_buscar_estudiantes'),
    path('boletin/individual/ver/<int:estudiante_id>/', views.ver_boletin_individual, name='ver_boletin_individual'),
    path('boletin/individual/imprimir/<int:estudiante_id>/', views.imprimir_boletin_individual, name='imprimir_boletin_individual'),
    
    # --- ¡NUEVAS RUTAS PARA BOLETÍN GRUPAL! ---
    path('boletin/grupal/filtro/', views.boletin_grupal_filtro, name='boletin_grupal_filtro'),
    path('boletin/grupal/imprimir/', views.imprimir_boletin_grupal, name='imprimir_boletin_grupal'),

    path('historial/filtro/', views.historial_academico_filtro, name='historial_academico_filtro'),
    path('historial/ver/<int:estudiante_id>/', views.ver_historial_academico, name='ver_historial_academico'),

    # --- Otras APIs (si las hubiera) ---
    path('get_secciones_por_nivel/', views.get_secciones_por_nivel, name='get_secciones_por_nivel'),
        path('historial/imprimir/<int:estudiante_id>/<int:anio>/<int:nivel_id>/<int:seccion_id>/', 
         views.imprimir_historial_anio, 
         name='imprimir_historial_anio'),
]

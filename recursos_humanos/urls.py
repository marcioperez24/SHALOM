from django.urls import path
from . import views

app_name = 'recursos_humanos'

urlpatterns = [
    path('', views.rrhh_home, name='rrhh_home'), # La raíz de la app
    path('empleados/', views.lista_empleados, name='lista_empleados'),
    path('empleados/nuevo/', views.crear_empleado, name='crear_empleado'),
    path('empleado/editar/<int:pk>/', views.editar_empleado, name='editar_empleado'),
    path('empleado/expediente/<int:pk>/', views.expediente_empleado, name='expediente_empleado'),
    path('empleado/contrato-print/<int:pk>/', views.imprimir_contrato, name='imprimir_contrato'),
    
    # --- Módulo de Planilla y Pagos ---
    # Esta es la que genera el cálculo individual
    path('planilla/generar/<int:empleado_id>/', views.generar_pago_mes, name='generar_pago_mes'),
    
    # Esta es la que activamos en el botón verde del Dashboard
    path('planilla/nomina-general/', views.nomina_general_mes, name='nomina_general'),
    path('planilla/nomina-imprimir/', views.imprimir_nomina_general, name='imprimir_nomina_general'),
    path('planilla/contabilizar/<int:pk>/', views.contabilizar_pago_planilla, name='contabilizar_pago_planilla'),
    
    path('verificar-duplicados/', views.verificar_duplicados, name='verificar_duplicados'),

    # --- Control de Asistencia ---
    path('asistencia/gestion/', views.gestion_asistencia, name='gestion_asistencia'),
    path('asistencia/kiosko/', views.kiosko_asistencia_view, name='kiosko_asistencia'),
    path('asistencia/feriado/', views.registrar_feriado, name='registrar_feriado'),
    path('asistencia/feriado/eliminar/<int:pk>/', views.eliminar_feriado, name='eliminar_feriado'),
    path('api/marcar-asistencia/', views.api_marcar_asistencia, name='api_marcar_asistencia'),
    
    path('empleado/horario/<int:pk>/', views.configurar_horario, name='configurar_horario'),

    # --- Liquidaciones ---
    path('empleado/liquidar/<int:pk>/', views.liquidar_empleado, name='liquidar_empleado'),
    path('empleado/finiquito/<int:pk>/', views.imprimir_finiquito, name='imprimir_finiquito'),
    path('empleado/liquidar/contabilizar/<int:pk>/', views.contabilizar_liquidacion, name='contabilizar_liquidacion'),
]
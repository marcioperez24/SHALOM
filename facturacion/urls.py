#facturacion/urls.py
from django.urls import path
from . import views

app_name = 'facturacion'

urlpatterns = [
    path('', views.facturacion_home_view, name='facturacion_home'),
    path('facturas/', views.lista_facturas_view, name='lista_facturas'),
    path('facturas/crear/', views.crear_factura_view, name='crear_factura'),
    path('facturas/recibo/generar/<int:factura_id>/', views.generar_recibo_view, name='generar_recibo'),
    path('conceptos/', views.conceptos_view, name='conceptos'),
    # Nueva URL de API para obtener información de un estudiante
    path('api/estudiante/<int:estudiante_id>/', views.obtener_estudiante_info, name='obtener_estudiante_info'),
    path('api/tipo_cambio/', views.obtener_tipo_cambio, name='obtener_tipo_cambio'),
    path('recibo/<int:recibo_id>/imprimir/', views.recibo_imprimir_view, name='recibo_imprimir'),
    path('detalle_recibo/<int:recibo_id>/', views.recibo_detalle_view, name='recibo_detalle'),
    path('pagar-pendiente/<int:factura_id>/', views.pagar_pendiente, name='pagar_pendiente'),
    path('facturas/<int:factura_id>/detalle/', views.detalle_factura_view, name='detalle_factura'),
    path('historial_pagos/<int:estudiante_id>/', views.historial_pagos_view, name='historial_pagos'),
    path('pagos/', views.pagos_view, name='pagos'),
    path('toggle_arqueo/', views.toggle_arqueo_view, name='toggle_arqueo'),
    path('iniciar_arqueo/', views.toggle_arqueo_view, name='iniciar_arqueo'),
    path('anular_recibo/<int:recibo_id>/', views.anular_recibo_view, name='anular_recibo'),
    path('arqueos/', views.lista_arqueos_view, name='lista_arqueos'),
    path('arqueos/<int:arqueo_id>/', views.detalle_arqueo_view, name='detalle_arqueo'),
    path('arqueos/imprimir/<int:arqueo_id>/', views.imprimir_arqueo_view, name='imprimir_arqueo'),
    path('informe_aranceles/', views.informe_aranceles_view, name='informe_aranceles'),
    
    # 2. NUEVA URL para el informe de impresión (solo contenido simple)
    path('informe_aranceles/imprimir/', views.informe_aranceles_imprimir_view, name='informe_aranceles_imprimir'), 
    path('api/obtener-servicios/', views.api_obtener_servicios, name='api_obtener_servicios'),
    path('arqueo/<int:arqueo_id>/exportar/', views.exportar_arqueo_excel_view, name='exportar_arqueo'),
    path('informes/aranceles/exportar/', views.informe_aranceles_exportar_view, name='informe_aranceles_exportar'),
    path('informes/consulta_ingresos/', views.consulta_ingresos_view, name='consulta_ingresos'),
    path('informes/consulta_ingresos/imprimir/', views.consulta_ingresos_imprimir_view, name='consulta_ingresos_imprimir'),
    
    path('reporte/saldos/', views.consulta_saldos_view, name='consulta_saldos_pendientes'),
    path('api/servicios_por_nivel_y_anio/', views.api_servicios_por_nivel_y_anio, name='api_servicios_por_nivel_y_anio'),
    path('consulta/facturas_pendientes/', views.consulta_facturas_pendientes_view, name='consulta_facturas_pendientes'),
    path('consulta/facturas_pendientes/imprimir/', views.consulta_facturas_pendientes_imprimir_view, name='consulta_facturas_pendientes_imprimir'),
    path('reporte/saldos/imprimir/', views.consulta_saldos_pendientes_imprimir_view, name='consulta_saldos_pendientes_imprimir'),
    
    path('reporte/estado-cuenta/', views.estado_cuenta_estudiante_view, name='estado_cuenta_estudiante'),
    path('reporte/estado-cuenta/imprimir/', views.estado_cuenta_imprimir_view, name='estado_cuenta_imprimir'),
    
]

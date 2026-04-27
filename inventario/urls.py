from django.urls import path
from . import views

app_name = 'inventario'

urlpatterns = [
    path('', views.lista_productos, name='lista_productos'),
    path('agregar/', views.agregar_producto, name='agregar_producto'),
    path('editar/<int:pk>/', views.editar_producto, name='editar_producto'),
    path('eliminar/<int:pk>/', views.eliminar_producto, name='eliminar_producto'),
    path('categorias/', views.gestionar_categorias, name='gestionar_categorias'),

    # Rutas de Compras de Inventario
    path('compras/', views.lista_compras_view, name='lista_compras'),
    path('compras/nueva/', views.crear_compra_view, name='crear_compra'),
    path('compras/anular/<int:compra_id>/', views.anular_compra_view, name='anular_compra'),
    path('compras/api/proveedor/agregar/', views.api_agregar_proveedor, name='api_agregar_proveedor'),
]

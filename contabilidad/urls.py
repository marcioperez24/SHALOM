from django.urls import path
from . import views

app_name = 'contabilidad'

urlpatterns = [
    path('', views.contabilidad_home, name='contabilidad_home'),
    path('movimientos/', views.listado_movimientos, name='listado_movimientos'),
    path('movimientos/nuevo/', views.registrar_movimiento, name='registrar_movimiento'),
]
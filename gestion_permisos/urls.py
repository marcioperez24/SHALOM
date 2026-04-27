from django.urls import path
from . import views

urlpatterns = [
    path('grupos/', views.lista_grupos_view, name='lista_grupos'),
    path('grupos/crear/', views.crear_grupo_view, name='crear_grupo'),
    path('grupos/editar/<int:group_id>/', views.editar_grupo_view, name='editar_grupo'),
    path('grupos/asignar-usuarios/<int:group_id>/', views.asignar_usuario_a_grupo_view, name='asignar_usuario_a_grupo'),
    path('grupos/eliminar/<int:group_id>/', views.eliminar_grupo_view, name='eliminar_grupo'),
]

# configuracion/urls.py
from django.urls import path
from . import views

app_name = 'configuracion'

urlpatterns = [
    path('', views.configuracion_home, name='configuracion_home'),
    path('usuarios/', views.listar_usuarios, name='listar_usuarios'),
    path('usuarios/crear/', views.crear_usuario, name='crear_usuario'),
    # Podemos añadir más URLs aquí para la edición de usuarios, roles, etc.
    path('usuarios/editar/<int:user_id>/', views.editar_usuario, name='editar_usuario'),
    # URL para deshabilitar un usuario
    path('usuarios/deshabilitar/<int:user_id>/', views.deshabilitar_usuario, name='deshabilitar_usuario'),
    
    # Rutas para la gestión de niveles
    path('niveles/', views.listar_niveles, name='listar_niveles'),
    path('niveles/crear/', views.crear_Nivel, name='crear_nivel'),
    path('niveles/editar/<int:NivelID>/', views.editar_Nivel, name='editar_nivel'),
    path('niveles/eliminar/<int:NivelID>/', views.eliminar_Nivel, name='eliminar_nivel'),
    
    # RUTAS PARA SECCIONES
    # -----------------------------------------------------------
    path('secciones/', views.listar_secciones, name='listar_secciones'),
    path('secciones/crear/', views.crear_seccion, name='crear_seccion'),
    path('secciones/editar/<int:SeccionID>/', views.editar_seccion, name='editar_seccion'),
    path('secciones/eliminar/<int:SeccionID>/', views.eliminar_seccion, name='eliminar_seccion'),
    
    # Rutas para Tipos de Servicio
    path('Tservicios/', views.listar_tservicios, name='listar_tservicios'),
    path('Tservicios/crear/', views.crear_tservicio, name='crear_tservicio'),
    path('Tservicios/editar/<int:TipoServicioID>/', views.editar_tservicio, name='editar_tservicio'),
    path('Tservicios/eliminar/<int:TipoServicioID>/', views.eliminar_tservicio, name='eliminar_tservicio'),
    
    # Rutas para Servicios
    path('servicios/', views.listar_servicios, name='listar_servicios'),
    path('servicios/crear/', views.crear_servicio, name='crear_servicio'),
    path('servicios/editar/<int:ServicioID>/', views.editar_servicio, name='editar_servicio'),
    path('servicios/eliminar/<int:ServicioID>/', views.eliminar_servicio, name='eliminar_servicio'),
    path('servicios/descargar-plantilla/', views.descargar_plantilla_servicios, name='descargar_plantilla'),
    path('servicios/importar-excel/', views.importar_servicios_excel, name='importar_excel'),
    
    # Rutas para Materias
    path('materias/', views.listar_materias, name='listar_materias'),
    path('materias/crear/', views.crear_materia, name='crear_materia'),
    path('materias/editar/<int:MateriaID>/', views.editar_materia, name='editar_materia'),
    path('materias/eliminar/<int:MateriaID>/', views.eliminar_materia, name='eliminar_materia'),
    
    # Rutas para TipoMatricula
    path('tipomatricula/', views.listar_tipomatricula, name='listar_tipomatricula'),
    path('tipomatricula/crear/', views.crear_tipomatricula, name='crear_tipomatricula'),
    path('tipomatricula/editar/<int:TipoMatriculaID>/', views.editar_tipomatricula, name='editar_tipomatricula'),
    path('tipomatricula/eliminar/<int:TipoMatriculaID>/', views.eliminar_tipomatricula, name='eliminar_tipomatricula'),
    
    # Rutas para Turno
    path('turnos/', views.listar_turnos, name='listar_turnos'),
    path('turnos/crear/', views.crear_turno, name='crear_turno'),
    path('turnos/editar/<int:TurnoID>/', views.editar_turno, name='editar_turno'),
    path('turnos/eliminar/<int:TurnoID>/', views.eliminar_turno, name='eliminar_turno'),
    
    # Rutas para Modalidades
    path('modalidades/', views.listar_modalidades, name='listar_modalidades'),
    path('modalidades/crear/', views.crear_modalidad, name='crear_modalidad'),
    path('modalidades/editar/<int:ModalidadID>/', views.editar_modalidad, name='editar_modalidad'),
    path('modalidades/eliminar/<int:ModalidadID>/', views.eliminar_modalidad, name='eliminar_modalidad'),
    
    # Rutas para Semestres
    path('semestres/', views.listar_semestres, name='listar_semestres'),
    path('semestres/crear/', views.crear_semestre, name='crear_semestre'),
    path('semestres/editar/<int:SemestreID>/', views.editar_semestre, name='editar_semestre'),
    path('semestres/eliminar/<int:SemestreID>/', views.eliminar_semestre, name='eliminar_semestre'),
    
    # Rutas para Cortes
    path('cortes/', views.listar_cortes, name='listar_cortes'),
    path('cortes/crear/', views.crear_corte, name='crear_corte'),
    path('cortes/editar/<int:CorteID>/', views.editar_corte, name='editar_corte'),
    path('cortes/eliminar/<int:CorteID>/', views.eliminar_corte, name='eliminar_corte'),
    
    # Rutas para Tipos de Cambio
    path('tipos-cambio/', views.listar_tipos_cambio, name='listar_tipos_cambio'),
    path('tipos-cambio/crear/', views.crear_tipo_cambio, name='crear_tipo_cambio'),
    path('tipos-cambio/editar/<int:TipoCambioID>/', views.editar_tipo_cambio, name='editar_tipo_cambio'),
    path('tipos-cambio/eliminar/<int:TipoCambioID>/', views.eliminar_tipo_cambio, name='eliminar_tipo_cambio'),


    path('licencia/administrar/', views.administrar_licencia_view, name='administrar_licencia'),
    path('licencia/vencida/', views.licencia_vencida_view, name='licencia_vencida'),

]
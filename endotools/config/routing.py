"""Routes configuration

The more specific and detailed routes should be defined first so they
may take precedent over the more generic routes. For more information
refer to the routes manual at http://routes.groovie.org/docs/
"""
from pylons import config
from routes import Mapper

def make_map():
    """Create, configure and return the routes Mapper"""
    map = Mapper(directory=config['pylons.paths']['controllers'],
                 always_scan=config['debug'])
    # The ErrorController route (handles 404/500 error pages); it should
    # likely stay at the top, ensuring it can always be resolved
    map.connect('error/:action/:id', controller='error')
    #   locales (traducciones)
    map.connect('locales/:lang/translation.:format', controller='locales', action='translation')
    #   forma correcta de entrar a la aplicación: web/start o web/main
    map.connect('/web/start', controller='main', action='web', filename='main.html')
    map.connect('/web/main', controller='main', action='web', filename='main.html')
    # /web, controlado por main.web, por defecto sirve ficheros de /webapp
    map.connect('/web/{filename:.*?}', controller='main', action='web')
    # acceso al admin
    map.connect('/admin', controller='main', action='admin')
    # acceso a los res. de Endosys App (blank.png...)
    map.connect('/res/{filename:.*?}', controller='main', action='res')
    # acceso a los custom res. (logos, fuentes...) en los informes html
    map.connect('/custom/res/{filename:.*?}', controller='main', action='custom_informes_res')
    # backward compatibility
    # newweb -> web
    map.connect('/newweb/{filename:.*?}', controller='main', action='web')
    # /yui2 -> /lib/yui2   y   /yui3 -> /lib/yui3 (deberian cambiarse todas las rutas a /lib/yuiX!)
    map.connect('/yui2/{filename:.*?}', controller='main', action='lib_yui2')
    map.connect('/yui3/{filename:.*?}', controller='main', action='lib_yui3')
    # acceso a la versión
    map.connect('/version', controller='main', action='version')
    # utilidad combo
    map.connect('/combo', controller='main', action='combo', format=None)
    map.connect('/combo.{format}', controller='main', action='combo')
    # COMMANDS
    map.connect('/commands/create_pacientes', controller='commands/create_pacientes', action='run')
    map.connect('/commands/organizar-capturas', controller='commands/organizar_capturas', action='run')
    map.connect('/commands/organizar-informes', controller='commands/organizar_informes', action='run')
    map.connect('/commands/migracion', controller='commands/migracion', action='run')
    # REDIRECCIONES
    # redireccionar por defecto a /web/start
    map.redirect('/', '/web/start')
    # /web también lleva a /web/start
    map.redirect('/web', '/web/start')
    # el admin que antes estaba en la raiz ahora est/a en /admin
    map.redirect('/admin', '/index.html')
    # REST
    map.resource('paciente', 'pacientes', controller='rest/pacientes', path_prefix='/rest', name_prefix='rest_')
    map.resource('exploracion', 'exploraciones', controller='rest/exploraciones', path_prefix='/rest', name_prefix='rest_')
    map.resource('aseguradora', 'aseguradoras', controller='rest/aseguradoras', path_prefix='/rest', name_prefix='rest_')
    map.resource('centro', 'centros', controller='rest/centros', path_prefix='/rest', name_prefix='rest_')
    map.resource('sala', 'salas', controller='rest/salas', path_prefix='/rest', name_prefix='rest_')
    map.resource('servicio', 'servicios', controller='rest/servicios', path_prefix='/rest', name_prefix='rest_')
    map.resource('formulario', 'formularios', controller='rest/formularios', path_prefix='/rest', name_prefix='rest_')
    map.resource('tipoExploracion', 'tiposExploracion', controller='rest/tiposExploracion', path_prefix='/rest', name_prefix='rest_')
    map.resource('campo', 'campos', controller='rest/campos', path_prefix='/rest', name_prefix='rest_')
    map.resource('grupoCampos', 'gruposCampos', controller='rest/gruposCampos', path_prefix='/rest', name_prefix='rest_')
    map.resource('cita', 'citas', controller='rest/citas', path_prefix='/rest', name_prefix='rest_')
    map.resource('captura', 'capturas', controller='rest/capturas', path_prefix='/rest', name_prefix='rest_')
    map.resource('informe', 'informes', controller='rest/informes', path_prefix='/rest', name_prefix='rest_')
    map.resource('elemento', 'elementos', controller='rest/elementos', path_prefix='/rest', name_prefix='rest_')
    map.resource('medico', 'medicos', controller='rest/medicos', path_prefix='/rest', name_prefix='rest_')
    map.resource('plantilla', 'plantillas', controller='rest/plantillas', path_prefix='/rest', name_prefix='rest_')
    map.resource('usuario', 'usuarios', controller='rest/usuarios', path_prefix='/rest', name_prefix='rest_')
    map.resource('permiso', 'permisos', controller='rest/permisos', path_prefix='/rest', name_prefix='rest_')
    map.resource('opcionConfig', 'opcionesConfig', controller='rest/opcionesConfig', path_prefix='/rest', name_prefix='rest_')
    map.resource('agenda', 'agendas', controller='rest/agendas', path_prefix='/rest', name_prefix='rest_')
    map.resource('agenda_chus', 'agendas_chus', controller='rest/agendas_chus', path_prefix='/rest', name_prefix='rest_')
    map.resource('predefinido', 'predefinidos', controller='rest/predefinidos', path_prefix='/rest', name_prefix='rest_')
    map.resource('busqueda', 'busquedas', controller='rest/busquedas', path_prefix='/rest', name_prefix='rest_')
    map.resource('campoFijo', 'camposFijos', controller='rest/camposFijos', path_prefix='/rest', name_prefix='rest_')
    map.resource('fusion', 'fusiones', controller='rest/fusiones', path_prefix='/rest', name_prefix='rest_')
    map.resource('motivoCancelacion', 'motivosCancelacion', controller='rest/motivosCancelacion', path_prefix='/rest', name_prefix='rest_')
    map.resource('prioridad', 'prioridades', controller='rest/prioridades', path_prefix='/rest', name_prefix='rest_')
    map.resource('provincia', 'provincias', controller='rest/provincias', path_prefix='/rest', name_prefix='rest_')
    map.resource('poblacion', 'poblaciones', controller='rest/poblaciones', path_prefix='/rest', name_prefix='rest_')
    map.resource('chunk', 'chunks', controller='rest/chunks', path_prefix='/rest', name_prefix='rest_')
    map.resource('workstation', 'workstations', controller='rest/workstations', path_prefix='/rest', name_prefix='rest_')
    map.resource('tarea', 'tareas', controller='rest/tareas', path_prefix='/rest', name_prefix='rest_')
    map.resource('notificaciones', 'notificaciones', controller='rest/notificaciones', path_prefix='/rest', name_prefix='rest_')
    # relaciones de subconjuntos
    # /exploraciones/n/capturas
    map.resource('captura', 'capturas', controller='rest/capturas', path_prefix='/rest/exploraciones/:exploracion_id', name_prefix="exploracion_")
    # /exploraciones/n/informes
    map.resource('informe', 'informes', controller='rest/informes', path_prefix='/rest/exploraciones/:exploracion_id', name_prefix="exploracion_")
    # /pacientes/n/informes
    map.resource('informe', 'informes', controller='rest/informes', path_prefix='/rest/pacientes/:paciente_id', name_prefix="paciente_")
    # /exploraciones/n/formularios
    map.resource('formulario', 'formularios', controller='rest/formularios', path_prefix='/rest/exploraciones/:exploracion_id', name_prefix="exploracion_")
    # /exploraciones/n/chunks
    map.resource('chunk', 'chunks', controller='rest/chunks', path_prefix='/rest/exploraciones/:exploracion_id', name_prefix="exploracion_")
    # /tiposExploracion/n/formularios
    map.resource('formulario', 'formularios', controller='rest/formularios', path_prefix='/rest/tiposExploracion/:tipoexploracion_id', name_prefix="tipoexploracion_")
    # /campos/n/elementos
    map.resource('elemento', 'elementos', controller='rest/elementos', path_prefix='/rest/campos/:campo_id', name_prefix="campo_")
    # /campos/n/predefinidos
    map.resource('predefinido', 'predefinidos', controller='rest/predefinidos', path_prefix='/rest/campos/:campo_id', name_prefix="campo_")
    # /pacientes/n/citas
    map.resource('cita', 'citas', controller='rest/citas', path_prefix='/rest/pacientes/:paciente_id', name_prefix="paciente_")
    # /pacientes/n/exploraciones
    map.resource('exploracion', 'exploraciones', controller='rest/exploraciones', path_prefix='/rest/pacientes/:paciente_id', name_prefix="paciente_")
    # /formularios/n/campos
    map.resource('campo', 'campos', controller='rest/campos', path_prefix='/rest/formularios/:formulario_id', name_prefix="formulario_")
    # por defecto
    map.connect(':controller/:action.:format')
    map.connect(':controller/:action/:id')
    map.connect('*url', controller='template', action='view')
    return map
import logging
log = logging.getLogger(__name__)

def _import(name):
    mod = __import__(name)
    components = name.split('.')
    for comp in components[1:]:
        mod = getattr(mod, comp)
    return mod

pluginPacientes = None
pluginCitas = None
pluginExploraciones = None
pluginInformes = None
pluginCampos = None
pluginAgendas = None
pluginHL7 = None

from pylons import config

try:
    plugins_module_name = 'custom.%s.plugins.config' % config.get('CARPETA_CUSTOM','HOSPITAL')
    plugins_module = _import(plugins_module_name)
except Exception as e:
    # Para probar el funcionamiento, descomentar la linea siguiente
    #raise
    log.error('Ha ocurrido un error cargando la configuracion de plugins:')
    log.error(e)
    plugins_module = None

if plugins_module:
    from endotools.lib.plugins.base import check_dependencies
    check_dependencies()

    pluginPacientes = getattr(plugins_module, 'pluginPacientes', None)
    pluginCitas = getattr(plugins_module, 'pluginCitas', None)
    pluginExploraciones = getattr(plugins_module, 'pluginExploraciones', None)
    pluginInformes = getattr(plugins_module, 'pluginInformes', None)
    pluginCampos = getattr(plugins_module, 'pluginCampos', None)
    pluginAgendas = getattr(plugins_module, 'pluginAgendas', None)
    pluginHL7 = getattr(plugins_module, 'pluginHL7', None)

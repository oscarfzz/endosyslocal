"""Pylons environment configuration"""
import os
import datetime
import _strptime

from sqlalchemy import engine_from_config
from pylons import config

import endotools.lib.app_globals as app_globals
import endotools.lib.helpers
from endotools.config.routing import make_map
from endotools.model import init_model
from endotools.lib.checks import check_cache_dir

def _endotools_environment_config():
    """ Configuración de variables de Endosys App, como por ejemplo rutas, etc...
        Añadir paths:
        ------------
        se puede añadir directamente a conf['pylons.paths']
    """
    paths = config['pylons.paths']

    # Carpetas de capturas, informes y chunks
    if check_cache_dir():
        paths['capturas'] = os.path.join(paths['root_parent'], 'data', 'capturas')
        paths['informes'] = os.path.join(paths['root_parent'], 'data', 'informes')
        paths['chunks'] = os.path.join(paths['root_parent'], 'data', 'chunks')
    else:
        paths['capturas'] = os.path.join(paths['root'], 'capturas')
        paths['informes'] = os.path.join(paths['root'], 'informes')
        paths['chunks'] = os.path.join(paths['root'], 'chunks')

    # Si se ha configurado una ruta para las capturas en el INI, asignarla
    paths['capturas'] = config.get('PATHS.CAPTURAS', paths['capturas'])


    # Si se ha configurado una ruta para los informes en el INI, asignarla
    paths['informes'] = config.get('PATHS.INFORMES', paths['informes'])

    if not os.path.exists(paths['capturas']):
        # Podria ser una ruta de red
        os.makedirs(paths['capturas'])
    if not os.path.exists(paths['informes']):
        os.makedirs(paths['informes'])
    if not os.path.exists(paths['chunks']):
        os.makedirs(paths['chunks'])

    # Carpeta de archivos especificos de un cliente/instalación
    config['CARPETA_CUSTOM'] = config.get('CARPETA_CUSTOM', 'files')
    carpeta_custom = os.path.join('custom', config['CARPETA_CUSTOM'])
    
    # raiz
    paths['custom'] = os.path.join(paths['root_parent'], carpeta_custom)
    
    # Informes:
    # Custom_informes_templ: plantillas especificas del cliente, para la
    #                        generación de informes.
    paths['custom_informes_templ'] = os.path.join(paths['root_parent'], carpeta_custom, 'informes', 'templates')
    
    # custom_informes_res: archivos especificos del cliente usados por
    #                      las plantillas de informes, como logos, fuentes, etc...
    paths['custom_informes_res'] = os.path.join(paths['root_parent'], carpeta_custom, 'informes', 'res')
    
    # Plugins
    # custom_plugins: plugins con funcionalidad específica del cliente,
    #                 de integración, etc...
    paths['custom_plugins'] = os.path.join(paths['root_parent'], carpeta_custom, 'plugins')

    if not os.path.exists(paths['custom_informes_res']):
        os.makedirs(paths['custom_informes_res'])
    if not os.path.exists(paths['custom_informes_templ']):
        os.makedirs(paths['custom_informes_templ'])
    if not os.path.exists(paths['custom_plugins']):
        os.makedirs(paths['custom_plugins'])

    # añade la carpeta de las plantillas de informes a la ruta de templates de mako
    config['buffet.template_options']['mako.directories'].append( paths['custom_informes_templ'] )

    # anade la carpeta de endotools/templates a los templates disponibles en el pylons
    config['buffet.template_options']['mako.directories'].append( os.path.join(paths['root'],'templates') )

def load_environment(global_conf, app_conf):
    global lock_chunks
    global event_chunks

    """ Configure the Pylons environment via the ``pylons.config``
        object
    """
    
    # Pylons paths
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    root_parent = os.path.split(root)[0]
    paths = dict(   root_parent=root_parent,
                    root=root,
                    controllers=os.path.join(root, 'controllers'),
                    static_files=os.path.join(root, 'public'),
                    templates=[os.path.join(root, 'templates')])

    # Initialize config with the basic options
    config.init_app(global_conf, app_conf, package='endotools',
                    template_engine='mako', paths=paths)

    _endotools_environment_config()

    config['routes.map'] = make_map()
    config['pylons.g'] = app_globals.Globals()
    config['pylons.h'] = endotools.lib.helpers

    # Customize templating options via this variable
    tmpl_options = config['buffet.template_options']


    #tmpl_options['mako.input_encoding'] = 'UTF-8'
    #tmpl_options['mako.output_encoding'] = 'UTF-8'
    #tmpl_options['mako.default_filters'] = ['force_ascii']
    #tmpl_options['mako.imports'] = ["from endotools.config.environment import force_ascii"]

    # CONFIGURATION OPTIONS HERE (note: all config options will override
    # any Pylons config options)
    import base64
    raw_password = config.get('raw_password')
    password = base64.b64decode(raw_password)
    config['sqlalchemy.url'] = config.get('sqlalchemy.url').format(password)

    engine = engine_from_config(config, 'sqlalchemy.')
    init_model(engine)

    # Chunks: Lanza el hilo de recuperacion de chunks 
    #         Solo se ejecuta si el EWC_MODO.ACTIVO = 1
    from endotools.lib.chunks.utils import comenzar_hilo_chunks
    modo_ewc = config.get('EWC_MODO.ACTIVO', '0')
    if modo_ewc == '1':
        comenzar_hilo_chunks()
    
    # PurgadoImagenes: lanza un hilo para pugar imagenes que
    #                  ya han sido enviadas al PACS
    from endotools.lib.purgadoImagenes.utils import comenzar_hilo_purgado
    purgado = config.get('PURGADO.ACTIVO', '0')
    if purgado == '1':
        comenzar_hilo_purgado()

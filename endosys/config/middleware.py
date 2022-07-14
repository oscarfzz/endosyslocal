"""Pylons middleware initialization"""
from paste.cascade import Cascade
from paste.registry import RegistryManager
from paste.urlparser import StaticURLParser
from paste.deploy.converters import asbool

from pylons import config
from pylons.error import error_template
from pylons.middleware import error_mapper, ErrorDocuments, ErrorHandler, \
    StaticJavascripts
from pylons.wsgiapp import PylonsApp

from endosys.config.environment import load_environment
import authkit.authenticate


def custom_error_mapper(code, message, environ, global_conf=None, **kw):
    # cuando es un error HTTPErrorXML, omitir las plantillas del pylons (porque interesa la informacion xml del content)
    if environ.get('is_HTTPErrorXML', False) or environ.get('is_HTTPErrorJSON', False):
        return None
    else:
        return error_mapper(code, message, environ, global_conf=None, **kw)

class ApiKeyMiddleware(object):
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        keyarg = "_apikey"
        if environ['REQUEST_METHOD'] in ['GET', 'POST', 'PUT']:
            from urlparse import parse_qs
            params = parse_qs(environ['QUERY_STRING'])
            if keyarg in params and len(params[keyarg][0]) > 10:
                from endosys import model
                from endosys.model import meta
                from urllib import urlencode
                q = meta.Session.query(model.Usuario).filter_by(clave=params[keyarg][0])
                del params[keyarg]
                environ['QUERY_STRING'] = urlencode(params, True)
                if q.count():
                    usuario = q.one()
                    if usuario.activo:
                        print "Usando API KEY de usuario " + usuario.username
                        environ['REMOTE_USER'] = usuario.username

        return self.app(environ, start_response)


def make_app(global_conf, full_stack=True, **app_conf):
    """Create a Pylons WSGI application and return it

    ``global_conf``
        The inherited configuration for this application. Normally from
        the [DEFAULT] section of the Paste ini file.

    ``full_stack``
        Whether or not this application provides a full WSGI stack (by
        default, meaning it handles its own exceptions and errors).
        Disable full_stack when this application is "managed" by
        another WSGI middleware.

    ``app_conf``
        The application's local configuration. Normally specified in the
        [app:<name>] section of the Paste ini file (where <name>
        defaults to main).
    """

    #import endotools.config.endotoolsweb
    #endotools.config.endotoolsweb.initialize()

    # Configure the Pylons environment
    load_environment(global_conf, app_conf)

    # The Pylons WSGI app
    app = PylonsApp()

    # CUSTOM MIDDLEWARE HERE (filtered by error handling middlewares)

    #app = LangMiddleware(app)

    if asbool(full_stack):
        # Handle Python exceptions
        # app = ErrorHandler(app, global_conf, error_template=error_template,
        #                  **config['pylons.errorware'])
        # XXX   #################################
        from endosys.lib.middleware.error import EndoTools_ErrorHandler
        app = EndoTools_ErrorHandler(app, global_conf, error_template=error_template,
                           **config['pylons.errorware'])
        # #######################################

        if int(config.get('PERMITIR_API_KEY', "0")) != 0:
            app = ApiKeyMiddleware(app)

        # authkit
        import endosys.lib.usuarios.LDAPauthentication
        if int(config.get('USAR_LDAP', '0')):
            print "Usando autenticacion LDAP"

        authkit.authenticate.valid_password = endosys.lib.usuarios.LDAPauthentication.valid_password
        # permission = ValidAuthKitUser()
        # app = authkit.authorize.middleware(app, permission)
        app = authkit.authenticate.middleware(app, app_conf)

        # Display error documents for 401, 403, 404 status codes (and
        # 500 when debug is disabled)
        app = ErrorDocuments(app, global_conf, mapper=custom_error_mapper, **app_conf)

    # Establish the Registry for this application
    app = RegistryManager(app)

    # Static files
    javascripts_app = StaticJavascripts()
    static_app = StaticURLParser(config['pylons.paths']['static_files'])
    app = Cascade([static_app, javascripts_app, app])
    
    #configura el idioma por defecto si no esta la clave ini
    if not ("lang" in config and config["lang"]):
        config["lang"] = "es"
    
    #elimina las tareas si no estan finalizadas
    from endosys.model.tareas import Tarea
    from endosys.model import meta
    q = meta.Session.query(Tarea)
    tareas = q.filter(Tarea.estado == 1)
    for t in tareas.all():
        t.estado=3
        meta.Session.update(t)
        meta.Session.commit()
    
    return app

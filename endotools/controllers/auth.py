import logging

from authkit.authorize.pylons_adaptors import authorize

from authkit.permissions import RemoteUser, ValidAuthKitUser, UserIn, HasAuthKitRole, And
#from authkit.authorize import middleware

from endotools.lib.base import *

log = logging.getLogger(__name__)

class AuthController(BaseController):

    @authorize(ValidAuthKitUser())
    def signin(self):
##        print "-------------------"
##        print "auth/signin CONTENT"
##        print request.body
##        print "auth/signin HEADERS"
##        for x in request.headers: print x, request.headers[x]
##        print "-------------------"
        #  devolver xml con el medico_id
        from endotools.lib.misc import medico_from_user
        medico = medico_from_user( request.environ['REMOTE_USER'] )
        response.content_type = "text/xml"
        response.headers['cache-control'] = "no-cache, no-store, must-revalidate"
        return "<medico><medico_id>%s</medico_id></medico>" % (medico.id, )

    def signout(self):
        return 'Signed out'#IDIOMA

    def remote_user(self):
        """ devuelve el usuario conectado o una cadena vacia si no se ha
        autenticado ningun usuario
        """
        return request.environ.get('REMOTE_USER', '')


#   esta linea es para incluir autenticacion en el controlador
#   si ya se ha incluido en el middleware (app = authkit.authorize.middleware(app, permission)) entonces no es necesaria
##AuthController = middleware(AuthController(), ValidAuthKitUser())

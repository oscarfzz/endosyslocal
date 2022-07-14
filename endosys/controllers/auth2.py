import logging

from authkit.authorize.pylons_adaptors import authorize

from authkit.permissions import RemoteUser, ValidAuthKitUser, UserIn, HasAuthKitRole, And
#from authkit.authorize import middleware

from endosys.lib.base import *
from endosys.lib.misc import formatea_valor

log = logging.getLogger(__name__)

class Auth2Controller(BaseController):

    @authorize(ValidAuthKitUser())
    def signin(self):
        #  devolver xml con el medico
        from endosys.lib.misc import medico_from_user
        medico = medico_from_user( request.environ['REMOTE_USER'] )
        response.content_type = "text/xml"
        response.headers['cache-control'] = "no-cache, no-store, must-revalidate"
        return u'<medico id="%s"><nombre>%s</nombre><username>%s</username></medico>' % (medico.id, formatea_valor(medico.nombre), medico.username)

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

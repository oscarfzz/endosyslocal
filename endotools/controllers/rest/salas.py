import logging
from pylons.i18n import _

from endotools.model.salas import Sala
from xml.etree.ElementTree import Element, SubElement, tostring

#from endotools.lib.base import *
from endotools.lib.genericREST import *

from authkit.authorize.pylons_adaptors import authorize
from authkit.permissions import RemoteUser, ValidAuthKitUser, UserIn, HasAuthKitRole, And
from endotools.lib.usuarios.seguridad import roles

log = logging.getLogger(__name__)


class SalasController(GenericRESTController):

    def __init__(self, *args, **kwargs):
        GenericRESTController.__init__(self, *args, **kwargs)
        self.tabla = Sala
        self.nombre_recurso = 'sala'
        self.nombre_recursos = 'salas'
        self.campos_index = ('id', 'nombre', 'centro')
        self.campo_orderby = Sala.nombre

    @authorize(RemoteUser())
    def index(self, format='xml'):
        return GenericRESTController.index(self, format)

	@authorize(RemoteUser())
	def show(self, id, format='xml'):
		return GenericRESTController.show(self, id, format)

	@authorize(HasAuthKitRole([roles.admin_organizacion]))
	def update(self, id):
		#   no permitir modificar. Para dar de baja, ver mas abajo, en el delete
		#   XXX o permitir modificar solo si no se ha utilizado aun...
		# IMPORTANTE MIRAR CON CARLOS VOY A COMENTAR LAS DOS LINEAS SIGUIENTES
		#response.status_code = 405
		#return "ERROR: No se puede modificar un elemento"
		return GenericRESTController.update(self, id)

	@authorize(HasAuthKitRole([roles.admin_organizacion]))
	def create(self, format='xml'):
		return GenericRESTController.create(self, format)

    @authorize(HasAuthKitRole([roles.admin_organizacion]))
    def delete(self, id):
        #   XXX aqui tendria que intentar eliminar, y si va ha sido utilizada, dar de baja
        return GenericRESTController.delete(self, id)

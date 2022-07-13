import logging
from pylons.i18n import _

from endotools.model.prioridades import Prioridad
from xml.etree.ElementTree import Element, SubElement, tostring

#from endotools.lib.base import *
from endotools.lib.genericREST import *

from authkit.authorize.pylons_adaptors import authorize
from authkit.permissions import RemoteUser, ValidAuthKitUser, UserIn, HasAuthKitRole, And
from endotools.lib.usuarios.seguridad import roles

log = logging.getLogger(__name__)


class PrioridadesController(GenericRESTController):

    def __init__(self, *args, **kwargs):
        GenericRESTController.__init__(self, *args, **kwargs)
        self.tabla = Prioridad
        self.nombre_recurso = 'prioridad'
        self.nombre_recursos = 'prioridades'
        self.campos_index = ('id', 'nombre', 'codigo', 'nivel')
        self.campo_orderby = Prioridad.nombre

    @authorize(RemoteUser())
    def index(self, format='xml'):
		return GenericRESTController.index(self, format)

    @authorize(RemoteUser())
    def show(self, id, format='xml'):
        return GenericRESTController.show(self, id, format)


    @authorize(HasAuthKitRole([roles.admin_organizacion]))
    def update(self, id):
		return GenericRESTController.update(self, id)

    @authorize(HasAuthKitRole([roles.admin_organizacion]))
    def create(self):
        return GenericRESTController.create(self)

    @authorize(HasAuthKitRole([roles.admin_organizacion]))
    def delete(self, id):
        #   XXX aqui tendria que intentar eliminar, y si va ha sido utilizada, dar de baja
        return GenericRESTController.delete(self, id)

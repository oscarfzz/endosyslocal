import logging
from pylons.i18n import _

from endotools.model.provincias import Provincia
from xml.etree.ElementTree import Element, SubElement, tostring

#from endotools.lib.base import *
from endotools.lib.genericREST import *

from authkit.authorize.pylons_adaptors import authorize
from authkit.permissions import RemoteUser, ValidAuthKitUser, UserIn, HasAuthKitRole, And
from endotools.lib.usuarios.seguridad import roles

log = logging.getLogger(__name__)


class ProvinciasController(GenericRESTController):

    def __init__(self, *args, **kwargs):
        GenericRESTController.__init__(self, *args, **kwargs)
        self.tabla = Provincia
        self.nombre_recurso = 'provincia'
        self.nombre_recursos = 'provincias'
        self.campos_index = ('id', 'codigo', 'nombre')
        self.contains_filter = ('nombre')
        self.campo_orderby = Provincia.nombre

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

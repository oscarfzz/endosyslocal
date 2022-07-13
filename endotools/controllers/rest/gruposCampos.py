import logging
from pylons.i18n import _
from endotools.model.gruposCampos import GrupoCampos
from xml.etree.ElementTree import Element, SubElement, tostring

#from endotools.lib.base import *
from endotools.lib.genericREST import *

from authkit.authorize.pylons_adaptors import authorize
from authkit.permissions import RemoteUser, ValidAuthKitUser, UserIn, HasAuthKitRole, And
from endotools.lib.usuarios.seguridad import roles

log = logging.getLogger(__name__)


class GruposcamposController(GenericRESTController):

	def __init__(self, *args, **kwargs):
		GenericRESTController.__init__(self, *args, **kwargs)
		self.tabla = GrupoCampos
		self.nombre_recurso = 'grupoCampos'
		self.nombre_recursos = 'gruposCampos'
		self.campos_index = ('id', 'nombre', 'columnas')
		self.campo_orderby = GrupoCampos.nombre

	@authorize(RemoteUser())
	def index(self, format='xml'):
		return GenericRESTController.index(self, format)

	@authorize(RemoteUser())
	def show(self, id, format='xml'):
		return GenericRESTController.show(self, id, format)

	@authorize(HasAuthKitRole([roles.admin_tipos_exploracion]))
	def update(self, id):
		return GenericRESTController.update(self, id)

	@authorize(HasAuthKitRole([roles.admin_tipos_exploracion]))
	def create(self, format='xml'):
		return GenericRESTController.create(self, format)

	@authorize(HasAuthKitRole([roles.admin_tipos_exploracion]))
	def delete(self, id):
		return GenericRESTController.delete(self, id)

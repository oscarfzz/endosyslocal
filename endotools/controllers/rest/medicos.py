##XXX   Tendria que ir vinculado a la gestion de usuarios

import logging
from pylons.i18n import _
from endotools.model.medicos import Medico
from xml.etree.ElementTree import Element, SubElement, tostring

from endotools.lib.genericREST import *

from authkit.authorize.pylons_adaptors import authorize
from authkit.permissions import RemoteUser, ValidAuthKitUser, UserIn, HasAuthKitRole, And
from endotools.lib.usuarios.seguridad import roles

log = logging.getLogger(__name__)

class MedicosController(GenericRESTController):

	def __init__(self, *args, **kwargs):
		GenericRESTController.__init__(self, *args, **kwargs)
		self.tabla = Medico
		self.nombre_recurso = 'medico'
		self.nombre_recursos = 'medicos'
		self.campos_index = ('user_uid', 'nombre')
		self.campo_orderby = Medico.nombre

	@authorize(RemoteUser())
	def index(self, format='xml'):
		return GenericRESTController.index(self, format)

	def _return_show(self, medico, data):
		data['usuario_id'] = formatea_valor(medico.username)

	@authorize(RemoteUser())
	def show(self, id, format='xml'):
		return GenericRESTController.show(self, id, format)

	def update(self, id):
		response.status_code = 405
		return _('ERROR: No se puede modificar un medico')#IDIOMAOK

	def create(self):
		response.status_code = 405
		return _('ERROR: No se puede crear un medico directamente (usar gestion de usuarios)')#IDIOMAOK

	def delete(self, id):
		response.status_code = 405
		return _('ERROR: No se puede eliminar un medico')#IDIOMAOK

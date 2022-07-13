import logging
from pylons.i18n import _
from endotools.model.centros import Centro
from xml.etree.ElementTree import Element, SubElement, tostring

#from endotools.lib.base import *
from endotools.lib.genericREST import *

from authkit.authorize.pylons_adaptors import authorize
from authkit.permissions import RemoteUser, ValidAuthKitUser, UserIn, HasAuthKitRole, And
from endotools.lib.usuarios.seguridad import roles

log = logging.getLogger(__name__)


class CentrosController(GenericRESTController):

	def __init__(self, *args, **kwargs):
		GenericRESTController.__init__(self, *args, **kwargs)
		self.tabla = Centro
		self.nombre_recurso = 'centro'
		self.nombre_recursos = 'centros'
		self.campos_index = ('id', 'codigo', 'nombre')
		self.campo_orderby = Centro.nombre

	@authorize(RemoteUser())
	def index(self, format='xml'):
		return self._doIndex(request.params, format)

	def _return_doIndex(self, registros, data, format):
		"""
		amplia la info del centro con los servicios
		"""
		for centro in registros:
			a = filter(lambda i: str(i['id']) == str(centro.id), data)
			if len(a) > 0:
				centro_el = a[0]
				# SERVICIOS
				centro_el['servicios'] = []
				for servicio in centro.servicios:
					centro_el['servicios'].append({
						'id': formatea_valor(servicio.id),
                        'nombre': formatea_valor(servicio.nombre)
					})
		return data


	@authorize(RemoteUser())
	def show(self, id, format='xml'):
		return GenericRESTController.show(self, id, format)


	@authorize(HasAuthKitRole([roles.admin_organizacion]))
	def update(self, id):
#		response.status_code = 405
#		return "ERROR: No se puede modificar un centro"
		return GenericRESTController.update(self, id)

	@authorize(HasAuthKitRole([roles.admin_organizacion]))
	def create(self, format='xml'):
		return GenericRESTController.create(self, format)

	@authorize(HasAuthKitRole([roles.admin_organizacion]))
	def delete(self, id):
		import endotools.lib.organizacion_centros
		endotools.lib.organizacion_centros.clear_defaults(centro_id = int(id), commit = False)
		return GenericRESTController.delete(self, id)

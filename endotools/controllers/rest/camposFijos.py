##XXX   Tendria que ir vinculado a la gestion de usuarios

import logging
from pylons.i18n import _
from xml.etree.ElementTree import Element, SubElement, tostring

from endotools.lib.genericREST import *

from authkit.authorize.pylons_adaptors import authorize
from authkit.permissions import RemoteUser, ValidAuthKitUser, UserIn, HasAuthKitRole, And
from endotools.lib.usuarios.seguridad import roles
from endotools.lib.busquedas import conjuntos
from endotools.lib.misc import obj_to_xml
import simplejson

log = logging.getLogger(__name__)

class CamposfijosController(BaseController):

	def __init__(self, *args, **kwargs):
		BaseController.__init__(self, *args, **kwargs)

	@authorize(RemoteUser())
	def index(self, format='xml'):

		data = []
		def procesa_campo(conjunto, campo):
			data.append({
				'id':				campo,
				'id_camp':			campo,
				'desc_camp':		conjuntos[conjunto].campos[campo].titulo,
				'id_conjunto':		conjunto,
				'desc_conjunto':	conjuntos[conjunto].descripcion,
				'nom_camp':			conjuntos[conjunto].campos[campo].nombre,
				'tipo_camp':		str(conjuntos[conjunto].campos[campo].tipo)
			})
		procesa_campo('PACIENTE', 'SEXO')
		procesa_campo('PACIENTE', 'POBLACION')
		procesa_campo('PACIENTE', 'PROVINCIA')
		procesa_campo('EXPLORACION', 'FECHA')
		procesa_campo('EXPLORACION', 'MEDICO')
		procesa_campo('EXPLORACION', 'TIPOEXPLORACION')
		procesa_campo('EXPLORACION', 'TIENE_IMAGENES')
		procesa_campo('EXPLORACION', 'SERVICIO')
		procesa_campo('EXPLORACION', 'EDAD_PACIENTE')
		procesa_campo('EXPLORACION', 'ASEGURADORA_ID')
		response.headers['cache-control'] = "no-cache, no-store, must-revalidate"
		if format == 'xml':
			response.content_type = "text/xml"
			return tostring(obj_to_xml(data, 'campoFijo', 'camposFijos'))
		elif format == 'json':
			response.content_type = 'application/json'
			return simplejson.dumps(data)


	@authorize(RemoteUser())
	def show(self, id, format='xml'):
		return ''

	def update(self, id):
		response.status_code = 405
		return _('ERROR: No se puede modificar un campo fijo')#IDIOMAOK

	def create(self):
		response.status_code = 405
		return _('ERROR: No se puede crear un campo fijo')#IDIOMAOk

	def delete(self, id):
		response.status_code = 405
		return _('ERROR: No se puede eliminar un campo fijo')#IDIOMAOk

import os
import logging
from pylons.i18n import _
from xml.etree.ElementTree import Element, SubElement, tostring

from endosys.lib.genericREST import *

from authkit.authorize.pylons_adaptors import authorize
from authkit.permissions import RemoteUser, ValidAuthKitUser, UserIn, HasAuthKitRole, And
from endosys.lib.usuarios.seguridad import roles
from pylons import config

import endosys.lib.informes
from endosys.lib.misc import *

log = logging.getLogger(__name__)

class PlantillasController(BaseController):

	def __init__(self, *args, **kwargs):
		BaseController.__init__(self, *args, **kwargs)

	@jsonify
	def _index_json(self):
		r = []
		exploracion_id = request.params.get('exploracion_id', None)
		exploracion_id = int(exploracion_id) if exploracion_id else None
		for plantilla in endosys.lib.informes.get_plantillas(exploracion_id):
			r.append({
				'plantilla': formatea_valor(plantilla)
			})
		return r

	@authorize(RemoteUser())
	def index(self, format='xml'):
		if format == 'xml':
			response.content_type = "text/xml"
			response.headers['cache-control'] = "no-cache, no-store, must-revalidate"
			root = Element('plantillas')

			exploracion_id = request.params.get('exploracion_id', None)
			exploracion_id = int(exploracion_id) if exploracion_id else None
			for plantilla in endosys.lib.informes.get_plantillas(exploracion_id):
				e = SubElement(root, 'plantilla')
				e.text = formatea_valor(plantilla)

			return tostring(root)

		elif format == 'json': return self._index_json()

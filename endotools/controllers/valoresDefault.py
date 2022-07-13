"""
Se iba a poner como controller REST, pero debido a que el funcionamiento debe ser
como un show, pero sin pasar un id (pues es automatico), ha parecido mas correcto
hacerlo como un controller normal.
"""
import os
import logging
from xml.etree.ElementTree import Element, SubElement, tostring
from endotools.lib.base import *
from endotools.lib.misc import *
from authkit.authorize.pylons_adaptors import authorize
from authkit.permissions import RemoteUser, ValidAuthKitUser, UserIn, HasAuthKitRole, And
import endotools.lib.organizacion_centros
from pylons import config
import endotools.lib.informes
import simplejson
from endotools.model.centros import Centro

log = logging.getLogger(__name__)

class ValoresdefaultController(BaseController):

	def __init__(self, *args, **kwargs):
		BaseController.__init__(self, *args, **kwargs)

	@authorize(RemoteUser())
	def index(self, format='xml'):
		"""
		obtiene algunos valores por defecto para el puesto/usuario:
			centro_id
			servicio_id
			agenda_id
		"""
		username =	request.environ.get('REMOTE_USER', None)
		ipaddress =	request.environ.get('REMOTE_ADDR', None)
		default = endotools.lib.organizacion_centros.get_default(username, ipaddress)

		centro = registro_by_id(Centro, default.get('centro_id', None) )
		centro_desc = None
		if centro:
			centro_desc = centro.nombre

		data = {
			'agenda_id':	formatea_valor_json(default.get('agenda_id', None)),
			'servicio_id':	formatea_valor_json(default.get('servicio_id', None)),
			'centro_id':	formatea_valor_json(default.get('centro_id', None)),
            'centro_desc':	formatea_valor_json(centro_desc)
		}

		# (sacado de genericREST/respuesta_doIndex)
		response.headers['cache-control'] = "no-cache, no-store, must-revalidate"
		if format == 'xml' or format == 'download':
			response.content_type = "text/xml"
			if format == 'download':
				response.headers.add('Content-Disposition', 'attachment;filename="%s.xml"' % self.nombre_recursos)
			return tostring(obj_to_xml(data, 'valoresDefault'))
		elif format == 'json':
			response.content_type = 'application/json'  # jQuery .ajax() funciona mejor con este MIME
			return simplejson.dumps(data)
		elif format == 'csv':
			response.content_type = 'text/csv'
			response.headers.add('Content-Disposition', 'attachment;filename="%s.csv"' % self.nombre_recursos)
			return obj_to_csv(data)


	@authorize(RemoteUser())
	def update(self):
		"""
		modifica algunos valores por defecto para el puesto/usuario. Se pasa
		mediante POST:
			centro_id
			servicio_id
			agenda_id
		"""
		agenda_id =		request.params.get('agenda_id', None)
		servicio_id =	request.params.get('servicio_id', None)
		centro_id =		request.params.get('centro_id', None)
		username =	request.environ.get('REMOTE_USER', None)
		ipaddress =	request.environ.get('REMOTE_ADDR', None)
		endotools.lib.organizacion_centros.set_default(username, ipaddress,
			agenda =	int(agenda_id) if agenda_id else None,
			servicio =	int(servicio_id) if servicio_id else None,
			centro =	int(centro_id) if centro_id else None
		)

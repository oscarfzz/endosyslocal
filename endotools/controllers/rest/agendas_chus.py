## lo hago que funcione SIEMPRE con un plugin...
## XXX repasar permisos...

import time
from datetime import date, timedelta

import logging
##from endotools.model.citas import Cita
from xml.etree.ElementTree import Element, SubElement, tostring

from endotools.lib.genericREST import *

from endotools.lib.base import *
from endotools.lib.misc import *
##from endotools.lib.genericREST import *

from authkit.authorize.pylons_adaptors import authorized, authorize, authorize_request, NotAuthorizedError
from authkit.permissions import RemoteUser, ValidAuthKitUser, UserIn, HasAuthKitRole, And
from endotools.lib.usuarios.seguridad import roles

from sqlalchemy.sql import and_

from endotools.lib.plugins.base import *
from endotools.config.plugins import pluginAgendas

log = logging.getLogger(__name__)

class AgendasChusController(GenericRESTController):

	def __init__(self, *args, **kwargs):
		GenericRESTController.__init__(self, *args, **kwargs)
##		self.tabla = Agenda
		self.nombre_recurso = 'agenda_chus'
		self.nombre_recursos = 'agendas_chus'
		self.campos_index = ('id', 'nombre', 'horamin', 'horamax', 'activa', 'codigo_servicio')



	def _doIndex(self, params, format='xml'):
		try:
			agendas = pluginAgendas.index(params)
		except E_NoEncontrado, e:
			log.error(e)
			abort_xml(404, 'No se ha encontrado ninguna agenda.', 2)
		except PluginException, e:
			log.error(e)
			abort_xml(e.http_status, str(e))
		except Exception, e:
			log.error(e)
			raise
			abort_xml(500, 'Ha ocurrido un error cargando las agendas (%s)' % e)

		# si no se encuentra ningun registro, devolver error 404
		if len(agendas) == 0: abort_xml(404, 'No se ha encontrado ninguna agenda', 2)

		data = self._crear_data(agendas, format, valid_fields=self.campos_index)
		data = self._return_doIndex(agendas, data, format)
		return self.respuesta_doIndex(agendas, data, format)




##		# solo formato XML
##		assert format == 'xml', 'El controlador solo permite el formato XML'
##
##		response.content_type = "text/xml"
##		response.headers['cache-control'] = "no-cache, no-store, must-revalidate"
##
##		root = Element(self.nombre_recursos)
##		for agenda in agendas:
##			e = SubElement(root, self.nombre_recurso, {
##						'id': formatea_valor(agenda.id),
##						'href': h.url_for('rest_' + self.nombre_recurso, id=agenda.id, format=format) })
##			SubElement(e, 'nombre').text = formatea_valor(agenda.nombre)
##			SubElement(e, 'horamin').text = formatea_valor(agenda.horamin)  # XXX horamin y horamax puede que lo quite
##			SubElement(e, 'horamax').text = formatea_valor(agenda.horamax)  # de aqui y lo ponga solo en el Show
##
##			# XXX   para la integración de SIHGA, se devuelve también el codigo del servicio
##			SubElement(e, 'servicio_id').text = formatea_valor(agenda.codigo_servicio)
##
##		return tostring(root)


	@authorize(RemoteUser())
	def index(self, format='xml'):
		p = request.params
		return self._doIndex(p, format)




##	def _construir_xml_show(self, agenda, root):
##		root.attrib['id'] = formatea_valor( agenda.id )
##		SubElement(root, 'nombre').text = formatea_valor(agenda.nombre)
##		SubElement(root, 'horamin').text = formatea_valor(agenda.horamin)
##		SubElement(root, 'horamax').text = formatea_valor(agenda.horamax)
##		SubElement(root, 'activa').text = formatea_valor(agenda.activa)
##
##		# XXX   para la integración de SIHGA, se devuelve tambien las prestaciones de la agenda
##		#	   y el codigo del servicio
##		SubElement(root, 'servicio_id').text = formatea_valor(agenda.codigo_servicio)
##		if agenda.prestaciones:
##			prestaciones = SubElement( root, 'prestaciones')
##			for p in agenda.prestaciones:
##				prestacion = SubElement( prestaciones, 'prestacion', {'id': formatea_valor(p.id)} )
##				SubElement(prestacion, 'id').text = formatea_valor(p.id)
##				SubElement(prestacion, 'descripcion').text = formatea_valor(p.descripcion)
##				SubElement(prestacion, 'tipoExploracion_id').text = formatea_valor(p.tipoExploracion_id)


	def _return_show(self, registro, data):
		""" Procesar la lista de Prestaciones """
		if registro.prestaciones:
			data['prestaciones'] = []
			for p in registro.prestaciones:
				o = {}
				for c, v in vars(p).iteritems():
					if c == 'id':
						o[c] = formatea_valor_json( v )
					elif not(c.startswith('_')):
						o[c] = formatea_valor_json( v )
				data['prestaciones'].append(o)


	@authorize(RemoteUser())
	def show(self, id, format='xml'):
		try:
			agenda = pluginAgendas.show(id)
		except PluginException, e:
			log.error(e)
			abort_xml(e.http_status, str(e))
		except Exception, e:
			log.error(e)
			abort_xml(500, 'Ha ocurrido un error cargando la agenda (%s)' % e)

		if not agenda: abort_xml(404, _('No se ha encontrado la agenda'), 2)#IDIOMAOK

		agenda2 = self._crear_data(agenda, format, valid_fields=self.campos_show)
		self._return_show(agenda, agenda2)
		return self.respuesta_show(None, agenda2, format)
			
##		# solo formato XML
##		assert format == 'xml', 'El controlador solo permite el formato XML'
##
##		response.content_type = "text/xml"
##		root = Element(self.nombre_recurso)
##		self._construir_xml_show(agenda, root)
##		return tostring(root)





	@authorize(RemoteUser())
	def update(self, id):
		agenda = pluginAgendas.agenda_from_params(request.params)
		try:
			pluginAgendas.update(id, agenda)
		except PluginException, e:
			log.error(e)
			abort_xml(e.http_status, str(e))
		except Exception, e:
			log.error(e)
			abort_xml(500, 'Ha ocurrido un error modificando la agenda (%s)' % e)




	def _doCreate(self, params):
		try:
			agenda = pluginAgendas.create(params)
		except PluginException, e:
			log.error(e)
			abort_xml(e.http_status, str(e))
		except Exception, e:
			log.error(e)
			abort_xml(500, 'Ha ocurrido un error creando la agenda (%s)' % e)

		response.status_code = 201
		#   devolver como xml
		response.content_type = "text/xml"
		root = Element(self.nombre_recurso)
		root.attrib['id'] = formatea_valor(agenda.id)
		return tostring(root)


	@authorize(RemoteUser())
	def create(self):
		return BaseController.create(self)




	@authorize(RemoteUser())
	def delete(self, id):
		try:
			pluginAgendas.delete(id)
		except PluginException, e:
			log.error(e)
			abort_xml(e.http_status, str(e))
		except Exception, e:
			log.error(e)
			abort_xml(500, 'Ha ocurrido un error eliminando la agenda (%s)' % e)

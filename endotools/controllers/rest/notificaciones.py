import logging
from pylons.i18n import _
from endotools.model import meta
from endotools.model.notificaciones import Notificacion
from endotools.model.medicos import Medico
from xml.etree.ElementTree import Element, SubElement, tostring
from endotools.lib.genericREST import *
from authkit.authorize.pylons_adaptors import authorize
from authkit.permissions import RemoteUser, ValidAuthKitUser, UserIn, HasAuthKitRole, And
from endotools.lib.usuarios.seguridad import roles
from endotools.lib.notificaciones import *
from sqlalchemy.sql import and_
log = logging.getLogger(__name__)
import os
import re



class NotificacionesController(GenericRESTController):

	def __init__(self, *args, **kwargs):
		GenericRESTController.__init__(self, *args, **kwargs)
		self.tabla = Notificacion
		self.nombre_recurso = 'notificacion'
		self.nombre_recursos = 'notificaciones'
		self.campos_index = ('id','username_origen','username_destino','fecha','hora','tipo_notificacion','contenido','leida','importante')
		self.campo_orderby = Notificacion.id
		self.campo_orderby_tipo = "DESC"

	#@authorize(RemoteUser())
	#def index(self, format='xml'):
	#	return GenericRESTController.index(self, format)

	def _filtrar_index(self, query, format='html'):
		username = request.environ.get('REMOTE_USER', None)
		query = query.filter(and_(self.tabla.username_destino==username))
		return query

	#antes de modificar una notificacion, verifica que sea del usuario a la que le pertenece
	def _es_propietario(self,id):
		username = request.environ.get('REMOTE_USER', None)
		q = meta.Session.query(self.tabla).filter(and_(self.tabla.id == id,self.tabla.username_destino == username))
		total = q.count()
		return total

	@conditional_authorize(RemoteUser())
	def update(self, id):

		if not self._es_propietario(id):
			response.status_code = 405
			return _('ERROR: No se puede modificar la tarea')
		else:
			return super(NotificacionesController, self).update(id)	

	@conditional_authorize(RemoteUser())
	def delete(self,id):
		if not self._es_propietario(id):
			response.status_code = 405
			return _('ERROR: No se puede eliminar la tarea')
		else:
			return super(NotificacionesController, self).delete(id)
	

	def _basic_sanitize(self, contenido):
		pattern = re.compile(r'\s?on\w+="[^"]+"\s?')
		result = re.sub(pattern, "", contenido) 
		pattern2 = re.compile(r'<script[\s\S]+?/script>')
		result = re.sub(pattern2, "", result)
		pattern3 = re.compile(r'<iframe[\s\S]+?/iframe>')
		result = re.sub(pattern2, "", result)
		return result

	def _doCreate(self, params, format='xml'):
		username = request.environ.get('REMOTE_USER', None)
		
		#comprobaciones
		try:
			tipo = params['tipo_notificacion']
		except Exception as e:
			log.error(e)
			raise Exception("No se especifico el tipo de notificacion (parametro: tipo_notificacion)")

		try:
			contenido = params['contenido']
		except Exception as e:
			log.error(e)
			raise Exception("La notificacion no tiene contenido (parametro: contenido)")

		contenido = self._basic_sanitize(contenido)

		if 'usuarios_destino' in params:
			usuarios_destino = params['usuarios_destino']
			usuarios_destino = usuarios_destino.split(",")

		notificacion=None
		#envio a muchos usuarios
		if usuarios_destino: # si hay contenido aqui => envio a muchos usuarios
			data = []
			if username.upper() == "SYSADMIN": # Solo el admin puede
				log.debug("permisos para crear")
				for user_id in usuarios_destino:
					q = meta.Session.query(Medico).filter( Medico.id == user_id )
					if q.count(): #existe
						
						user_destino = q.one()
						notificacion = nueva_notificacion(username_destino=user_destino.username,tipo_notificacion=tipo,contenido=contenido)
						notificacion.username_origen = username

						if 'importante' in params:
							notificacion.importante = params['importante']

						meta.Session.update(notificacion)
						meta.Session.commit()

						data.append({ 'id': formatea_valor_json(notificacion.id) })
			else:
				response.status_code = 405
				return _('ERROR: No puede crear mensajes')

 		
 		# envia a un solo usuario
		else:
			notificacion = nueva_notificacion(username_destino=username,tipo_notificacion=tipo,contenido=contenido)
			#   devolver como xml o json
			data = { 'id': formatea_valor_json(notificacion.id) }

		data = self._return_doCreate(notificacion, data)	
		response.status_code = 201
		if format == 'xml':
			response.content_type = "text/xml"
			return tostring(obj_to_xml(data, self.nombre_recurso))
		elif format == 'json':
			response.content_type = 'application/json'
			return simplejson.dumps(data)
	
import logging
from pylons.i18n import _
from endosys.model import meta
from endosys.model.tareas import Tarea
from xml.etree.ElementTree import Element, SubElement, tostring

from endosys.lib.genericREST import *

from authkit.authorize.pylons_adaptors import authorize
from authkit.permissions import RemoteUser, ValidAuthKitUser, UserIn, HasAuthKitRole, And
from endosys.lib.usuarios.seguridad import roles
from endosys.lib.tareas import *
import os
from sqlalchemy.sql import and_, or_
import threading

log = logging.getLogger(__name__)

class TareasController(GenericRESTController):

	def __init__(self, *args, **kwargs):
		GenericRESTController.__init__(self, *args, **kwargs)
		self.tabla = Tarea
		self.nombre_recurso = 'tarea'
		self.nombre_recursos = 'tareas'
		self.campos_index = ('id','fecha_comienzo','hora_comienzo','fecha_fin','hora_fin','estado', 'descripcion','resultado','descargable','username')
		self.campo_orderby = Tarea.id
		self.campo_orderby_tipo = "DESC"

	def _content_type(self, archivo):
		#si se quiere agregar uno mas 
		#http://www.iana.org/assignments/media-types/media-types.xhtml
		ext = archivo.split(".")[-1].upper()
		if ext == '.CSV': return "text/csv"
		elif ext == '.xls': return "application/vnd.ms-excel"
		else: return 'application/octet-stream'

	#poner en el lib/misc
	def _binfileiter(self, filename):
		"""
		para no cargar todo un fichero en memoria (con MPGs se colgara)
		crear un iterador y usarlo para la descarga
		"""
		size = 1*1024*1024 # paquetes de 1 MB...
		f = file(filename, 'rb')
		try:
			while True:
				buffer = f.read(size)
				if buffer:
					yield buffer
				else:
					break
		finally:
			f.close()

	def _es_propietario(self,id):
		username = request.environ.get('REMOTE_USER', None)
		q = meta.Session.query(self.tabla).filter(and_(self.tabla.id == id,self.tabla.username == username))
		total = q.count()
		return total


	def delete(self,id):

		username = request.environ.get('REMOTE_USER', None)
		if self._es_propietario(id) or username.upper() == "SYSADMIN":
			'''
			for t in threading.enumerate():
				if t.name==str(id):
			'''		

			return super(TareasController, self).delete(id)
		else:
			response.status_code = 405
			return _('ERROR: No se puede eliminar la tarea')

	def _deleted(self, registro):
		#borrar el archivo generado si es que tiene datos
		if registro.descargable:
			ruta = 'data/ficheros/' + registro.resultado
			eliminar_archivo(ruta)
		
	@authorize(RemoteUser())
	def index(self, format='xml'):
		return GenericRESTController.index(self, format)

	def _filtrar_index(self, query, format='html'):
		username = request.environ.get('REMOTE_USER', None)
		if username.upper() != "SYSADMIN":
			query = query.filter(and_(self.tabla.username==username))
		return query

	def _return_show(self, tarea, data):
		pass

	@authorize(RemoteUser())
	def show(self, id, format='xml'):

		tarea = self._registro_by_id(id)
		#si es descargable me quedo con la extension
		if tarea.descargable:
			if format=="xml" or format=="json":
				return GenericRESTController.show(self, id, format)
			else:
				resultado = tarea.resultado
				archivo = "data/ficheros/"+resultado
				ext = archivo.split(".")[-1].upper()
				if ext==format.upper():
					if os.path.exists(archivo):
						response.content_type = self._content_type(archivo)
						response.headers['content-length'] = os.path.getsize(archivo)
						return self._binfileiter(archivo)
					else: #no existe fisicamente el archivo
						response.status_code = 400
						return _('ERROR: El archivo solicitado no existe')
				else: #se pidio de un formato que no puede ser entregado
					response.status_code = 400	
					return _('ERROR: El archivo solicitado no existe')
		else:
			return GenericRESTController.show(self, id, format)

	@authorize(RemoteUser())
	def update(self, id):
		response.status_code = 405
		return _('ERROR: No se puede modificar una tarea')


	def _doCreate(self, params, format='xml'):
		#crea una nueva tarea para ese username
		#todo comprobar username
		username = request.environ.get('REMOTE_USER', None)
		
		#2.4.10.2 Fix para que no se creen muchas tareas y se queden procesando en el servidor 
		# 		  y produzca un crecimiento de memoria
		# TODO: Mejorar y hacer una cola de tareas
		q = meta.Session.query(self.tabla).filter(or_(self.tabla.estado == 1,self.tabla.estado == 0)) 
		if q.count() > 0:
			abort_json(400,_(u'No es posible iniciar la tarea porque hay una en curso'))#IDIOMAOK
			#raise Exception(_('No es posible iniciar la tarea porque hay una en curso'))

		try:
			tipo = params['tipo_tarea']
		except Exception as e:
			log.error(e)
			raise Exception("No se especifico el tipo de tarea (parametro: tipo_tarea)")

		tarea = nueva_tarea(username,tipo)

		#crea el hilo para realizar la tarea
		crear_hilo(tarea,params)

		#   devolver como xml o json
		data = { 'id': formatea_valor_json(tarea.id) }
		data = self._return_doCreate(tarea, data)
		response.status_code = 201
		if format == 'xml':
			response.content_type = "text/xml"
			return tostring(obj_to_xml(data, self.nombre_recurso))
		elif format == 'json':
			response.content_type = 'application/json'
			return simplejson.dumps(data)
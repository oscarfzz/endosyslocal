import logging
from xml.etree.ElementTree import Element, SubElement, tostring

from pylons.i18n import _
from sqlalchemy.sql import and_, or_
from authkit.authorize.pylons_adaptors import authorize
from authkit.permissions import RemoteUser, ValidAuthKitUser, UserIn, HasAuthKitRole, And

from endosys.lib.genericREST import *
from endosys.model import meta
from endosys.model.textosPredefinidos import TextoPredefinido
from endosys.lib.usuarios.seguridad import roles
from endosys.lib.plugins.base import *
from endosys.config.plugins import pluginCampos

log = logging.getLogger(__name__)


class PredefinidosController(GenericRESTController):

	def __init__(self, *args, **kwargs):
		GenericRESTController.__init__(self, *args, **kwargs)
		self.tabla = TextoPredefinido
		self.nombre_recurso = 'predefinido'
		self.nombre_recursos = 'predefinidos'
		self.campos_index = ('id', 'nombre', 'campo_id', 'activo', 'texto')
		self.campo_orderby = TextoPredefinido.nombre


	@authorize(RemoteUser())
	def index(self, campo_id=None, format='xml'):
		p = request.params
		if campo_id != None: p['campo_id'] = campo_id

		# si está el campo "activo", intenta pasarlo a INT (esperando 0 o 1),
		# ya que si no, al ser tipo BIT en BBDD, no lo reconoce bien
		if 'activo' in p:
			try:
				p['activo'] = int(p['activo'])
			except Exception as e:
				log.error(e)

		return self._doIndex(p, format)

	def _doIndex(self, params, format='xml'):
		activo_filter = params.pop('activo', None)
		print activo_filter
		self.activo_filter = (False if activo_filter == 'false' or activo_filter == 0 
							  else True if activo_filter == 'true' or activo_filter == 1
							  else None)
		return GenericRESTController._doIndex(self, params, format)
	
	def _filtrar_index(self, query, format='html'):
		activo_filter = self.__dict__.pop('activo_filter', None)
		if activo_filter != None:
			if activo_filter:
				query = query.filter(or_( self.tabla.activo == activo_filter, self.tabla.activo == None ))
			else:
				query = query.filter( self.tabla.activo == activo_filter)

		return query


	def _return_doIndex(self, registros, data, format):
		for d in data:
			if d['activo'] is None:
				d['activo'] = True
		return data

	@authorize(RemoteUser())
	def show(self, id, format='xml'):
		if format == 'txt':
			registro = self._registro_by_id(id)
			return formatea_valor(registro.texto)
		else:
			return GenericRESTController.show(self, id, format)
	
	def _return_show(self, registro, data):
		if data['activo'] is None:
			data['activo'] = True
		return data

##	@authorize(HasAuthKitRole([roles.crear_elementos]))
	@conditional_authorize(HasAuthKitRole([roles.crear_elementos, roles.baja_elementos]))
	def update(self, id, campo_id=None):
		#   no permitir modificar. Para dar de baja, ver mas abajo, en el delete
		#   XXX o permitir modificar solo si no se ha utilizado aun...
##		response.status_code = 405
##		return "ERROR: No se puede modificar un elemento"

		# XXX bueno... de momento si que lo permito, para que funcione tal como esta
		p = request.params
		if campo_id != None: p['campo_id'] = campo_id
		
		if 'nombre' in p:
			predefinido = self._registro_by_id(id)
			existe_elemento = meta.Session.query(TextoPredefinido).filter(TextoPredefinido.nombre == p["nombre"])
			existe_elemento = existe_elemento.filter(TextoPredefinido.campo_id == predefinido.campo_id)
			existe_elemento = existe_elemento.filter(TextoPredefinido.id!=id)
			if existe_elemento.count()>0:
				abort_json(400, _("Ya existe un texto predefinido con el mismo nombre"))

		self._update_registro_from_params( self._registro_by_id(id), p )
		meta.Session.commit()
		#return GenericRESTController.update(self, id)

	@authorize(HasAuthKitRole([roles.crear_elementos]))
	def create(self, campo_id=None, format='xml'):
		p = request.params

		if campo_id != None: p['campo_id'] = campo_id

		if 'nombre' in p:
			existe_elemento = meta.Session.query(TextoPredefinido).filter(TextoPredefinido.nombre == p["nombre"])
			existe_elemento = existe_elemento.filter(TextoPredefinido.campo_id == p["campo_id"])
			if existe_elemento.count()>0:
				abort_json(400, _("Ya existe un texto predefinido con el mismo nombre"))

		return self._doCreate(p, format)
		#return GenericRESTController.create(self)

	@authorize(HasAuthKitRole([roles.baja_elementos]))
	def delete(self, id):
		#   XXX aqui tendria que intentar eliminar, y si va ha sido utilizado, dar de baja
		return GenericRESTController.delete(self, id)

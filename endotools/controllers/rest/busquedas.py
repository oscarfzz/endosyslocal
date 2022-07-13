import logging
from endotools.model import meta
from endotools.model.busquedas import Busqueda
import xml.etree.ElementTree
from xml.etree.ElementTree import Element, SubElement, tostring

#from endotools.lib.base import *
from endotools.lib.genericREST import *

from authkit.authorize.pylons_adaptors import authorize
from authkit.permissions import RemoteUser, ValidAuthKitUser, UserIn, HasAuthKitRole, And
from endotools.lib.usuarios.seguridad import roles

import endotools.lib.busquedas

log = logging.getLogger(__name__)

class BusquedasController(GenericRESTController):

	def __init__(self, *args, **kwargs):
		GenericRESTController.__init__(self, *args, **kwargs)
		self.tabla = Busqueda
		self.nombre_recurso = 'busqueda'
		self.nombre_recursos = 'busquedas'
		self.campos_index = ('id', 'descripcion', 'nivel', 'username', 'servicio_id', 'comentario')
		self.campo_orderby = Busqueda.descripcion


	def _construir_xml_show(self, busqueda, root):
		# De momento se dejan las busquedas avanzadas como XML, ya que estan
		# guardadas asi en BBDD
		root.append( xml.etree.ElementTree.fromstring( formatea_valor( busqueda.xml ) ) )


	@authorize(RemoteUser())
	def show(self, id, format='xml'):
		return GenericRESTController.show(self, id, format)

	@authorize(RemoteUser())
	def _doIndex(self, params, format='xml'):
		return GenericRESTController._doIndex(self, params, format)

	@authorize(RemoteUser())
	def index(self, format='xml'):
		p = request.params

		self.mostrar_todos = True

		self.servicio_activo_id = None
		if "servicio_id" in p:
			self.mostrar_todos = False
			self.servicio_activo_id = p["servicio_id"]
			del p["servicio_id"]

		self.username = None
		if "username" in p:
			if p["username"] != "sysadmin":
				self.mostrar_todos = False
				self.username = p["username"]
			else:
				self.mostrar_todos = True
			del p["username"]

		return self._doIndex(p, format)
		#return GenericRESTController.index(self, format)

	def _filtrar_index(self, query, format=None):
		if not self.mostrar_todos:
			query = query.filter( or_(Busqueda.nivel == 0,
							  and_(Busqueda.nivel == 1, Busqueda.servicio_id == self.servicio_activo_id),
							  Busqueda.nivel == 2,
							  and_(Busqueda.nivel == 3, Busqueda.servicio_id == self.servicio_activo_id),
							  and_(Busqueda.nivel == 4, Busqueda.username == self.username)
							))

		return query

	@conditional_authorize(RemoteUser())
	def update(self, id):
		p = request.params
		if 'xml' in p:
			busqueda = endotools.lib.busquedas.Busqueda( request.params.get('xml', '') )
			p['xml'] =  busqueda.to_xml()
		self._update_registro_from_params( self._registro_by_id(id), p )
		meta.Session.commit()

	@conditional_authorize(RemoteUser())
	def create(self, format='xml'):
		p = request.params
		busqueda = endotools.lib.busquedas.Busqueda( request.params.get('xml', '') )
		p['xml'] =  busqueda.to_xml()
		return self._doCreate(p, format)

	@conditional_authorize(RemoteUser())
	def delete(self, id):
		return GenericRESTController.delete(self, id)

import logging
from pylons.i18n import _
from endosys.model import meta
from endosys.model.aseguradoras import Aseguradora
from endosys.model.pacientes import Paciente
from xml.etree.ElementTree import Element, SubElement, tostring

from endosys.lib.genericREST import *
from sqlalchemy.sql import and_, or_

from authkit.authorize.pylons_adaptors import authorize
from authkit.permissions import RemoteUser, ValidAuthKitUser, UserIn, HasAuthKitRole, And
from endosys.lib.usuarios.seguridad import roles

log = logging.getLogger(__name__)

class AseguradorasController(GenericRESTController):

	def __init__(self, *args, **kwargs):
		GenericRESTController.__init__(self, *args, **kwargs)
		self.tabla = Aseguradora
		self.nombre_recurso = 'aseguradora'
		self.nombre_recursos = 'aseguradoras'
		self.campos_index = ('id', 'nombre', 'activo')
		self.campos_orderby = Aseguradora.nombre

	@authorize(RemoteUser())
	def index(self, format='xml'):
		p = request.params

		if 'activo' in p:
			self.activo = int(p['activo'])
			del(p['activo'])
		else:
			self.activo = None
		return self._doIndex(p, format)

	def _filtrar_index(self, query, format= None):

		if self.activo != None:
			if self.activo == True:
				query = query.filter(or_( model.Aseguradora.activo == self.activo, model.Aseguradora.activo == None ))
			else:
				query = query.filter( Aseguradora.activo == self.activo)

		##query = query.order_by(model.Aseguradora.nombre)

		return query

	@authorize(RemoteUser())
	def show(self, id, format='xml'):
		return GenericRESTController.show(self, id, format)

	@conditional_authorize(HasAuthKitRole([roles.baja_elementos, roles.crear_elementos]))
	def update(self, id):
		##solamente se permite modificar el activo
		if 'nombre' in request.params:
			raise NotAuthorizedError

		return GenericRESTController.update(self, id)
##		return GenericRESTController.update(self, id)

	@authorize(HasAuthKitRole([roles.crear_elementos]))
	def create(self,format='xml'):
		p = request.params
		return GenericRESTController._doCreate(self, p, format)
		##return GenericRESTController.create(self)

	@authorize(HasAuthKitRole([roles.baja_elementos]))
	def delete(self, id):
		#obtener el elmento
		aseguradora = meta.Session.query(Aseguradora).filter(Aseguradora.id == id).one()
		nombre = unicode(aseguradora.nombre,errors='ignore')

		# checkear si esta siendo utilizado en ValorMulti y ValorSelec
		q = meta.Session.query(Paciente).filter(Paciente.aseguradora_id == id)
		cant = q.count()
		#si tiene elementos no se puede eliminar
		if cant:
			# Envia el error 500 con el nombre,
			json = { 'nombre': nombre }
			abort_json(500, json)
		else:
			return GenericRESTController.delete(self, id)


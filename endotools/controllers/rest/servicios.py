import logging
from pylons.i18n import _
from endotools.model import meta
from endotools.model.servicios import Servicio
from endotools.model.salas import Rel_Salas_Servicios
from endotools.model.medicos import Rel_Medicos_Servicios
from endotools.model.usuarios import get_usuario
from xml.etree.ElementTree import Element, SubElement, tostring

#from endotools.lib.base import *
from endotools.lib.genericREST import *

from authkit.authorize.pylons_adaptors import authorize
from authkit.permissions import RemoteUser, ValidAuthKitUser, UserIn, HasAuthKitRole, And
from endotools.lib.usuarios.seguridad import roles

log = logging.getLogger(__name__)


class ServiciosController(GenericRESTController):

	def __init__(self, *args, **kwargs):
		GenericRESTController.__init__(self, *args, **kwargs)
		self.tabla = Servicio
		self.nombre_recurso = 'servicio'
		self.nombre_recursos = 'servicios'
		self.campos_index = ('id', 'nombre', 'centro', 'codigo')
		# 19/10/2016: Se deja comentado porque no se probo lo suficientes.
		# 			  esta linea mejora la carga de las agendas, que en este momento esta tardando mucho
		# 			  hay que probar si poniendo esta linea afecta a otra parte del sistema
		# 			  (este es un comentario de nacho)
		self.campos_show = ('nombre', 'centro', 'codigo')
		self.campo_orderby = Servicio.nombre

	@authorize(RemoteUser())
	def index(self, format='xml'):
		return self._doIndex(request.params, format)

	def _return_doIndex(self, registros, data, format):
		"""
		amplia la info del servicio con las agendas
		"""
		for servicio in registros:
			a = filter(lambda i: str(i['id']) == str(servicio.id), data)
			if len(a) > 0:
				servicio_el = a[0]
				# AGENDAS
				servicio_el['agendas'] = []
				for agenda in servicio.agendas:
					servicio_el['agendas'].append({
						'id': formatea_valor(agenda.id),
						'nombre': formatea_valor(agenda.nombre)
					})
		return data


	@authorize(RemoteUser())
	def show(self, id, format='xml'):
		return GenericRESTController.show(self, id, format)

	def _return_show(self, servicio, data):
		data['salas'] = []
		for rel in servicio.salas:
			data['salas'].append({
				'id': formatea_valor(rel.sala.id),
				'nombre': formatea_valor(rel.sala.nombre),
				'centro_id': formatea_valor(rel.sala.centro_id)
			})

		data['medicos'] = []
		for rel in servicio.medicos:
			usuario = get_usuario(username=rel.medico.username)
			data['medicos'].append({
				'id': formatea_valor(rel.medico.id),
				'nombre': formatea_valor(rel.medico.nombre),
				'tipo': formatea_valor(usuario.tipo)
			})

	@authorize(HasAuthKitRole([roles.admin_organizacion]))
	def update(self, id):
		#   no permitir modificar. Para dar de baja, ver mas abajo, en el delete
		#   XXX o permitir modificar solo si no se ha utilizado aun...
		#response.status_code = 405
		#return "ERROR: No se puede modificar un elemento"


		"""
		Modifica un Medico.
		"servicios" es una lista de ids de servicios. Puede estar vacia.
		"""
		#   XXX si el medico ya tiene exploraciones no deberia poder renombrarse...
		servicio = registro_by_id(Servicio, id)
		if servicio is None:
			abort(404, _(u'No se encuentra el servicio indicado con id: %s') % id)#IDIOMAOK
		else:


			codigo = request.params.get('codigo', None)
			if codigo:
				servicio.codigo = codigo

			nombre = request.params.get('nombre', None)
			if nombre:
				servicio.nombre = nombre

			centro_id = request.params.get('centro_id', None)
			if centro_id:
				servicio.centro_id = centro_id

			self.guardar_salas_medicos(servicio)



			#extración de codigo



			meta.Session.update(servicio)
			try:
				meta.Session.commit()
			except IntegrityError as e:
				log.error(e)
				raise
				#abort(403, u"No se puede modificar el servicio")


		#return GenericRESTController.update(self, id)
	def guardar_salas_medicos(self, servicio):
		if 'salas' in request.params:
			salas = request.params['salas']

			if salas:
				salas = map(lambda s: int(s), salas.split(','))
			else:
				salas = []

			# quitar salas y asignar las nuevas
			for rel in servicio.salas:
				meta.Session.delete(rel)

			while len(servicio.salas) > 0: servicio.salas.pop()

			for sala_id in salas:
				rel = Rel_Salas_Servicios()
				servicio.salas.append(rel)
				rel.sala_id = sala_id
				rel.servicio_id = id


		if 'medicos' in request.params:
			medicos = request.params['medicos']

			if medicos:
				medicos = map(lambda s: int(s), medicos.split(','))
			else:
				medicos = []

			# quitar salas y asignar las nuevas
			for rel in servicio.medicos:
				meta.Session.delete(rel)

			while len(servicio.medicos) > 0: servicio.medicos.pop()

			#Session.commit()

			for medico_id in medicos:
				rel = Rel_Medicos_Servicios()
				servicio.medicos.append(rel)
				rel.medico_id = medico_id
				rel.servicio_id = id



	def _created(self, servicio):
		self.guardar_salas_medicos(servicio)

		#Session.update(servicio)
		try:
			meta.Session.commit()
		except IntegrityError as e:
			log.error(e)
			raise

	@authorize(HasAuthKitRole([roles.admin_organizacion]))
	def create(self,  format='xml'):
		return GenericRESTController.create(self,  format)

	@authorize(HasAuthKitRole([roles.admin_organizacion]))
	def delete(self, id):
		servicio = registro_by_id(Servicio, id)
		if servicio is None:
			abort(404, _(u'No se encuentra el servicio indicado con id: %s') % id)#IDIOMAOK
		else:
			# quitar salas asignadas al servicio
			for rel in servicio.salas:
				meta.Session.delete(rel)
			while len(servicio.salas) > 0: servicio.salas.pop()

			# quitar medicos asignadas al servicio
			for rel in servicio.medicos:
				meta.Session.delete(rel)
			while len(servicio.medicos) > 0: servicio.medicos.pop()

			import endotools.lib.organizacion_centros
			endotools.lib.organizacion_centros.clear_defaults(servicio_id = servicio.id, commit = False)

			meta.Session.delete( servicio )
			meta.Session.commit()

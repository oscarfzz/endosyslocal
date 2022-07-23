import logging
from pylons.i18n import _
from endosys.model import meta
from endosys.model.workstations import Workstation, Rel_Servicios_Workstations
from endosys.lib.genericREST import *
from authkit.authorize.pylons_adaptors import authorized, authorize, NotAuthorizedError, NotAuthenticatedError
from authkit.permissions import RemoteUser, ValidAuthKitUser, UserIn, HasAuthKitRole, And
from endosys.lib.usuarios.seguridad import roles
from endosys.lib.organizacion_centros import get_workstation
from pylons import config
from sqlalchemy import or_, and_
from endosys.lib.misc import *
log = logging.getLogger(__name__)

class WorkstationsController(GenericRESTController):

	def __init__(self, *args, **kwargs):
		GenericRESTController.__init__(self, *args, **kwargs)
		self.tabla = Workstation
		self.nombre_recurso = 'workstation'
		self.nombre_recursos = 'workstations'
		self.campos_index = ('id', 'nombre', 'ip', 'nombre_equipo', 'tipo')
		self.campos_show = ('id', 'nombre', 'ip', 'nombre_equipo', 'tipo', 'servicios', 'borrado_motivo', 'borrado')
		self.campo_orderby = Workstation.nombre


	@authorize(RemoteUser())
	def index(self, format='xml'):
		return GenericRESTController.index(self, format)


	def show(self, id, format='xml'):
		"""
		Si id='auto', entonces se busca por la IP del cliente. 
		Para esto no hace falta estar autenticado.
		"""
		if id == 'auto':
			ipaddress =	obtener_request_ip(request)
			workstation = get_workstation(ip=ipaddress)
			if workstation:
				id = workstation.id
			else:
				id = -1 # para que falle el GenericRESTController.show()
		else:
			if not authorized(RemoteUser()): raise NotAuthenticatedError

		return GenericRESTController.show(self, id, format)

	def _return_show(self, workstation, data):
		# añadir la info de los servicios asignados al centro
		data['servicios'] = []
		for rel in workstation.servicios:
			data['servicios'].append({
				'id': formatea_valor(rel.servicio.id),
				'codigo': formatea_valor(rel.servicio.codigo),
				'nombre': formatea_valor(rel.servicio.nombre),
				'centro_id': formatea_valor(rel.servicio.centro_id)
			})

	@authorize(HasAuthKitRole([roles.admin_organizacion]))
##	@authorize(RemoteUser())
	def update(self, id):
		"""
		Modifica un Workstation. params: nombre, ip, tipo, servicios
		"servicios" es una lista de ids de servicios. Puede estar vacia.
		"""
		workstation = registro_by_id(Workstation, id)
		
		# comrobacion de que exista
		if workstation is None:
			abort_json(404, _(u'No se encuentra el Puesto indicado con id: %s') % id)#IDIOMAOK

		# comprobacion de que no este borrado
		if workstation.borrado == True:
			abort_json(400, _(u'El puesto que desea modificar esta borrado'))#IDIOMAOK

		# comprobacion de que la ip no este usada por otro puesto
		workstation_ip = request.params['ip'] or None # Usar None en vez de, por ejemplo, cadena vacía
		#comprobar que esa ip no este usada por otro workstation
		if workstation_ip is not None:
			workstations = meta.Session.query(Workstation).filter(Workstation.ip == workstation_ip).filter(Workstation.id != id)
			# solo busca en las que no estan borradas
			workstations = workstations.filter(and_(or_(Workstation.borrado == 0, Workstation.borrado == None)))
			if workstations.count() > 0:
				abort_json(400, _(u'El IP que desea asignar ya esta en uso por otro puesto'))#IDIOMAOK
		
		# realiza el guardao
		nombre = request.params.get('nombre', None)
		if nombre: workstation.nombre = nombre

		if 'ip' in request.params:
			workstation.ip = workstation_ip
			
		tipo = request.params.get('tipo', None)
		if tipo: workstation.tipo = tipo

		nombre_equipo = request.params.get('nombre_equipo', None)
		if nombre_equipo: workstation.nombre_equipo = nombre_equipo

		self._guardar_servicios(workstation)

		meta.Session.update(workstation)
		try:
			meta.Session.commit()
		except IntegrityError as e:
			log.error(e)
			# seria raro que ingrese aqui
			abort_json(400, _(u'A ocurrido un error de integridad referencial.'))#IDIOMAOK


	def _guardar_servicios(self, workstation):
		if 'servicios' in request.params:
			servicios = request.params['servicios']
			servicios = map(lambda s: int(s), servicios.split(',')) if servicios else []

			# quitar servicios y asignar los nuevos
			for rel in workstation.servicios: meta.Session.delete(rel)
			while len(workstation.servicios) > 0: workstation.servicios.pop()
			for servicio_id in servicios:
				rel = Rel_Servicios_Workstations()
				workstation.servicios.append(rel)
				rel.servicio_id = servicio_id
				rel.workstation_id = id


##	@authorize(HasAuthKitRole([roles.admin_tipos_exploracion]))
	@authorize(RemoteUser())
	def create(self, format='xml'):
		p = request.params
		print(p)

		comprobacion_por_nombre_equipo = config.get('WORKSTATIONS.COMPROBACION_POR_NOMBRE_EQUIPO', '0')
		comprobacion_por_ip = config.get('WORKSTATIONS.COMPROBACION_POR_IP', '1')

		if comprobacion_por_nombre_equipo == '1':
			import os
			nombre_equipo = os.environ['COMPUTERNAME']
			p['nombre_equipo'] = nombre_equipo
			print(nombre_equipo)
			workstations = meta.Session.query(Workstation).filter(
				and_(Workstation.nombre_equipo == nombre_equipo, or_(Workstation.borrado == 0, Workstation.borrado == None)))
			if workstations.count() > 0:
				abort_json(400, _(u'El nombre del equipo que desea asignar ya esta en uso por otro puesto'))#IDIOMAOK


		elif comprobacion_por_ip == '1':
			# Si no se proporciona una IP, se da por hecho que ha de usar la del client conectacto,
			# es decir, que se está registrando.
			if not 'ip' in p:
				p['ip'] = obtener_request_ip(request)
				
			# Otro caso distinto es si se proporciona el parametro IP vacío (ip=''), que significa
			# que se trata del Workstation "por defecto" y se asignará NULL
			if p['ip'] == '':
				if not(config.get("WORKSTATIONS.PERMITIR_SIN_IP", '0') == '1'):
					abort_json(400, _(u'No se permite la creación de un Workstation por defecto'))
			else:
				# #comprobar que esa ip no este usada por otro workstation
				workstation_ip = p['ip'] or None # Usar None en vez de, por ejemplo, cadena vacía
				if workstation_ip is not None:
					workstations = meta.Session.query(Workstation).filter(and_(Workstation.ip == workstation_ip, or_(Workstation.borrado == 0, Workstation.borrado == None)))
					if workstations.count() > 0:
						abort_json(400, _(u'El IP que desea asignar ya esta en uso por otro puesto'))#IDIOMAOK

		return self._doCreate(p, format)


	def _created(self, workstation):
		self._guardar_servicios(workstation)

		meta.Session.update(workstation)
		try:
			meta.Session.commit()
		except IntegrityError as e:
			log.error(e)
			raise

	@authorize(HasAuthKitRole([roles.admin_tipos_exploracion]))
	def delete(self, id):
		workstation = self._registro_by_id(id)
		
		if 'borrado_motivo' not in request.params or len(request.params["borrado_motivo"].strip())==0:
			abort_json(400, _(u'No se ha indicado el motivo de borrado.'))#IDIOMAOK

		workstation.borrado_motivo = request.params["borrado_motivo"].strip()
		workstation.borrado = 1
		meta.Session.update(workstation)
		meta.Session.commit()
		#return GenericRESTController.delete(self, id)

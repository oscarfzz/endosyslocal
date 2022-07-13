"""
XXX de momento esta hecho de manera que el update recibe un solo servicio,
aunque ya utiliza el nuevo modelo de datos de relacion medicos - servicios N:N
Esto es asi para mantener la compatibilidad con la gestión de usuarios actual
por web.
"""
import os
import logging

from paste import request
from pylons.i18n import _
from endotools.model import meta
from xml.etree.ElementTree import Element, SubElement, tostring

from endotools.lib.genericREST import *

from authkit.authorize.pylons_adaptors import authorized, authorize
from authkit.permissions import RemoteUser, ValidAuthKitUser, UserIn, HasAuthKitRole, And
from authkit.users.sqlalchemy_driver import UsersFromDatabase
from endotools.lib.usuarios.seguridad import roles, roles_details
from endotools.model.medicos import Medico, Rel_Medicos_Servicios, Rel_Medicos_Agendas, get_medico, medico_tiene_servicio
from endotools.model.usuarios import Usuario, get_usuario
from endotools.model.servicios import Servicio
from endotools.model.agendas import Agenda
from endotools.lib.misc import obj_to_xml
import simplejson
from sqlalchemy.orm import defer

log = logging.getLogger(__name__)

class UsuariosController(BaseController):

	def __init__(self, *args, **kwargs):
		BaseController.__init__(self, *args, **kwargs)

	@authorize(HasAuthKitRole([roles.admin_usuarios_restringido, roles.admin_usuarios]))
	def index(self, format='xml'):
	
		# construir con un formato base, con lists y dicts
		usuarios = []
		users = request.environ['authkit.users']
		for user in users.list_users():
			# usuario vinculado
			usuario = None
			activo = True
			ldap = True
			tipo = 0
			q = meta.Session.query(Usuario).filter(Usuario.username == user)
			if q.count():
				usuario = q.one()
				if usuario.activo != None:
					activo = usuario.activo
				else:
					activo = True

			# medico vinculado
			medico = None
			nombre = None
			q = meta.Session.query(Medico).filter(Medico.username == user)
			if q.count():
				medico = q.one()
				####
				if "servicios" in request.params: #Comprobamos si en el request.params estamos pasando los servicios
					servicios_ids = map(lambda item: int(item), request.params["servicios"].split(",")) #obtenemos una lista con los servicios
				
					ok = False
					for rel in medico.servicios:
						if rel.servicio.id in servicios_ids: #Si el servicio del request coincide con el servicio asignado a algunos de los médicos, saldremos del bucle 
							ok = True
							break
							
					if not ok: #Si no hay coincidencia seguiremos recorriendo la lista de usuarios
						continue
				####
				nombre = formatea_valor(medico.nombre)
				ldap = usuario.ldap
				tipo = str(usuario.tipo)

			usuarios.append({'id': formatea_valor(user),
							'nombre': nombre,
							'activo': activo,
							'ldap': ldap,
							'tipo' : tipo})

		response.headers['cache-control'] = "no-cache, no-store, must-revalidate"
		if format == 'xml':
			response.content_type = "text/xml"
			return tostring(obj_to_xml(usuarios, 'usuario', 'usuarios'))
		elif format == 'json':
			response.content_type = 'application/json'
			return simplejson.dumps(usuarios)

#@authorize(HasAuthKitRole([roles.admin_usuarios]))
	@authorize(RemoteUser())
	def show(self, id, format=''):
		"""
		OJO: Se da el caso especial de que el "id" es el nombre de usuario,
		y éste puede contener el caracter de punto ".". Esto causa que el
		controller interprete que se está indicando el formato, cuando realmente
		es parte del nombre de usuario.

		p.e: rest/usuarios/juan.perez

		"juan.perez" es el nombre de usuario, pero un controller interpreta
		que el id es "juan" y el format es "perez".

		Por eso se hace un tratamiento especial, ignorando el formato, y conca-
		tenandolo al id (el formato siempre es 'xml').

		PRUEBA: interpretar siempre como JSON
		"""

		if format: id = '.'.join( (id, format) )
		format = 'json'

		# si no tiene "admin_usuarios", permitir solo el usuario actual

		if not authorized(HasAuthKitRole([roles.admin_usuarios_restringido, roles.admin_usuarios])):
			if id.lower() != request.environ['REMOTE_USER'].lower(): # Los .lower(), que no estaban antes, arreglan el bug #452
				abort(403, _(u'No tiene permisos para consultar la información de otros usuarios'))#IDIOMAOK

		users = request.environ['authkit.users']

		# comprobar que exista el usuario
		if not users.user_exists(id):
			abort(404)

		# construir la respuesta
		# ###########################################################
		data = {
			'id': id,
			'permisos': []
		}

		# datos adicionales del usuario:
		usuario = None
		q = meta.Session.query(Usuario).filter( Usuario.username == id ).options(defer('clave'))
		if q.count():
			usuario = q.one()
			data['ldap'] = formatea_valor(usuario.ldap)
			data['tipo'] = formatea_valor(usuario.tipo if usuario.tipo != None else 0)
			data['activo'] = formatea_valor(usuario.activo if usuario.activo != None else True)
			if '_clave' in request.params and request.environ['REMOTE_USER'].upper() == "SYSADMIN":
				data['key'] = formatea_valor(usuario.clave)

		# medico vinculado
		medico = None
		q = meta.Session.query(Medico).filter(Medico.username == id)
		if q.count():
			medico = q.one()
			data['medico'] = {
				'id': formatea_valor(medico.id),
				'nombre': formatea_valor(medico.nombre),
				'apellido1': formatea_valor(medico.apellido1),
				'apellido2': formatea_valor(medico.apellido2),
				'colegiado': formatea_valor(medico.colegiado),
				'servicios': [],
				'agendas': []
			}

			# SERVICIOS DEL MEDICO
			for rel in medico.servicios:
				data['medico']['servicios'].append({
					'id': formatea_valor(rel.servicio.id),
					'nombre': formatea_valor(rel.servicio.nombre),
					'codigo': formatea_valor(rel.servicio.codigo),
					'centro_id': formatea_valor(rel.servicio.centro_id)
				})

			# AGENDAS DEL MEDICO
			for rel in medico.agendas:
				data['medico']['agendas'].append({
					'id': formatea_valor(rel.agenda.id),
					'nombre': formatea_valor( rel.agenda.nombre ),
					'codigo': formatea_valor( rel.agenda.codigo ),
					'servicio_id': formatea_valor( rel.agenda.servicio_id )
				})

		# permisos
		for role in users.user_roles(id):
			data['permisos'].append({
				'id': role,
				'nombre': formatea_valor( roles_details[role].nombre ),
				'descripcion': formatea_valor( roles_details[role].descripcion )
			})
		# ###########################################################

		response.headers['cache-control'] = "no-cache, no-store, must-revalidate"
		if format == 'xml':
			response.content_type = "text/xml"
			return tostring(obj_to_xml(data, 'usuario',
				collection_member={
					'permisos': 'permiso',
                    'servicios': 'servicio',
                    'agendas': 'agenda'
				}
			))

		if format == 'json':
			response.content_type = "application/json"
			return simplejson.dumps(data)


	@authorize( HasAuthKitRole([roles.admin_usuarios_restringido , roles.admin_usuarios]))
	def update(self, id, format=''):
		"""
		IMPORTANTE: Enviar siempre el "medico", ya que si no se elimina el registro de la tabla "Medicos"!
		
		parámetros:
			newid		nuevo nombre
			password	password
			permisos	role1,role2,role3...
			ldap		0|1
			medico		nombre del medico
			servicios	string separado por comas con los id de los servicios
						Es opcional, si no se indica no se cambian los servicios. puede ser vacio para indicar ninguno.
			agendas		string separado por comas con los id de las agendas
						Es opcional, si no se indica no se cambian las agendas. puede ser vacio para indicar ninguna.
			tipo		entero con el tipo de usuario (por ahora 0 para usuario y 1 para administradores).
			activo		0|1
			_clave		Si esta presente regenera la clave para la API Key (Solo sysadmin).

		parámetros ya no válidos:
			servicio	(desde 2.4.11.1)
			
		tratamiento especial de id y format, ver comentarios en show()
		"""

		if format: id = '.'.join( (id, format) )
		format = 'xml'

		users = request.environ['authkit.users']

		# NO PERMITIR MODIFICAR el usuario sysadmin por otro usuario que no sea el mismo (sysadmin)
		if id.upper() == "SYSADMIN" and not request.environ['REMOTE_USER'].upper() == "SYSADMIN":
			log.error("Error sysadmin")
			abort(403, _(u'El usuario sysadmin sólo se puede modificar por él mismo'))#IDIOMAOK
		# comprobar que exista el usuario
		if not users.user_exists(id):
			abort(404)
		# modificar password
		# XXX por seguridad, que solo pueda el propio usuario o un superadmin?
		if 'password' in request.params:
			users.user_set_password(id, request.params['password'])

		#procesar parametro ldap
		if 'ldap' in request.params:
			usuario = None
			q = meta.Session.query(Usuario).filter( Usuario.username == id )
			if q.count():
				usuario = q.one()
				if usuario is None:
					abort(404, _(u'No se encuentra el usuario en LDAP indicado con id: %s') % username)#IDIOMAOK
				else:
					usuario.username = id
					usuario.ldap = int(request.params['ldap'])
					meta.Session.update(usuario)
					try:
						meta.Session.commit()
					except IntegrityError as e:
						log.error(e)
						abort(403, _(u'No se puede modificar el usuario'))#IDIOMAOK
					#ldap = request.params['ldap']
					#self._modificar_usuario(usuario.username, request.params['ldap'] )

		# procesar parametro tipo
		if 'tipo' in request.params:
			usuario = get_usuario(username = id)
			if usuario is None:
				abort(404,
						_(
						u'No se encuentra el usuario indicado con id: %s') % id)  # IDIOMAOK
			else:
				usuario.tipo = int(request.params['tipo'])
				meta.Session.update(usuario)
				try:
					meta.Session.commit()
				except IntegrityError as e:
					log.error(e)
					abort(403, _(u'No se puede modificar el usuario'))  # IDIOMAOK

		# procesar parametro activo
		if 'activo' in request.params:
			# NO PERMITIR DESACTIVAR al usuario sysadmin
			if id.upper() == "SYSADMIN" and request.params['activo'] != "1":
				abort(403, _(u'El usuario sysadmin no se puede desactivar'))  # IDIOMAOK
			# No permitir desactivarse a uno mismo.
			if id.upper() == request.environ['REMOTE_USER'].upper() and request.params['activo'] != "1":
				abort(403, _(u'El usuario no se puede desactivar a si mismo'))
			usuario = get_usuario(username = id)
			if usuario is None:
				abort(404,
					  _(
						  u'No se encuentra el usuario indicado con id: %s') % id)  # IDIOMAOK
			else:
				# print("He entrado en el activo")
				usuario.activo = int(request.params['activo'])
				meta.Session.update(usuario)
				try:
					meta.Session.commit()
				except IntegrityError as e:
					log.error(e)
					abort(403, _(u'No se puede modificar el usuario'))  # IDIOMAOK

		# procesar el parametro
		if 'permisos' in request.params:
			if request.params['permisos']:
				permisos = request.params['permisos'].split(',')
			else:
				permisos = []
			self._procesar_permisos(id, permisos)

		# procesar parametro "medico":
		#   si no tiene, eliminar el medico asignado (si tenia)
		#   si tiene y no habia medico asignado, crear uno nuevo
		#   si tiene y es igual al asignado no hacer nada
		#   si tiene y es distinto al asignado, intentar renombrarlo
		medico = get_medico(username = id)
		if 'medico' in request.params:
			nombre_medico = request.params['medico']
			colegiado = request.params.get('colegiado', None)
			
			servicios = request.params.get('servicios', None)
			if servicios:
				if len(servicios) > 0:
					servicios = map(lambda s: int(s), servicios.split(','))
				else:
					servicios = []

			agendas = request.params.get('agendas', None)
			if agendas:
				if len(agendas) > 0:
					agendas = map(lambda s: int(s), agendas.split(','))
				else:
					agendas = []

			if not medico:
				self._crear_medico(id, nombre_medico, servicios, colegiado,agendas)
			else:
				self._modificar_medico(medico.id, id, nombre_medico, colegiado, servicios, agendas)
		else:
			if medico: self._eliminar_medico(medico.id)


		# modificar username
		# XXX por seguridad, que solo pueda el propio usuario o un superadmin?
		# XXX falta comprobar si ya existe un usuario con ese newid
		if 'newid' in request.params:
			if id != request.params['newid']:
				users.user_set_username(id, request.params['newid'])

		if '_clave' in request.params:
			if not request.environ['REMOTE_USER'].upper() == "SYSADMIN":
				log.error("Error sysadmin")
				abort(403, _(u'Solo sysadmin puede gestionar las claves API.'))  # IDIOMAOK
			else:
				# comprobar que exista el usuario
				if not users.user_exists(id):
					abort(404)
				# datos adicionales del usuario:
				q = meta.Session.query(Usuario).filter(Usuario.username == id)
				if q.count():
					usuario = q.one()
					if usuario is None:
						abort(404, _(u'No se encuentra el usuario LDAP indicado con id: %s') % id)  # IDIOMAOK
					else:
						import hashlib
						if request.params['_clave'] != "delete":
							usuario.clave = hashlib.sha224(usuario.username + str(datetime.datetime.now())).hexdigest()
						else:
							usuario.clave = None
						meta.Session.update(usuario)
						try:
							meta.Session.commit()
						except IntegrityError as e:
							log.error(e)
							abort(403, _(u'No se puede modificar el usuario'))  # IDIOMAOK


		meta.Session.commit()


	@authorize( HasAuthKitRole([roles.admin_usuarios_restringido , roles.admin_usuarios]))
	def create(self, format='json'):
		log.debug('usuarios create %s', format)
		# parametros:
		#   id=nombre
		#   password=password
		#   permisos=role1,role2,role3... (opcional)
		#   medico=nombre del medico (opcional)
		users = request.environ['authkit.users']

		# comprobar parametros (id y password obligatorios)
		if not set(('id', 'password')) <= set(request.params):
			abort(400)
		id = request.params['id']
		password = request.params['password']

		# comprobar que no exista el usuario
		if users.user_exists(id):
			abort(403)

		# crearlo
		users.user_create(id, password)
		meta.Session.commit()


		# datos adicionales del usuario:

		usuario = Usuario()
		usuario.username = id
		usuario.ldap = int (request.params['ldap'])
		usuario.tipo = int (request.params['tipo'])
		usuario.activo = int (request.params['activo'])

		meta.Session.save(usuario)
		meta.Session.commit()

		# procesar el parametro permisos si lo tiene
		if 'permisos' in request.params:
			if request.params['permisos']:
				permisos = request.params['permisos'].split(',')
			else:
				permisos = []
			self._procesar_permisos(id, permisos)

		# si tiene parametro "medico", crear un nuevo medico
		# asignado a este nuevo usuario
		if 'medico' in request.params:
			nombre_medico = request.params['medico']
			colegiado = request.params.get('colegiado', None)

			servicios = request.params.get('servicios', None) or request.params.get('servicio', None)
			if servicios:
				servicios = map(lambda s: int(s), servicios.split(','))

			agendas = request.params.get('agendas', None) or request.params.get('agendas', None)
			if agendas:
				agendas =  map(lambda s: int(s), agendas.split(','))
			self._crear_medico(id, nombre_medico, servicios, colegiado,agendas)

		#   devolver como xml o json
		data = { 'id': formatea_valor(id) }
##		response.status_code = 201
		if format == 'xml':
			response.content_type = "text/xml"
			return tostring(obj_to_xml(data, 'usuario'))
		elif format == 'json':
			response.content_type = 'application/json'
			return simplejson.dumps(data)



	def _procesar_permisos(self, id, permisos):
		users = request.environ['authkit.users']
		log.info("processar premisos")

		# quitar los roles que tiene el usuario y que no estan en la lista pasada como parametro
		log.info("QUITAR:")
		for role in users.user_roles(id):
			log.info(role)
			#si el rol es restringido y no tiene permisos admin_server debe de dar error
			#EN ESTE CASO VAMOS HA IGNORARLOS
			if roles_details[role].restringido and not authorized( HasAuthKitRole(roles.admin_usuarios) ):
				continue
				#abort(403, u"No dispone de permisos para modificar un permiso restringido")

			if not role in permisos:
				log.info("ELIMINAR")
				log.info(role)
				users.user_remove_role(id, role)

		# anadir los roles que estan en la lista pasada como parametro y no tiene aun el usuario
		log.info("ANADIR:")
		for permiso in permisos:
			if roles_details[permiso].restringido and not authorized( HasAuthKitRole(roles.admin_usuarios) ):
				abort(403, _(u'No dispone de permisos para modificar un permiso restringido'))#IDIOMAOK

			if not permiso in users.user_roles(id):
				users.user_add_role(id, permiso)

		meta.Session.commit()


	@authorize( HasAuthKitRole([roles.admin_usuarios_restringido , roles.admin_usuarios]))
	def delete(self, id, format=''):
		"""
		tratamiento especial de id y format, ver comentarios en show()
		"""
		if format: id = '.'.join( (id, format) )
		format = 'xml'

		users = request.environ['authkit.users']

		#NO PERMITIR ELIMINAR EL USUARIO SYSADMIN
		if id.upper() == "SYSADMIN": abort(403, u"Usuario protegido")

		# comprobar que exista el usuario
		if not users.user_exists(id):
			abort(404)
		# datos adicionales del usuario:
		q = meta.Session.query(Usuario).filter( Usuario.username == id )
		if q.count():
			usuario =  q.one()
			if usuario is None:
				abort(404, _(u'No se encuentra el usuario LDAP indicado con id: %s') % id)#IDIOMAOK
			else:
				meta.Session.delete(usuario)
				meta.Session.commit()
				try:
					meta.Session.commit()
				except IntegrityError as e:
					log.error(e)
					abort(403, _(u'No se puede eliminar el usuario LDAP'))#IDIOMAOK



		# eliminar el medico asociado (si tiene)
		q = meta.Session.query(Medico).filter( Medico.username == id )
		if q.count():
			self._eliminar_medico( q.one().id )

		# eliminarlo
		users.user_delete(id)

		meta.Session.commit()


	def _eliminar_medico(self, medico_id):
		medico = registro_by_id(Medico, medico_id)
		if medico is None:
			abort(404, _(u'No se encuentra el médico indicado con id: %s') % medico_id)#IDIOMAOK
		else:
			# quitar primero las relaciones con servicios y agendas (Rel_Medicos_Servicios y Rel_Medicos_Agendas)
			for rel in medico.servicios: meta.Session.delete(rel)
			for rel in medico.agendas: meta.Session.delete(rel)
			# eliminar el médico
			meta.Session.delete(medico)
			try:
				meta.Session.commit()
			except IntegrityError as e:
				log.error(e)
				abort(403, _(u'No se puede eliminar el médico'))#IDIOMAOK


	def _crear_medico(self, usuario_id, nombre, servicios = None, colegiado = None, agendas = None):
		"""
		Crea un nuevo Medico.
		"servicios" es una lista de ids de servicios. Puede estar vacia.
		"""
		log.debug('_crear_medico')
		medico = Medico()
		medico.username = usuario_id
		medico.nombre = nombre
		if colegiado != None:
			medico.colegiado = colegiado

		# graba las agendas seleccionadas.
		if agendas:
			for agenda_id in agendas:
				rel = Rel_Medicos_Agendas()
				medico.agendas.append(rel)
				rel.agenda_id = agenda_id

		# Graba los servicios seleccionados.
		if servicios:
			for servicio_id in servicios:
				rel = Rel_Medicos_Servicios()
				medico.servicios.append(rel)
				rel.servicio_id = servicio_id

				# si por alguna razon agendas viene en none pero el servicio esta seleccionado
				# entonces selecciona todas las agendas de ese servicio.
				if agendas == None:
					#   XXX además asignar todas las agendas del servicio al medico
					servicio = registro_by_id(Servicio, servicio_id)
					for agenda in servicio.agendas:
						rel = Rel_Medicos_Agendas()
						medico.agendas.append(rel)
						#rel.medico_id = medico.id
						rel.agenda_id = agenda.id


		meta.Session.save(medico)
		meta.Session.commit()
##		try:
##			Session.commit()
##		except IntegrityError:
##			abort(403, _(u'No se puede crear el médico'))#IDIOMAOK


	def _modificar_medico(self, medico_id, usuario_id, nombre, colegiado = None, servicios = None, agendas=None):
		"""
		Modifica un Medico.
		
		parámetros:
			servicios - es una lista de ids de servicios.
				- Si tiene elementos, sustituirán a los actuales servicios del médico
				- Si es una lista vacía [] quitará todos los elementos al médico
				- Si no se indica (es None) no se cambiarán los servicios del médico
			
			agendas - es una lista de ids de agendas. Se aplica la misma lógica que en "servicios"
			
		NOTA: Por la relación que hay entre servicios y agendas, es necesario que se indiquen
		o ambos parámetros o ninguno, pero no sólo uno de ellos.
		"""
		log.debug('servicios %s', servicios)
		log.debug('agendas %s', agendas)
		#   XXX si el medico ya tiene exploraciones no deberia poder renombrarse...
		log.debug('_modificar_medico')
		medico = registro_by_id(Medico, medico_id)
		if medico is None:
			abort(404, _(u'No se encuentra el médico indicado con id: %s') % medico_id)#IDIOMAOK
		else:
			medico.username = usuario_id
			medico.nombre = nombre

			if colegiado != None:
				medico.colegiado = colegiado

			if servicios != None and agendas != None:
				# quitar servicios y asignar el nuevo
				for rel in medico.servicios: meta.Session.delete(rel)
				while len(medico.servicios) > 0: medico.servicios.pop()

				#   XXX además también quita las agendas y asigna luego las correspondientes a los servicios nuevos
				for rel in medico.agendas: meta.Session.delete(rel)
				while len(medico.agendas) > 0: medico.agendas.pop()

				# graba las agendas seleccionadas.
				if agendas:
					for agenda_id in agendas:
						rel = Rel_Medicos_Agendas()
						medico.agendas.append(rel)
						rel.agenda_id = agenda_id

				# Graba los servicios seleccionados.
				if servicios:
					for servicio_id in servicios:
						rel = Rel_Medicos_Servicios()
						medico.servicios.append(rel)
						rel.servicio_id = servicio_id

						# si por alguna razon agendas viene en none pero el servicio esta seleccionado
						# entonces selecciona todas las agendas de ese servicio.
						if agendas == None:
							#   XXX además asignar todas las agendas del servicio al medico
							servicio = registro_by_id(Servicio, servicio_id)
							for agenda in servicio.agendas:
								rel = Rel_Medicos_Agendas()
								medico.agendas.append(rel)
								#rel.medico_id = medico.id
								rel.agenda_id = agenda.id

			meta.Session.update(medico)
			try:
				meta.Session.commit()
			except IntegrityError as e:
				log.error(e)
				abort(403, _(u'No se puede modificar el médico'))#IDIOMAOK

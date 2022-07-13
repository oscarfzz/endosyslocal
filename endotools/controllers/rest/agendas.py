import logging

from pylons.i18n import _
from pylons import request
from xml.etree.ElementTree import Element, SubElement, tostring
from authkit.authorize.pylons_adaptors import authorize
from authkit.permissions import RemoteUser, ValidAuthKitUser, UserIn, HasAuthKitRole, And

from endotools.model import meta
from endotools.model.agendas import Agenda, HorarioAgenda
from endotools.model.salas import Rel_Salas_Agendas
from endotools.model.medicos import Rel_Medicos_Agendas
from endotools.model.usuarios import get_usuario
from endotools.lib.genericREST import GenericRESTController
from endotools.lib.usuarios.seguridad import roles
from endotools.lib.misc import generic_abort, formatea_valor, registro_by_id

from datetime import date, datetime
from time import strptime

log = logging.getLogger(__name__)

# usado para nombrar los elems XML de los horarios de las agendas
_DIAS_SEMANA = (u"LUNES", u"MARTES", u"MIERCOLES", u"JUEVES", u"VIERNES", u"SABADO", u"DOMINGO")#NO TRADUCIR

class AgendasController(GenericRESTController):

	def __init__(self, *args, **kwargs):
		GenericRESTController.__init__(self, *args, **kwargs)
		self.tabla = Agenda
		self.nombre_recurso = 'agenda'
		self.nombre_recursos = 'agendas'
		self.campos_index = ('id', 'nombre', 'codigo', 'servicio')
		self.campo_orderby = Agenda.nombre

	def _filtrar_index(self, query, format= None):
		if self.medico_id:
			# filtra las agendas por medico
			query = query.filter(Agenda.medicos.any(medico_id=self.medico_id))
		return query

	@authorize(RemoteUser())
	def index(self, format='xml'):
		p = request.params
		if 'medico_id' in p:
			self.medico_id = int(p['medico_id'])
			del(p['medico_id'])
		else:
			self.medico_id = None

		return self._doIndex(p, format)

	def _return_doIndex(self, registros, data,format):
		""" Amplia la info de la agenda extraida por defecto de la BBDD con los
			horarios, medicos y salas.
		"""
		for agenda in registros:
			a = filter(lambda i: str(i['id']) == str(agenda.id), data)
			if len(a) > 0:
				agenda_el = a[0]

				# ampliar la info del servicio con el Centro
				agenda_el['servicio']['centro'] = {
					'id': formatea_valor(agenda.servicio.centro.id),
                    'nombre': formatea_valor(agenda.servicio.centro.nombre)
				}

				# HORARIOS
				# añadir los horarios. crea un elem por cada dia (lunes, martes...)
				# y guarda la referencia a cada uno para ir añadiendo las horas
				agenda_el['horarios'] = {}
				dias_els = []
				for numero_dia, nombre_dia in enumerate(_DIAS_SEMANA):
					agenda_el['horarios'][nombre_dia] = { 'numero': formatea_valor(numero_dia) }
					dias_els.append( agenda_el['horarios'][nombre_dia] )

				for horario in agenda.horarios:
					assert horario.dia_semana in range(0, 7), 'El dia del horario debe ser un numero de 0 a 6'
					if not 'horas' in dias_els[horario.dia_semana]:
						dias_els[horario.dia_semana]['horas'] = []
					dias_els[horario.dia_semana]['horas'].append({
						'ini': formatea_valor(horario.hora_ini),
						'fin': formatea_valor(horario.hora_fin)
					})

				# MEDICOS
				agenda_el['medicos'] = []
				for rel in agenda.medicos:
					usuario = get_usuario( username = rel.medico.username )
					if (usuario and usuario.activo and usuario.tipo != 1) or not usuario:
						agenda_el['medicos'].append({
							'id':		 formatea_valor(rel.medico.id),
							'nombre':	 formatea_valor(rel.medico.nombre),
							'username':  formatea_valor(rel.medico.username),
							'apellido1': formatea_valor(rel.medico.apellido1),
							'apellido2': formatea_valor(rel.medico.apellido2),
							'colegiado': formatea_valor(rel.medico.colegiado)
						})

				# SALAS
				agenda_el['salas'] = []
				for rel in agenda.salas:
					agenda_el['salas'].append({
						'id': formatea_valor(rel.sala.id),
						'nombre': formatea_valor(rel.sala.nombre)
					})
		return data

	@authorize(RemoteUser())
	def show(self, id, format='xml'):
		return GenericRESTController.show(self, id, format)

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
		agenda = registro_by_id(Agenda, id)
		if agenda is None:
			generic_abort(frmt='xml', status=404, mensaje=_(u'No se encuentra la agenda indicada con id: %s') % id)#IDIOMAOK
		else:
			codigo = request.params.get('codigo', None)
			if codigo:
				agenda.codigo = codigo

			nombre = request.params.get('nombre', None)
			if nombre:
				agenda.nombre = nombre

			# mirar con carlos xq desde la administración no se envia, en modificar la agenda
			servicio_id = request.params.get('servicio_id', None)
			if servicio_id:
				agenda.servicio_id = servicio_id

			self.interpretar_salas_medicos_horarios(agenda)

			meta.Session.update(agenda)
			try:
				meta.Session.commit()
			except IntegrityError as e:
				log.error(e)
				generic_abort(frmt='xml', status=404, mensaje=_(u'No se puede modificar el agenda indicada con id: %s') % id)#IDIOMAOK
				

	def interpretar_salas_medicos_horarios(self,agenda):

		if 'salas' in request.params:
			salas = request.params['salas']

			if salas:
				salas = map(lambda s: int(s), salas.split(','))
			else:
				salas = []

			# quitar salas y asignar las nuevas
			for rel in agenda.salas:
				meta.Session.delete(rel)

			while len(agenda.salas) > 0: agenda.salas.pop()

			for sala_id in salas:
				rel = Rel_Salas_Agendas()
				agenda.salas.append(rel)
				rel.sala_id = sala_id
				rel.agenda_id = id


		if 'medicos' in request.params:
			medicos = request.params['medicos']

			if medicos:
				medicos = map(lambda s: int(s), medicos.split(','))
			else:
				medicos = []

			# quitar salas y asignar las nuevas
			for rel in agenda.medicos:
				meta.Session.delete(rel)

			while len(agenda.medicos) > 0: agenda.medicos.pop()

			for medico_id in medicos:
				rel = Rel_Medicos_Agendas()
				agenda.medicos.append(rel)
				rel.medico_id = medico_id
				rel.agenda_id = id

		dias_semana = ["LUNES", "MARTES", "MIERCOLES", "JUEVES", "VIERNES", "SABADO", "DOMINGO"]#NO TRADUCIR
		#Funcionalidad Horarios, si se envia los parametros de dias vacios significa que elimina sus horarios
		#si no se envian, no los modifica

		#para saber si viene algun item de los dias de la semana
		#en el caso de que sea TRUE se eliminarán todos los horarios
		alguno = False
		for item in dias_semana:
			alguno = alguno or item in request.params

		if alguno:
			for horario in agenda.horarios:
				meta.Session.delete(horario)

			for indice, dia_semana in enumerate(dias_semana):
				if dia_semana in request.params:
					dia = request.params[dia_semana]

					if dia:
						horarios = dia.split(',')
						for horario in horarios:
							log.debug(horario)
							horas = horario.split('-')

							d = date.today()
							if horas[0].count(':') == 1: horas[0] = horas[0] + ':00'
							t1 = strptime(horas[0], "%H:%M:%S")
							hora_ini = datetime(d.year, d.month, d.day, t1.tm_hour, t1.tm_min)

							if horas[1].count(':') == 1: horas[1] = horas[1] + ':00'
							t2 = strptime(horas[1], "%H:%M:%S")
							hora_fin = datetime(d.year, d.month, d.day, t2.tm_hour, t2.tm_min)

							horario_agenda = HorarioAgenda()
							agenda.horarios.append(horario_agenda)
							horario_agenda.agenda_id = id
							horario_agenda.hora_ini = hora_ini
							horario_agenda.hora_fin = hora_fin
							horario_agenda.dia_semana = indice

	def _created(self, agenda):
		self.interpretar_salas_medicos_horarios(agenda)
		try:
			meta.Session.commit()
		except IntegrityError as e:
			log.error(e)
			raise

	@authorize(HasAuthKitRole([roles.admin_organizacion]))
	def create(self, format='xml'):
		p = request.params
		if 'nombre' not in p:
			generic_abort(frmt=format, status=400, mensaje=_(u"El campo 'nombre' es obligatorio"))#IDIOMAOK
		if 'servicio_id' not in p:
			generic_abort(frmt=format, status=400, mensaje=_(u"El campo 'servicio_id' es obligatorio"))#IDIOMAOK
		return GenericRESTController.create(self,  format)

	@authorize(HasAuthKitRole([roles.admin_organizacion]))
	def delete(self, id):
		agenda = registro_by_id(Agenda, id)
		if agenda is None:
			abort(404, _(u'No se encuentra la agenda indicada con id: %s') % id)#IDIOMAOK
		else:
			# quitar salas asignadas a la agenda
			for rel in agenda.salas:
				meta.Session.delete(rel)
			while len(agenda.salas) > 0: agenda.salas.pop()

			# quitar medicos asignadas a la agenda
			for rel in agenda.medicos:
				meta.Session.delete(rel)
			while len(agenda.medicos) > 0: agenda.medicos.pop()

			# quitar horarios asignados a la agenda
			for horario in agenda.horarios:
				meta.Session.delete(horario)
			while len(agenda.horarios) > 0: agenda.horarios.pop()

			import endotools.lib.organizacion_centros
			endotools.lib.organizacion_centros.clear_defaults(agenda_id = agenda.id, commit = False)

			meta.Session.delete(agenda)
			meta.Session.commit()
''' clase base para crear un plugin de gestion de citas mediante DICOM worklist. Desciende de PluginCitas.

interesante:
	-que se configurar el mapeo de los campos del worklist a los campos del objeto Cita
	-que se pueda configurar qué campos se piden al worklist
	-que se pueda configurar como se parsea el campo patientName


posibles errores: (usar los mismos codigos http, por conveniencia)

403 - No permitido: no se permite la operacion
401 - No autorizado: la operacion se permite pero no esta autorizado
400 - parametros incorrectos: los parametros suministrados son incorrectos
404 - no se ha encontrado: no existe ninguna cita con el id o parametros de busqueda indicados
500 - error no especificado

estados correctos:
200 - ok
201 - la cita se ha creado correctamente

'''

# XXX deberia gestionar tambien (o opcionalmente): salas (y tipos prestacion y medicos?) para vincular correctamente
# XXX Mejor usar excepciones?

##import rpdb2
import logging
log = logging.getLogger(__name__)

from endotools.model import meta
from endotools.lib.misc import record, registro_by_id, medico_from_user
#from endotools.lib.plugins.base import obj_from_params, Plugin
from endotools.lib.plugins.base import *
from endotools.lib.plugins.base.citas import PluginCitas, Cita
from sqlalchemy.types import Integer, Date
from sqlalchemy.sql import and_
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.exceptions import IntegrityError
from pylons import config
from datetime import datetime, date
import endotools.lib.dicom
import endotools.lib.dicom.util
from endotools.lib.pydcmtk.pydcmtk import *
import time
import endotools.model
import endotools.model.citas #, endotools.model.tiposExploracion
import endotools.model.pacientes
from endotools.model.map_Prest_TiposExpl import get_servicios_from_prestacion
from endotools.model.servicios import get_servicio


class CitaWorklist(Cita):

##	def __init__(self, work):
##		"""
##		work	es de tipo model.worklist.Work (un dicom.util.WLWork creo que tambien serviria)
##		"""
##		Cita.__init__(self)
##		self.work = None
##		if work:
##			self.from_work(work)


	def __init__(self, work = None, registro_cita = None):
		"""
		work	es de tipo model.worklist.Work (un dicom.util.WLWork creo que tambien serviria)
		si se indica un id de la tabla citas, rellena los datos con él.
		"""
		Cita.__init__(self)
		self.work = None
		if work and registro_cita:
			raise Exception(u'Sólo puede indicar un parámetro ("work" o "registro_cita") al crear uan instancia de "CitaWorklist"')
		if work:
			self.from_work(work)
		elif registro_cita:
			self.from_bbdd(registro_cita)


	def from_work(self, work):
		self.work = work	#   almacena los datos originales (no se si sera necesario para algo xxx)
		#   XXX el mapeo que viene a continuacion se deberia adaptar a cada caso en una subclase de CitaWorklist

		self.id = None								  #   es el id en base de datos (xxx confirmarlo)
		#self._codigo = work.accessionNumber			 #   por defecto se toma el campo "accessionNumber" como el identificador de la cita

		self.hora = endotools.lib.dicom.util.DICOM_to_datetime(work.schProcStepStartDate, work.schProcStepStartTime)	#   hora de la cita
		self.exploracion = None
		self.exploracion_id = None
		self.paciente.id = None
		s = work.patientName.split('^')				 #   xxx	 descomponer el nombre del paciente
		self.paciente.nombre = s[1]
		self.paciente.apellido1 = s[0]
		self.paciente.apellido2 = ''
		self.paciente.fechaNacimiento = endotools.lib.dicom.util.DICOM_to_date(work.patientBirthDate)
		self.paciente.idunico = work.patientID
		self.paciente.CIP = ''
		self.paciente.aseguradora_id = None
		self.paciente.centros = []
		self.paciente_id = None						 #   no lo registra en la BBDD
#XXX		self.paciente.sexo = work.patientSex			#   sexo
#XXX		self.paciente.fechanac? = work.patientBirthDate	  #   fecha nacimiento

		#   XXX	 obtener el tipo de exploracion. De alguna forma en la subclase
##		tipoexploracion_id = getTipoExploracionId(cita_de_ws.CodPrestacion)
		tipoexploracion_id = None
		if (tipoexploracion_id):
			tipoexploracion = registro_by_id(endotools.model.tiposExploracion.TipoExploracion, tipoexploracion_id)
			self.tipoExploracion.id = tipoexploracion.id
			self.tipoExploracion._codigo = cita_de_ws.CodPrestacion  # XXX?
			self.tipoExploracion.nombre = tipoexploracion.nombre
			self.tipoExploracion.color = tipoexploracion.color
			self.tipoExploracion_id = self.tipoExploracion.id
			log.debug('tipoExploracion: %s', tipoexploracion.nombre)
		else:
			self.tipoExploracion.id = None
##			self.tipoExploracion._codigo = work.CodPrestacion  # XXX?
			self.tipoExploracion.nombre = None
			self.tipoExploracion.color = None
			self.tipoExploracion_id = self.tipoExploracion.id
		# XXX
##		self.SIHGA_codigo_prestacion = cita_de_ws.CodPrestacion
##		self.SIHGA_descripcion_prestacion = cita_de_ws.DescripcionPrestacion
		# XXX	   info de la sala, medico y servicio
		self.sala.id = None			 #'1'
		self.sala.nombre = '-'		  #'Sala 1'
		self.sala_id = self.sala.id

		self.medico.id = None		   #'1'
		self.medico.username = '-'	  #'xxxxxx'
		self.medico.nombre = '-'		#'Dr. X'
		self.medico_id = self.medico.id

		#	QUITAR_CITA.SERVICIO_ID
##		self.servicio.id = None
##		self.servicio.nombre = '-'
##		self.servicio_id = self.servicio.id 	#	cita.servicio_id

		self.prioridad_id = None
		self.cancelada = None

		# XXX   esto está hecho asi para el Baix, pero puede que en otros casos
		#       funcione distinto...

		#	QUITAR_CITA.SERVICIO_ID
##		# EXTRAER SERVICIO_ID A PARTIR DEL SCHEDULEDPROCEDURESTEPID
##		codigo_servicio =	get_servicio_from_prestacion(prestacion=work.schProcStepID)
##		servicio =			get_servicio(codigo=codigo_servicio)
##		log.debug('codigo_servicio: %s' % codigo_servicio);
##		if servicio:
##			log.debug('servicio.nombre: %s' % servicio.nombre);
##			self.servicio.id =		servicio.id
##			self.servicio.nombre =	servicio.nombre
##			self.servicio_id = self.servicio.id 	#	cita.servicio_id

		# ######################

		# worklist
		self.work = record()
		self.work.accessionNumber = work.accessionNumber
		self.work.patientID = work.patientID
		self.work.patientName = work.patientName
		self.work.patientBirthDate = work.patientBirthDate
		self.work.patientSex = work.patientSex
		self.work.schProcStepStartDate = work.schProcStepStartDate
		self.work.schProcStepStartTime = work.schProcStepStartTime
		self.work.studyInstanceUID = work.studyInstanceUID
		self.work.requestingPhysician = work.reqPhysician
		self.work.requestingService = work.reqService
		self.work.referringPhysiciansName = work.refPhysicianName

		# datos adicionales
##		self.info.codigo_prestacion = work.schProcStepID
##		self.info.descripcion_prestacion = work.schProcStepDescription
		self.ex.prestacion_cod = work.schProcStepID
		self.ex.prestacion_descr = work.schProcStepDescription

		self.work.placerOrderNumber = work.placerOrderNumber # XXX?

##		# datos adicionales
##		self.ncita = cita_de_ws.NCita


	def from_bbdd(self, registro):
		self.id = registro.id
		#self._codigo = registro._codigo
		self.fecha = registro.fecha
		self.hora = registro.hora
		self.exploracion = None
		self.exploracion_id = None
		self.paciente.id = registro.paciente.id
		self.paciente.nombre = registro.paciente.nombre
		self.paciente.apellido1 = registro.paciente.apellido1
		self.paciente.apellido2 = registro.paciente.apellido2
		self.paciente.fechaNacimiento = registro.paciente.fechaNacimiento
		self.paciente.idunico = registro.paciente.idunico
		self.paciente.CIP = registro.paciente.CIP
		self.paciente.centros = []
		self.paciente_id = registro.paciente_id

##		self.tipoExploracion.nombre = registro.tipoExploracion.nombre
##		self.tipoExploracion.color = registro.tipoExploracion.color
##		self.tipoExploracion.id = registro.tipoExploracion.id
##		self.tipoExploracion_id = registro.tipoExploracion_id
		self.tipoExploracion.id = None
		self.tipoExploracion.nombre = None
		self.tipoExploracion.color = None
		self.tipoExploracion_id = self.tipoExploracion.id


##			self.sala = None
##			self.medico = None

		# XXX
		self.sala.id = None			 #'1'
		self.sala.nombre = '-'		  #'Sala 1'
		self.sala_id = self.sala.id

		self.medico.id = None		   #'1'
		self.medico.username = '-'	  #'xxxxxx'
		self.medico.nombre = '-'		#'Dr. X'
		self.medico_id = self.medico.id

		#	QUITAR_CITA.SERVICIO_ID
##		self.servicio.id = None
##		self.servicio.nombre = '-'
##		self.servicio_id = self.servicio.id 	#	cita.servicio_id

		self.prioridad_id = None
		self.cancelada = registro.cancelada

		# worklist
		log.debug("CITA.PACIENTE: %s", registro.paciente)
		log.debug("CITA.WORKLIST: %s", registro.work)
		log.debug(dir(registro.work))
		log.debug(registro.work.accessionNumber)

		self.work = record()
		self.work.accessionNumber = registro.work.accessionNumber
		self.work.patientID = registro.work.patientID
		self.work.patientName = registro.work.patientName
		self.work.patientBirthDate = registro.work.patientBirthDate
		self.work.patientSex = registro.work.patientSex
		self.work.schProcStepStartDate = registro.work.schProcStepStartDate
		self.work.schProcStepStartTime = registro.work.schProcStepStartTime
		self.work.studyInstanceUID = registro.work.studyInstanceUID
		self.work.requestingPhysician = registro.work.reqPhysician
		self.work.requestingService = registro.work.reqService
		self.work.referringPhysiciansName = registro.work.refPhysicianName

		self.work.placerOrderNumber = registro.work.placerOrderNumber # XXX?



class PluginCitasWorklist(PluginCitas):

	def __init__(self):
		Plugin.__init__(self)

	def index(self, params):
		""" devuelve un list de objetos CitaWorklist
			parametros:
				fecha		la fecha de las citas. En formato dd/mm/YYYY
				agenda_id   (int) se utiliza para extraer el codigo del centro

			notas:
			la busqueda desde la pantalla de citas pendientes envia tambien el parametro "exploracion_id" vacio,
			para indicar que muestre solo las citas no realizadas (sin exploracion asociada)
		"""

		#   XXX	 utilizar mejor endotools.lib.dicom.thread¿? creando hilos por cada peticion, asi no se bloquea al ejecutar el dcmQuery, esperando la respuesta

		if not 'fecha' in params or not params['fecha']:
			raise E_ParamIncorrecto('No se ha indicado el parametro "fecha" en la llamada a "index" de "PluginCitasWorklist"')

		# convertir el parametro 'fecha' a datetime
		t = time.strptime(params['fecha'], "%d/%m/%Y")
		fecha = datetime(t.tm_year, t.tm_mon, t.tm_mday)

		# si hay param. agenda, obtener el codigo de Centro para filtrar la descarga del worklist
		agenda = None   #	QUITAR_CITA.SERVICIO_ID     uso la variable "agenda" mas adelante
		codigo_centro = None
		if 'agenda_id' in params:
			agenda = registro_by_id(endotools.model.Agenda, params['agenda_id'])
			codigo_centro = agenda.servicio.centro.codigo

		# obtener el worklist (esto ya lo guarda en BBDD, tabla Worklist)
		#   XXX por defecto uso modality VL... que se pueda configurar
		worklist = endotools.lib.dicom.get_worklist(fecha, None, codigo_centro)

		lista = []
		# recorrer todas las 'citas' obtenidas del Worklist
		for awork in worklist:
			cita = CitaWorklist(work = awork)
			cita.fecha = fecha

			# le asigna el mismo agenda_id que se había pasado como param
			cita.agenda_id = params.get('agenda_id', None)

			# siempre, filtrar por el/los servicio/s del medico actual
			medico = params['__medico']

#			if medico and medico.servicio_id and cita.servicio_id:
#				if cita.servicio_id != medico.servicio_id:
#					continue

			#	QUITAR_CITA.SERVICIO_ID
##			if (cita.servicio_id != None) and (len(medico.servicios) > 0):
##				ok = False
##				for rel in medico.servicios:
##					if cita.servicio_id == rel.servicio_id:
##						ok = True
##						break
##				if not ok: continue
			#   Ahora se filtra el worklist recibido según si la agenda pertenece al servicio obtenido a partir de la prestacion (mediante la tabla "map_Prest_TiposExpl")
			#   No creo que haga falta comprobar que la agenda pertenezca al medico, ya que si no no dejaria escogerla desde Citas Pendientes...
			#   Además se hace que una prestacion pueda ser de mas de un servicio... por lo tanto se mira que alguno de los servicios sea el de la agenda.
			#   (si no se pasa agenda, se omite este filtrado)
####			codigo_servicio =	get_servicio_from_prestacion(prestacion=cita.info.codigo_prestacion)  # xxx ya no se usa .info.codigo_prestacion
##			codigo_servicio =	get_servicio_from_prestacion(prestacion=cita.ex.prestacion_cod)
##			servicio =			get_servicio(codigo=codigo_servicio)
##			log.debug('codigo_servicio: %s' % codigo_servicio)
##			if servicio and agenda:
##				log.debug('servicio.nombre: %s' % servicio.nombre)
##				if agenda.servicio_id != servicio.id:
##					continue

##			print cita.work.patientID, '?'

			# Si se indica un codigo de prestacion y una agenda, entonces comprobar si se ha de filtrar la cita
			if cita.ex.prestacion_cod != None and agenda:
				ok = False
				codigos_servicio =	get_servicios_from_prestacion(prestacion=cita.ex.prestacion_cod)
##				print cita.work.patientID, codigos_servicio
				for codigo_servicio in codigos_servicio:
					servicio = get_servicio(codigo=codigo_servicio)
##					log.debug('codigo_servicio: %s' % codigo_servicio)
					if servicio:
##						log.debug('servicio.nombre: %s' % servicio.nombre)
						if agenda.servicio_id == servicio.id:
##							log.debug('la agenda "%s" pertenece a este servicio' % agenda.nombre)
							ok = True
							break
				if not ok: continue
##			print cita.work.patientID, 'OK'

			# crear el paciente si no existe (se identifica por el nhc... XXX   en algún caso podría ser otro id, por ejemplo CIP, CIPA, NUHSA...)	//////y no hay plugin de pacientes
			# XXX pensar si seria mejor hacer esto desde el show
##			from endotools.config.plugins import pluginPacientes
##			if not pluginPacientes:
			#import endotools.model.pacientes   no se porqué, si pongo el import aqui hace cosas raras (con la variable local endotools), asi que lo pongo arriba de todo
			q = meta.Session.query(endotools.model.pacientes.Paciente)
			q = q.filter( endotools.model.pacientes.Paciente.idunico == cita.paciente.idunico )
			if q.count() > 0:
				paciente = q.one()
				cita.paciente.id = paciente.id
				cita.paciente_id = paciente.id
			else:
				paciente = endotools.model.pacientes.Paciente()
				paciente.idunico = cita.paciente.idunico
				paciente.CIP = cita.paciente.CIP
				paciente.nombre = cita.paciente.nombre
				paciente.apellido1 = cita.paciente.apellido1
				paciente.apellido2 = cita.paciente.apellido2
##				paciente.fechaNacimiento = cita.paciente.fechaNacimiento
				#	si la fecha es anterior a 1800, poner null, que SQL Server puede fallar con fechas muy antiguas...
				if cita.paciente.fechaNacimiento and cita.paciente.fechaNacimiento < date(1800, 1, 1):
					paciente.fechaNacimiento = None
				else:
					paciente.fechaNacimiento = cita.paciente.fechaNacimiento
				paciente.DNI = '-'
				meta.Session.save(paciente)
				meta.Session.commit()
				cita.paciente.id = paciente.id
				cita.paciente_id = paciente.id
			# ##########################

			# si no existe el registro en la tabla citas, crearlo y asignarlo
			# al worklist
			if not awork.cita_id:
				# crear los registros en la BBDD
				nuevaCita = self.nueva_cita_BBDD(cita)

				# actualizar el registro de la tabla Worklist
				awork = endotools.lib.dicom.update_work(awork, cita_id = nuevaCita.id)
			# si ya existia, coger la exploracion asociada (si tiene)
			else:
##				cita.tipoExploracion_id = reg_cita.tipoExploracion_id
##				cita.tipoExploracion.id = cita.tipoExploracion_id
				registroCita = registro_by_id(endotools.model.citas.Cita, awork.cita_id)
				cita.exploracion_id = registroCita.exploracion_id
				cita.exploracion = registroCita.exploracion

			# asignar el id del registro de la cita
			cita.id = awork.cita_id

			# si se ha pasado el parametro "exploracion_id", realizar la comprobacion
			if 'exploracion_id' in params:
				# si el valor es una cadena vacia, interpretar como null
				valor = params['exploracion_id']
				if valor == '': valor = None
				if not cita.exploracion_id == valor: continue

			lista.append(cita)

		return lista


	def show(self, id):
		""" devuelve un objeto Cita con el id indicado """
		# devolver de BBDD (no accede para nada la tabla de BBDD Worklist, solo a la tabla Citas)
		cita = registro_by_id(endotools.model.citas.Cita, id)
		if cita is None:
			raise E_NoEncontrado
		else:
			return CitaWorklist(registro_cita = cita)


	def create(self, cita):
		""" crea una nueva cita a partir del objeto Cita pasado como parametro.
		devuelve el id
		"""
		pass

	def update(self, id, cita):
		""" modifica una cita con el id indicado a partir de los datos del objeto Cita pasado como parametro.
		devuelve un codigo de estado
		"""
		pass

	def delete(self, id):
		""" elimina una cita con el id indicado.
		devuelve un codigo de estado
		"""
		pass

	def nueva_cita_BBDD(self, cita):
		"""
		añade un nuevo registro a las tablas 'citas' y actualiza el registro
		de la tabla 'Worklist'.

		parámetros:
			cita:   objeto de tipo 'CitaWorklist'
		"""
		# crear el nuevo registro en la tabla 'citas'
		nuevaCita = endotools.model.citas.Cita()
		for campo in endotools.model.citas.Cita.c.keys():
			if campo == 'id': continue
			if not campo in cita.__dict__: continue
			if not isinstance(getattr(endotools.model.citas.Cita, campo), InstrumentedAttribute): continue
			valor = cita.__dict__[campo]
			setattr(nuevaCita, campo, valor)
		meta.Session.save(nuevaCita)
		meta.Session.commit()
		# XXX controlar excepcion IntegrityError, lanzada cuando algun valor no puede ser nulo

		# devuelve el registro (model.citas.Cita)
		return nuevaCita

	def cita_from_params(self, params):
		""" devuelve un objeto Cita a partir de unos params
		"""
		cita = Cita()
		obj_from_params(cita, params)
		return cita


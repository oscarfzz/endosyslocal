"""
Gestión de citas. Cualquier parte de EndoSys que acceda a las citas
debería hacerlo utilizando este module.

  XXX rest/citas
  XXX plugins...

Accede siempre a la bbdd de EndoSys Web. Se debería implementar aqui la
funcionalidad de los plugins para cambiar el comportamiento

XXX renombrar el concepto CITA, ya que en los hospitales hay distintos conceptos
como cita, petición, wirklist, etc... que al final son lo mismo en EndoSys Web.
"""
import logging
from pylons.i18n import _
import time
import datetime
import endosys.model as model
from endosys.model.citas_ex import get_cita_ex
from endosys.model import meta
from endosys.model.meta import engine
from sqlalchemy.sql import and_, or_, not_, func
import sqlalchemy.databases.mssql as mssql
import sqlalchemy.databases.oracle as oracle
import sqlalchemy.databases.mysql as mysql
import misc
import endosys.lib.registro as registro
from endosys.model.citas import Cita


log = logging.getLogger(__name__)

# campos de texto varchar(50) de la tabla citas_ex
CAMPOS_CITA_EX = (
			'id_ext_1',
			'id_ext_2',
			'id_ext_3',
			'id_ext_4',
			#'nhc',
			'idunico',
			'numero_cita',
			'numero_episodio',
			'numero_peticion',
			'prestacion_cod',
			'prestacion_descr',
			'servicio_cod',
			'servicio_descr',
			'agenda_cod',
			'agenda_descr',
			'procedencia_cod',
			'procedencia_descr',
			'servicio_peticionario_cod',
			'servicio_peticionario_descr',
			'medico_peticionario_cod',
			'medico_peticionario_descr'
)

def get_by_id_ext(id_ext, nombre_campo_id):
	"""
	obtener una cita a partir de su identificador externo (HL7, DICOM worklist...)
	XXX de forma temporal se usa "nombre_campo_id" para indicar el campo
		identificador. Habrá que pensar la forma correcta de hacerlo.
	"""
	if not nombre_campo_id: nombre_campo_id = 'numero_peticion'
	campo_id = getattr(model.Cita_ex, nombre_campo_id)
##	q = Session.query(Cita).join(Cita.ex).filter(Cita_ex.numero_peticion == id_ext) # XXX
	q = meta.Session.query(model.Cita).join(model.Cita.ex).filter(campo_id == id_ext) # XXX
	total = q.count()
	if total == 1:
		return q.one()
	elif total > 1:
		#	XXX	No deberia pasar!!! pero para que no falle, se devuelve el primero.
		#		se registra en el log, para luego revisar el problema.
		log.warning('get_by_id_ext() ha devuelto mas de 1 registro. id_ext = %s, nombre_campo_id = %s' % (id_ext, nombre_campo_id))
		return q.first()
	else: # total == 0
		return None


def nueva_cita():
	log.debug('nueva_cita()')
	cita = model.Cita()
	cita.ex = model.Cita_ex()
	return cita


def eliminar_cita(cita, username = None, ipaddress = None, id_hl7_log = None):


	meta.Session.delete(cita.ex)
	meta.Session.delete(cita)
	meta.Session.commit()
	registro.nuevo_registro_cita(username, ipaddress, cita, registro.eventos.eliminar,
					registro.res.cita, 'Datos cita', None, id_hl7_log)
	return cita


def guardar_cita(cita,  username = None, ipaddress = None, cita_updating = None, id_hl7_log = None):
	#   XXX utiliza "id" para saber si es una nueva cita (id=None) o
	#   una cita existente que se está modificando (id!=None)
	if cita.id:
		#   modificando, update
		log.debug('guardar_cita() - update (modificar)')
		meta.Session.update(cita)
		registro.nuevo_registro_cita(username, ipaddress, cita, registro.eventos.modificar,
							registro.res.cita, 'Datos cita', cita_updating, id_hl7_log)
	else:
		#   nuevo, insert
		log.debug('guardar_cita() - save (crear nueva)')
		meta.Session.save(cita)
		#   parece que también se ejecuta el save del cita_ex (está en cita.ex)
		registro.nuevo_registro_cita(username, ipaddress, cita, registro.eventos.crear,
									registro.res.cita, 'Datos cita', None, id_hl7_log)

	print "ASEGURADORA: " + str(cita.aseguradora_id)
	cita.paciente.aseguradora_id = cita.aseguradora_id
	meta.Session.update(cita.paciente)

	cita_ex_numero_cita = '(no tiene cita.ex asociado)'
	if cita.ex:
		cita_ex_numero_cita = cita.ex.numero_cita
	log.debug('	cita.id = %s, cita.ex.numero_cita = %s' % (cita.id, cita_ex_numero_cita))
	meta.Session.commit()
	#   en cita.id está el nuevo id (en el caso de que fuera una nueva cita)


def get_hora_fin(cita):
	"""
	devuelve la hora fin calculada de una cita a partir de la hora y duracion
	(la duracion se guarda en minutos)

		cita	registro Cita de sqlalchemy

	devuelve el mismo tipo que cita.hora (deberia ser un datetime.datetime)

	OJO! no se tiene en cuenta si pasa al dia siguiente!!!
	"""
	if not cita.hora or not cita.duracion:
		return None
	d = datetime.timedelta(0, cita.duracion*60)
	return cita.hora + d


def cita_en_horario(horario, cita):
	"""
	Devuelve si la cita indicada está dentro del horario. "cita" es un objeto
 	que tenga los miembros fecha, hora y duracion, por lo que puede ser una
	Cita del model, o el objeto devuelto por from_params()

		cita.fecha   	datetime.date
		cita.hora		datetime.datetime
		cita.duracion   int (minutos)
		horario	 	sql alchemy (agenda.horarios...)
	"""
	# XXX   no se contempla el caso de que una cita abarque 2 dias (p.e. desde
	#		las 23:45 hasta las 00:15 del dia siguiente)
	# weekday() devuelve lunes 0 - domingo 6, lo cual ya está bien
	if not(horario.dia_semana == cita.fecha.weekday()):
		return False

	# en las horas del horario, como son datetimes, asigna a todas la misma parte
	# de fecha (la de la cita.fecha)
	hora_ini = datetime.datetime(cita.fecha.year, cita.fecha.month, cita.fecha.day, cita.hora.hour, cita.hora.minute)
	hora_fin = hora_ini + datetime.timedelta(0, cita.duracion*60)
	horario_ini = datetime.datetime(cita.fecha.year, cita.fecha.month, cita.fecha.day, horario.hora_ini.hour, horario.hora_ini.minute)
	horario_fin = datetime.datetime(cita.fecha.year, cita.fecha.month, cita.fecha.day, horario.hora_fin.hour, horario.hora_fin.minute)
	return (hora_ini >= horario_ini) and (hora_fin <= horario_fin)


def from_params(params):
	"""
	devuelve un record que representa una cita, con valores extraidos
	de un objeto de parametros HTTP (GET o POST).

	params	  objeto request.params, de un controller
	return	  objeto record. los nombres de campos coinciden con model.Cita.
				además se añade "hora_fin". Solo existirán aquellos campos que
				se han indicado. Si se han indicado vacios tendrán valor None,
				si un campo no se ha indicado, no estará en el objeto record.

	posibles parámetros:
		fecha
		hora
		paciente_id
		servicio_id (NO)
		cancelada
		medico_id
		sala_id
		observaciones
		duracion
		hora_fin

		 tipoExploracion_id

		id_ext_1
		id_ext_2
		id_ext_3
		id_ext_4
		nhc
		numero_cita
		numero_episodio
		numero_peticion
		prestacion_cod
		prestacion_descr
		servicio_cod
		servicio_descr
		agenda_cod
		agenda_descr
		procedencia_cod
		procedencia_descr
		servicio_peticionario_cod
		servicio_peticionario_descr
		medico_peticionario_cod
		medico_peticionario_descr
		 estado
	"""
	cita = misc.record()
	# campos de cita
	#   preprocesado...
	#   	fecha
	fecha = params.get('fecha', None)
	if fecha:
		t = time.strptime(fecha, "%d/%m/%Y")
		fecha = datetime.date(t.tm_year, t.tm_mon, t.tm_mday)
	#   	hora
	hora = params.get('hora', None)
	if hora: hora = misc.strtotime(hora, d = fecha)
	#   	hora_fin
	hora_fin = params.get('hora_fin', None)
	if hora_fin: hora_fin = misc.strtotime(hora_fin, d = fecha)
	#		cancelada
	cancelada = params.get('cancelada', None)
	if cancelada:
		cancelada = not( (cancelada.upper() == 'NO') or (cancelada == '0') )

	#   ...asignar params
	cita.fecha =		fecha
	cita.hora =			hora
	cita.hora_fin =		hora_fin
	cita.cancelada =	cancelada
	if 'paciente_id' in params:	cita.paciente_id =	misc.try_int(params['paciente_id'])
	if 'sala_id' in params:		cita.sala_id =		misc.try_int(params['sala_id'])
	if 'agenda_id' in params:	cita.agenda_id =	misc.try_int(params['agenda_id'])
	if 'medico_id' in params:	cita.medico_id =	misc.try_int(params['medico_id'])
	if 'aseguradora_id' in params:    cita.aseguradora_id = misc.try_int(params['aseguradora_id'])

	if 'observaciones' in params: cita.observaciones = params['observaciones']

	if 'prioridad_id' in params: cita.prioridad_id = misc.try_int(params['prioridad_id'])
	if 'tipoExploracion_id' in params: cita.tipoExploracion_id = misc.try_int(params['tipoExploracion_id'])

##	cita.paciente_id =	misc.try_int( params.get('paciente_id', None) )
##	cita.sala_id =		misc.try_int( params.get('sala_id', None) )
##	cita.agenda_id =	misc.try_int( params.get('agenda_id', None) )
##	cita.medico_id =	misc.try_int( params.get('medico_id', None) )
##	cita.observaciones = params.get('observaciones', None)
	cita.duracion =		misc.try_int( params.get('duracion', None) )
	cita.motivo_id =	misc.try_int( params.get('motivo_id', None) )

	# campos de cita_ex
	cita.ex = misc.record()
	for c in CAMPOS_CITA_EX:
		setattr( cita.ex, c, params.get(c, None) )
	cita.ex.estado = params.get('estado', None)
	# Si se envía '' a un id_ext_N, pasarlo a None
	if cita.ex.id_ext_1 == '': cita.ex.id_ext_1 = None
	if cita.ex.id_ext_2 == '': cita.ex.id_ext_2 = None
	if cita.ex.id_ext_3 == '': cita.ex.id_ext_3 = None
	if cita.ex.id_ext_4 == '': cita.ex.id_ext_4 = None

#   DEPRECATED  Ya no se utiliza
##	# XXX temporal, para que funcione integración CAPIO o Gregorio sin cambios en Mirth
##	_resultado_enviado = params.get('_resultado_enviado', None)
##	if _resultado_enviado:
##		if (_resultado_enviado.upper() == 'NO') or (_resultado_enviado.upper() == '0'):
##			cita.ex.estado = 0  # informe no enviado
##		else:
##			cita.ex.estado = 1  # informe enviado

	return cita


def queryfilter_citas_superpuestas(q, hora_ini, hora_fin):
	"""
	aplica un filter() a un query() de Citas de sql alchemy, devolviendo solo
	las citas que se superponen a la hora_ini y hora_fin indicados.

		q   		objeto Query() de sql alchemy
		hora_ini	datetime.datetime
		hora_fin	datetime.datetime
	"""
	# XXX   probar con Oracle!!!! y con MySQL!!!
	# cada motor de bbdd tiene su propia implementación

	#   SQL Server o Oracle 11g (y probablemente inferiores, 10g...)
	if isinstance(engine.dialect, mssql.MSSQLDialect) or\
		isinstance(engine.dialect, oracle.OracleDialect):
		cita_hora_fin = (model.Cita.hora + (model.Cita.duracion/(24.0*60.0)))
	#   MySQL
	elif isinstance(engine.dialect, mysql.MySQLDialect):
		cita_hora_fin = func.ADDTIME(model.Cita.hora, func.SEC_TO_TIME(model.Cita.duracion*60))
##		q = Session.query(model.Cita).filter(func.ADDTIME(model.Cita.hora, func.SEC_TO_TIME(model.Cita.duracion*60)) > model.Cita.hora)

	return q.filter(
		not_(
			or_(
				and_(
					model.Cita.hora	<= hora_ini,
					cita_hora_fin	<= hora_ini,
				),
				and_(
					model.Cita.hora	>= hora_fin,
					cita_hora_fin	>= hora_fin,
				)
			)
		)
	)

##	return q.filter(
##		not_(
##			or_(
##				and_(
##					(model.Cita.hora									) <= hora_ini,
##					(model.Cita.hora + (model.Cita.duracion/(24.0*60.0))) <= hora_ini,
##				),
##				and_(
##					(model.Cita.hora									) >= hora_fin,
##					(model.Cita.hora + (model.Cita.duracion/(24.0*60.0))) >= hora_fin,
##				)
##			)
##		)
##	)


def set_cita(cita, data):
	#import pdb; pdb.set_trace()

	"""
	Asigna los campos de una cita, procesando casos como la hora fin/duracion,
	y teniendo en cuenta restricciones segun agenda, medico o sala, etc...

	Además de modificar el registro Cita, también modifica el registro Cita_ex
	en principio se usa solo para modificar el cita_ex.estado (resultado_enviado en integraciones CAPIO y Gregorio)

	 cita   registro de sql alchemy
	 data   los datos a asignar. es el objeto devuelto por from_params()

	ATENCION: es muy importante que la hora de la cita siempre incluya también la fecha correcta!
	"""
	# los valores finales que tendrá la cita
	fecha = 		data.fecha or cita.fecha
	hora = 			data.hora or cita.hora

	paciente_id =	data.paciente_id	if hasattr(data, 'paciente_id') else	cita.paciente_id
	agenda_id =		data.agenda_id		if hasattr(data, 'agenda_id') else		cita.agenda_id
	sala_id =		data.sala_id		if hasattr(data, 'sala_id') else		cita.sala_id
	medico_id =		data.medico_id		if hasattr(data, 'medico_id') else		cita.medico_id
	aseguradora_id = data.aseguradora_id if hasattr(data, 'aseguradora_id') else        cita.aseguradora_id
	observaciones =	data.observaciones	if hasattr(data, 'observaciones') else	cita.observaciones
	prioridad_id =	data.prioridad_id	if hasattr(data, 'prioridad_id') else	cita.prioridad_id
	tipoExploracion_id =	data.tipoExploracion_id	if hasattr(data, 'tipoExploracion_id') else	cita.tipoExploracion_id
##	paciente_id = 	data.paciente_id or cita.paciente_id
##	agenda_id = 	data.agenda_id or cita.agenda_id
##	sala_id = 		data.sala_id or cita.sala_id
##	medico_id = 	data.medico_id or cita.medico_id
##	observaciones =	data.observaciones or cita.observaciones
	log.debug('agenda_id: %s medico_id: %s sala_id: %s', agenda_id, medico_id, sala_id)

	# comprobar datos obligatorios
	if	not paciente_id or not fecha or not hora:
			raise Exception(_(u'Los siguientes campos de una cita son obligatorios: "paciente_id", "fecha" y "hora"'))#IDIOMAOK
	# XXX   obligatorio id_ext_1¿?
##		or (data.ex.order_number == None):

	# comprobar que el paciente no este deshabilitado, ya que no se permite asignarle nuevas citas
	paciente = misc.registro_by_id(model.Paciente, paciente_id)
	if paciente.deshabilitado:
		raise Exception(_(u'El paciente indicado está deshabilitado. No se puede asignar una nueva cita'))#IDIOMAOK

	# si no hay duracion, comprueba si hay hora_fin para calcular la duracion
	hora_fin = data.hora_fin
	duracion = data.duracion
	if not duracion and hora_fin:
		# si la hora fin es inferior a la de inicio, sumarle un dia (podria ser p.ej. 23:50 - 00:20...)
		if hora_fin < hora: hora_fin = hora_fin + datetime.timedelta(1)
		duracion = (hora_fin - hora).seconds / 60	# la operacion de resta devuelve un datetime.timedelta
	duracion = duracion or cita.duracion
	if not hora_fin:
		if duracion:
		# Se ha tenido que controlar si existe la duración, ya que en integración, se da el caso que no existe hora_fin ni duración
		# Entonces generaba ERROR ya que intentaba utilizar la duración y no existia
			hora_fin = hora + datetime.timedelta(0, duracion)

	# comprobar restricciones
	#  XXX  atencion, aqui se deberían controlar la posibilidad de que si se modifica
	#	   simultaneamente desde 2 puestos, la restriccion se podria no aplicar.
	#	   esto ya pasa en algun otro sitio de la aplicación. Se debería estudiar
	#	   que opciones hay de bloqueos, transacciones, etc... a nivel de BBDD.

	#  si tiene agenda, comprobar que la fecha y hora esten dentro del horario
	# salvo si queremos cancelar la cita.
	agenda = None
	if agenda_id and not (hasattr(data, 'cancelada') and data.cancelada):
		agenda = misc.registro_by_id(model.Agenda, agenda_id)
		check_cita = misc.record()
		check_cita.fecha =	fecha
		check_cita.hora =	hora
		check_cita.duracion = duracion or 15 # si no hubiera duración, se supone de 15 minutos.
		if not misc.find(agenda.horarios, cita_en_horario, check_cita):
			raise Exception(_(u'La cita no está en un horario correcto de la agenda'))#IDIOMAOK
	log.debug('agenda %s', agenda)

	#  si tiene SALA...
	if sala_id:
		# si tiene agenda, comprobar que la agenda acepte esta sala
		if agenda:
			if not misc.find(agenda.salas, lambda rel: rel.sala_id == sala_id):
				raise Exception(_(u'La sala indicada no está disponible en la agenda indicada'))#IDIOMAOK

		# comprobar que en esa fecha y hora no haya otra cita para la misma sala.
		q = meta.Session.query(model.Cita).filter(model.Cita.sala_id == sala_id)
		q = q.filter(model.Cita.exploracion_id == None)
		q = q.filter(or_(model.Cita.cancelada == False, model.Cita.cancelada == None))

		if cita.id: # si no es una nueva cita, filtrarla también
			q = q.filter(model.Cita.id != cita.id)

		q = queryfilter_citas_superpuestas(q, hora, hora_fin)

		if q.count() > 0:
			raise Exception(_(u'La sala indicada ya está ocupada por otra cita en el intervalo de tiempo indicado'))#IDIOMAOK

	#  si tiene MEDICO...
	if medico_id:
		# si tiene agenda, comprobar que la agenda acepte este medico
		if agenda:
			log.debug('agenda.medicos %s', agenda.medicos)
			if not misc.find(agenda.medicos, lambda rel: rel.medico_id == medico_id):
				raise Exception(_(u'El médico indicado no está disponible en la agenda indicada'))#IDIOMAOK

		# comprobar que en esa fecha y hora no haya otra cita para el mismo medico.
		q = meta.Session.query(model.Cita).filter(model.Cita.medico_id == medico_id)
		q = q.filter(model.Cita.exploracion_id == None)
		q = q.filter(or_(model.Cita.cancelada == False, model.Cita.cancelada == None))
		if cita.id:
			q = q.filter(model.Cita.id != cita.id)

		q = queryfilter_citas_superpuestas(q, hora, hora_fin)

		if q.count() > 0:
			raise Exception(_(u'El médico indicado ya está ocupado por otra cita en el intervalo de tiempo indicado'))#IDIOMAOK

	# asignar valores
	cita.paciente_id = 	paciente_id
	cita.fecha =		fecha
	cita.hora =		 hora
	cita.duracion =	 duracion
	cita.agenda_id =	agenda_id
	cita.sala_id =	  sala_id
	cita.medico_id =	medico_id
	cita.aseguradora_id =	aseguradora_id
	cita.observaciones = observaciones
	cita.tipoExploracion_id = tipoExploracion_id
	cita.prioridad_id = prioridad_id
##	if data.paciente_id: cita.paciente_id =	data.paciente_id
##	if data.fecha:		cita.fecha =		data.fecha
##	if data.hora:		cita.hora =			data.hora
##	if duracion:		cita.duracion =		duracion
##	if data.medico_id:	cita.medico_id =	data.medico_id
##	if data.sala_id:	cita.sala_id =		data.sala_id
##	if data.agenda_id:	cita.agenda_id =	data.agenda_id
##	if data.observaciones: cita.observaciones = data.observaciones

	# CITAS_EX
	# XXX   comprobacion de indices
	#	   EN PRINCIPIO SOLO USADO EN INTEGRACION "ANTIGUA" DE CAPIO SIN HL7_PROCESS
	if data.ex.id_ext_1 != None:
		if get_cita_ex(id_ext_1 = data.ex.id_ext_1):
			raise Exception(_(u'Error de integridad. El identificador externo de la cita debe ser único'))#IDIOMAOK
##			abort_xml(400, u'Error de integridad. El identificador externo de la cita debe ser único', codigo=1000)
	if data.ex.id_ext_2 != None:
		if get_cita_ex(id_ext_2 = data.ex.id_ext_2):
			raise Exception(_(u'Error de integridad. El identificador externo de la cita debe ser único'))#IDIOMAOK
	if data.ex.id_ext_3 != None:
		if get_cita_ex(id_ext_3 = data.ex.id_ext_3):
			raise Exception(_(u'Error de integridad. El identificador externo de la cita debe ser único'))#IDIOMAOK
	if data.ex.id_ext_4 != None:
		if get_cita_ex(id_ext_4 = data.ex.id_ext_4):
			raise Exception(_(u'Error de integridad. El identificador externo de la cita debe ser único'))#IDIOMAOK
	# ####################

	# asigna los campos de cita_ex. En principio, esto solo se usa en las integración
	# antigua de CAPIO, y en la del Gregorio que no se ha llegado a poner en producción.
	for campo in CAMPOS_CITA_EX:
		if getattr(data, campo, None):
			setattr( cita.ex, campo, getattr(data, campo) )

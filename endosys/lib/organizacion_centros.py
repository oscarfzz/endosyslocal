"""
Gestión de centros, servicios y salas (componentes organizativos de los centros).
Cualquier parte de EndoSys que acceda a estos recursos debería hacerlo
utilizando este module.

Valorar si se incluye aqui también:
	-la gestión de agendas
	-la info. de valores por defecto (agenda, servicio, centro) de medicos y
	 puestos cliente

TODO:
	-"cachear" automaticamente el listado de centros. Y que haya una función
	 para actualizar/borrar cache.
"""
import logging
import time
import datetime
import endosys.model as model
from endosys.model import meta
import misc
from pylons import config
from sqlalchemy import or_, and_

log = logging.getLogger(__name__)


#   CENTROS

def get_centros():
	"""
	obtiene un list con todos los centros. Cada elemento es un record con los
	mismo campos que model.Centro.
	"""
	q = meta.Session.query(model.Centro)
	centros = []
	registros = q.all()
	for reg in registros:
		centro = misc.record()
		centro.codigo =		reg.codigo
		centro.nombre =		reg.nombre
		centros.append(centro)
	return centros

def centro_by_codigo(codigo):
	q = meta.Session.query(model.Centro).filter('codigo' == codigo)
	total = q.count()
	if total == 1:
		return q.one()
	elif total > 1:
		#	XXX	No deberia pasar!!!
		log.warning('centro_by_codigo() ha devuelto mas de 1 registro. codigo = %s' % (codigo))
		return q.first()
	else:
		return None

def nuevo_centro():
	log.debug('nuevo_centro()')
	centro = model.Centro()
	return centro

def eliminar_centro(centro):
	meta.Session.delete(centro)
	meta.Session.commit()

def guardar_centro(centro):
	#   XXX utiliza "id" para saber si es un nuevo centro (id=None) o
	#   un centro existente que se está modificando (id!=None)
	if centro.id:
		#   modificando, update
		log.debug('guardar_centro() - update (modificar)')
		meta.Session.update(centro)
	else:
		#   nuevo, insert
		log.debug('guardar_centro() - save (crear nuevo)')
		meta.Session.save(centro)

	meta.Session.commit()
	#   en centro.id está el nuevo id (en el caso de que fuera un nuevo centro)

def centro_from_params(params):
	"""
	devuelve un record que representa un centro, con valores extraidos
	de un objeto de parametros HTTP (GET o POST).

	params      objeto request.params, de un controller
	return      objeto record. los nombres de campos coinciden con model.Centro.

	posibles parámetros:
		codigo
		nombre
		servicios y salas?
	"""
	centro = misc.record()
	# campos de centro
	#   preprocesado...
	#   	-
	#   ...asignar params
	centro.nombre =	params.get('nombre', None)
	centro.codigo =	params.get('codigo', None)

	return centro


#   SERVICIOS

def servicio_by_codigo(codigo):
	pass


#   SALAS

def sala_by_codigo(codigo):
	pass


#   PUESTOS CLIENTE

def get_puesto(ip):
	"""
	obtiene un Puesto_cliente a partir de su IP (clave primaria). Si no existe,
	lo crea.
	"""
	q = meta.Session.query(model.Puesto_cliente).filter(model.Puesto_cliente.ip == ip)
	if q.count():
		return q.one()
	else:
		puesto = model.Puesto_cliente()
		puesto.ip = ip
		#Session.save()
		return puesto

def guardar_puesto(puesto, commit=True):
	#   al no tener id no se puede saber si es nuevo o existente mirando si
	#   id tiene valor o no.
	#   la forma correcta es comprobando que tenga el atributo "_instance_key".
	#   si lo tiene ya existia, si no es nuevo.
	if hasattr(puesto, '_instance_key'):
		#   modificando, update
		meta.Session.update(puesto)
	else:
		#   nuevo, insert
		meta.Session.save(puesto)

	if commit:
		meta.Session.commit()
	#   en puesto.ip está el nuevo ip (en el caso de que fuera un nuevo puesto)



#   UTILIDADES...
##def default_centro(username = None, puesto_cliente = None):
##	"""
##	obtiene el Centro por defecto según el Puesto cliente y el usuario.
##	params:
##		username       	usuario (str)
##		puesto_cliente  IP (str) o Puesto_cliente (model)
##		devuelve:       Centro (model)
##
##	de momento solo busca según Puesto_cliente.
##	"""
##	if puesto_cliente:
##		if isinstance(puesto_cliente, str):
##			puesto_cliente = get_puesto(puesto_cliente)
##		return misc.registro_by_id(model.Centro, puesto_cliente.centro_id)

def get_default(username = None, puesto_cliente = None):
	"""
	obtiene valores por defecto según el Puesto cliente y el usuario.
	params:
		username       	usuario (str)
		puesto_cliente  IP (str) o Puesto_cliente (model)
		devuelve:       dict con centro_id, servicio_id y agenda_id (pueden ser None)

	de momento solo busca según Puesto_cliente.
	"""
	ret = {}
	if puesto_cliente:
		if isinstance(puesto_cliente, str):
			puesto_cliente = get_puesto(puesto_cliente)
		ret['centro_id'] = puesto_cliente.centro_id
		ret['servicio_id'] = puesto_cliente.servicio_id
		ret['agenda_id'] = puesto_cliente.agenda_id
	return ret

def set_default(username = None, puesto_cliente = None, **kwargs):
	"""
	asigna valores por defecto al Puesto cliente y/o usuario.
	params:
		username       	usuario (str)
		puesto_cliente  IP (str) o Puesto_cliente (model)
	kwargs (opcionales):
		agenda          agenda id (int) o Agenda (model)
		servicio        servicio id (int) o Servicio (model)
		centro          centro id (int) o Centro (model)

	de momento solo asigna valores al puesto cliente, no al usuario.

	Si se indica agenda, se asigna la agenda, servicio y centro, y se omiten
	otros parametros.
	Si se indica servicio se asigna servicio y centro, y se omiten otros params
	Si se indica centro, se asigna.
	"""
	if puesto_cliente:
		if isinstance(puesto_cliente, str):
			puesto_cliente = get_puesto(puesto_cliente)
		if kwargs.get('agenda', None):
			agenda = kwargs['agenda']
			if isinstance(agenda, int):
				agenda = misc.registro_by_id(model.Agenda, agenda)
			assert(agenda)
 			puesto_cliente.agenda_id = agenda.id
 			puesto_cliente.servicio_id = agenda.servicio.id
 			puesto_cliente.centro_id = agenda.servicio.centro.id
		elif kwargs.get('servicio', None):
			servicio = kwargs['servicio']
			if isinstance(servicio, int):
				servicio = misc.registro_by_id(model.Servicio, servicio)
			assert(servicio)
 			puesto_cliente.servicio_id = servicio.id
 			puesto_cliente.centro_id = servicio.centro.id
		elif kwargs.get('centro', None):
			centro = kwargs['centro']
			if isinstance(centro, int):
				centro = misc.registro_by_id(model.Centro, centro)
			assert(centro)
 			puesto_cliente.centro_id = centro.id
		guardar_puesto(puesto_cliente)


def clear_defaults(**kwargs):
	"""
	Pone a null las referencias a la agenda/servicio/centro indicados. Se utiliza
	cuando se va a eliminar el recurso.

	kwargs:
		agenda_id		  agenda id (int)
		servicio_id		servicio id (int)
		centro_id		  centro id (int)
		commit          indica si se realizará el commit o no (bool, False si se omite)
	"""
	agenda_id = kwargs.get('agenda_id', None)
	servicio_id = kwargs.get('servicio_id', None)
	centro_id = kwargs.get('centro_id', None)
	q = meta.Session.query(model.Puesto_cliente)
	for puesto in q.all():
		log.debug("%s %s", type(puesto.agenda_id), type(agenda_id))
		changed = False
		if agenda_id and puesto.agenda_id == agenda_id:
			puesto.agenda_id = None
			changed = True
		if servicio_id and puesto.servicio_id == servicio_id:
			puesto.servicio_id = None
			changed = True
		if centro_id and puesto.centro_id == centro_id:
			puesto.centro_id = None
			changed = True
		if changed:
			guardar_puesto(puesto, commit=False)
	if kwargs.get('commit', False):
		meta.Session.commit()

# workstations 
def get_workstation(**kwargs):
	"""
	obtiene un registro 'Workstation' a partir de un identificador,
	pasado como kwarg.
	Puede ser:
		id
		nombre
		ip
	"""
	q_ws = meta.Session.query(model.Workstation)
	# filtra los borrados
	q_ws = q_ws.filter(and_(or_(model.Workstation.borrado == 0, model.Workstation.borrado == None)))

	if 'id' in kwargs:
		q_ws = q_ws.filter( model.Workstation.id == kwargs['id'] )
	elif 'ip' in kwargs:
		q_ws = q_ws.filter( model.Workstation.ip == kwargs['ip'] )
		if not q_ws.count() and config.get("WORKSTATIONS.PERMITIR_SIN_IP", '0') == '1':
			# si no hay con esa ip y esta configurado para que funcione con sin IP
			q_ws = meta.Session.query(model.Workstation).filter( model.Workstation.ip == None )
			q_ws = q_ws.filter(and_(or_(model.Workstation.borrado == 0, model.Workstation.borrado == None)))
	elif 'nombre_equipo' in kwargs:
		q_ws = q_ws.filter( model.Workstation.nombre_equipo == kwargs['nombre_equipo'] )
	elif 'nombre' in kwargs:
		q_ws = meta.Session.query(model.Workstation).filter( model.Workstation.nombre == kwargs['nombre'] )
	else:
		raise Exception(u'la función "get_workstation" debe tener 1 solo parámetro "id", "ip", "nombre equipo" o "nombre"')

	
	if q_ws.count():
		return q_ws.one()
	else:
		return None
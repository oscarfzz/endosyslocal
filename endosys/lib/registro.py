"""
Registro de sucesos: para LOPD.

Cualquier operación sobre datos sensibles debe quedar registrada.

Por defecto, cualquier modificación de un dato crea una fila en la
tabla "Registro".

TODO:
	·Que sea configurable si se hace en una tabla, archivo, etc...

	·Que sea configurable las columnas del registro

	·Mejorar el registro (se ha hecho rápido)

	·Llevar un control de versiones especifico de la implementacion del
	 registro de sucesos, para informar a los clientes cuando se actualiza.
	 incluso, hacer que sea opcional actualizar esta parte...

	·El campo RES deberia ser una clave a una tabla, p.ej. "recursos_registro",
	 o ni siquiera con tabla, ya que son estáticos.

	·idea a valorar: en campos tipo memo, realizar una comparación y registrar
	 solo, o resaltar, las palabras cambiadas, no todo.

"""

import logging
import datetime
from endosys.model.registro import Registro
from endosys.model import meta
from endosys.model.pacientes import Paciente
import socket
from pylons import config
from endosys.lib.misc import registro_by_id, formatea_valor
from endosys.lib.organizacion_centros import get_workstation

log = logging.getLogger(__name__)

DEFAULT_REMOTE_USER = 'admin'
USAR_GETHOSTBYADDR = config.get('REGISTRO.USAR_GETHOSTBYADDR', '0') == '1'

#print 'REGISTRO.USAR_GETHOSTBYADDR', config.get('REGISTRO.USAR_GETHOSTBYADDR', '0'), USAR_GETHOSTBYADDR

class res:
	"""
	lista de recursos registrables
	"""
	exploracion =	'EXPLORACION'
	informe =		'INFORME'
	captura =       'CAPTURA'
	cita =          'CITA'
	paciente =      'PACIENTE'
##	formulario =	'FORMULARIO'

class eventos:
	"""
	lista de eventos registrables
	"""
	crear =		'CREAR'
	modificar =	'MODIFICAR'
	eliminar =	'ELIMINAR'
	mostrar =   'MOSTRAR'
	fusionar =  'FUSIONAR'

def estado_exploracion(estado):
	"""
	retorna un valor descriptivo del estado de una exploracion
	"""
	estados = {
		0:  'INICIADA',
		1:  'FINALIZADA',
		2:  'CANCELADA'
	}

	return estados.get(estado, 'OTRO')


def try_get_host(ip):
	"""
	intenta obtener el nombre del host, pero si da error devuelve ''
	"""
	if not USAR_GETHOSTBYADDR: return ''
	try:
		return socket.gethostbyaddr(ip)[0]
	except Exception as e:
		log.error(e)
		return ''


def nuevo_registro(username, ip, exploracion, evento, res, data, old, new):
	"""
	crea un nuevo registro de acceso relacionado con una exploracion
	"""
	r = Registro()

	r.username =        username
	r.ip =              ip
	r.hostname =		try_get_host(ip)
	r.fechahora =		datetime.datetime.today()
	r.idunico =         registro_by_id(Paciente, exploracion.paciente_id).idunico
	if exploracion.servicio is not None:
		r.centro_id = 		exploracion.servicio.centro_id
		for centro in registro_by_id(Paciente, exploracion.paciente_id).centros:
			if centro.centro_id == exploracion.servicio.centro_id:
				r.nhc_centro =	centro.nhc
	r.evento =          evento
	r.res =				res
	r.data =            data
	r.old =             old
	r.new =             new
	r.paciente_id =     exploracion.paciente_id
	r.exploracion_id =  exploracion.id
	r.workstation_id = _obtener_workstation_id(ip)

	meta.Session.save(r)
	meta.Session.commit()


def nuevo_registro_paciente(username, ip, paciente, evento, res, data, old, new, id_hl7_log = None):
	"""
	crea un nuevo registro, relativo solo a un paciente, no a exploracion
	"""
	datos_paciente_old = ""
	datos_paciente_new = ""

	if not paciente: return

	if new:
		datos_centro = ""
		if hasattr(new, "centros"):
			for centro in new.centros:
				datos_centro += " NHC (centro_id: %s) - %s" % (centro.centro_id, centro.nhc)

		datos_paciente_new = "IdUnico - " + formatea_valor(new.idunico) + \
					datos_centro + \
					" CIP - " + formatea_valor(new.CIP) + \
					" nombre - " + formatea_valor(new.nombre)+ \
					" apellido1 - " + formatea_valor(new.apellido1)+ \
					" apellido2 - " + formatea_valor(new.apellido2)+ \
					" fechaNacimiento - " + formatea_valor(new.fechaNacimiento)+ \
					" sexo - " + formatea_valor(new.sexo)+ \
					" DNI - " + formatea_valor(new.DNI)+ \
					" direccion - " + formatea_valor(new.direccion)+ \
					" poblacion - " + formatea_valor(new.poblacion)+ \
					" provincia - " + formatea_valor(new.provincia)+ \
					" codigoPostal - " + formatea_valor(new.codigoPostal)+ \
					" aseguradora_id - " + formatea_valor(new.aseguradora_id)+ \
					" numAfiliacion - " + formatea_valor(new.numAfiliacion)+ \
					" telefono1 - " + formatea_valor(new.telefono1)+ \
					" telefono2 - " + formatea_valor(new.telefono2)+ \
					" comentarios - " + formatea_valor(new.comentarios)+ \
					" numero_expediente - " + formatea_valor(new.numero_expediente)+ \
					" deshabilitado - " + formatea_valor(new.deshabilitado)

	if old:
		datos_centro = ""
		if hasattr(old, "centros"):
			for centro in old.centros:
				if type(centro) == dict:
					datos_centro += " NHC (centro_id: %s) - %s" % (centro["centro_id"], centro["nhc"])
				else:
					datos_centro += " NHC (centro_id: %s) - %s" % (centro.centro_id, centro.nhc)

		datos_paciente_old = "IdUnico - " + formatea_valor(old.idunico) + \
							datos_centro + \
							" CIP - " + formatea_valor(old.CIP) + \
							" nombre - " + formatea_valor(old.nombre)+ \
							" apellido1" \
							" - " + formatea_valor(old.apellido1)+ \
							" apellido2 - " + formatea_valor(old.apellido2)+ \
							" fechaNacimiento - " + formatea_valor(old.fechaNacimiento)+ \
							" sexo - " + formatea_valor(old.sexo)+ \
							" DNI - " + formatea_valor(old.DNI)+ \
							" direccion - " + formatea_valor(old.direccion)+ \
							" poblacion - " + formatea_valor(old.poblacion)+ \
							" provincia - " + formatea_valor(old.provincia)+ \
							" codigoPostal - " + formatea_valor(old.codigoPostal)+ \
							" aseguradora_id - " + formatea_valor(old.aseguradora_id)+ \
							" numAfiliacion - " + formatea_valor(old.numAfiliacion)+ \
							" telefono1 - " + formatea_valor(old.telefono1)+ \
							" telefono2 - " + formatea_valor(old.telefono2)+ \
							" comentarios - " + formatea_valor(old.comentarios)+ \
							" numero_expediente - " + formatea_valor(old.numero_expediente)+ \
							" deshabilitado - " + formatea_valor(old.deshabilitado)



	r = Registro()

	r.username =        username
	r.ip =              ip
	r.hostname =		try_get_host(ip)
	r.fechahora =		datetime.datetime.today()
	r.idunico =         paciente.idunico
	r.evento =          evento
	r.res =				res
	r.data =            data
	r.old =             datos_paciente_old
	r.new =             datos_paciente_new
	r.paciente_id =     paciente.id
	r.exploracion_id =  None
	r.workstation_id = _obtener_workstation_id(ip)
	r.hl7_log_id = id_hl7_log

	meta.Session.save(r)
	meta.Session.commit()

def nuevo_registro_cita(username, ip, cita, evento, res, data, cita_old, id_hl7_log = None):
	"""
	crea un nuevo registro, relativo solo a un paciente, no a exploracion
	"""
	from endosys.lib.pacientes import get_by_id

	datos_cita_old = ""
	datos_cita_new = ""

	if not cita: return

	if cita:

		paciente = get_by_id(cita.paciente_id)
		#   QUITAR_CITA.SERVICIO_ID (se ha quitado servicio_id)
		datos_cita_new = "id - " + formatea_valor(cita.id) + \
					" paciente_id - " + formatea_valor(cita.paciente_id) + \
                    " fecha - " + formatea_valor(cita.fecha)+ \
					" hora - " + formatea_valor(cita.hora)+ \
					" medico_id - " + formatea_valor(cita.medico_id)+ \
					" sala_id - " + formatea_valor(cita.sala_id)+ \
					" tipoExploracion_id - " + formatea_valor(cita.tipoExploracion_id)+ \
					" exploracion_id - " + formatea_valor(cita.exploracion_id)+ \
					" motivo_id - " + formatea_valor(cita.motivo_id)+ \
					" prioridad_id - " + formatea_valor(cita.prioridad_id)+ \
					" cancelada - " + formatea_valor(cita.cancelada)+ \
					" agenda_id - " + formatea_valor(cita.agenda_id)+ \
					" duracion - " + formatea_valor(cita.duracion)
	if cita_old:
		#   QUITAR_CITA.SERVICIO_ID (se ha quitado servicio_id)
		datos_cita_old = "id - " + formatea_valor(cita_old.id) + \
					" paciente_id - " + formatea_valor(cita_old.paciente_id) + \
                    " fecha - " + formatea_valor(cita_old.fecha)+ \
					" hora - " + formatea_valor(cita_old.hora)+ \
					" medico_id - " + formatea_valor(cita_old.medico_id)+ \
					" sala_id - " + formatea_valor(cita_old.sala_id)+ \
					" tipoExploracion_id - " + formatea_valor(cita_old.tipoExploracion_id)+ \
					" exploracion_id - " + formatea_valor(cita_old.exploracion_id)+ \
					" motivo_id - " + formatea_valor(cita_old.motivo_id)+ \
					" prioridad_id - " + formatea_valor(cita_old.prioridad_id)+ \
					" cancelada - " + formatea_valor(cita_old.cancelada)+ \
					" agenda_id - " + formatea_valor(cita_old.agenda_id)+ \
					" duracion - " + formatea_valor(cita_old.duracion)

	r = Registro()

	r.username =		username
	r.ip =			  ip
	r.hostname =		try_get_host(ip)
	r.fechahora =		datetime.datetime.today()
	r.idunico =			paciente.idunico
## el siguiente codigo se ha comentado porque daba problemas al eliminar unca cita mediante hl7 orm de cancelacion
##	if cita.sala is not None:
##		r.centro_id =		cita.sala.centro_id
##		for centro in paciente.centros:
##			if cita.sala.centro_id == centro.centro_id:
##				r.nhc_centro = centro.centro_id
	r.evento =		  evento
	r.res =				res
	r.data =			data
	r.old =			 datos_cita_old
	r.new =			 datos_cita_new
	r.paciente_id =	 paciente.id
	r.exploracion_id =  None
	r.workstation_id = _obtener_workstation_id(ip)
	r.hl7_log_id = id_hl7_log

	meta.Session.save(r)
	meta.Session.commit()

def _obtener_workstation_id(ip=None):
	workstation_id = None
	if ip != None and ip != '':
		workstation = get_workstation(ip=ip)
		if workstation!=None:
			workstation_id = workstation.id

	return workstation_id


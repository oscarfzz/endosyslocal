import logging
import time
import endosys.lib.registro as registro
from endosys.model.pacientes import Paciente, Rel_Pacientes_Centros
from endosys.model import meta
from sqlalchemy.sql import and_, or_, not_

'''
Gestión de pacientes. Cualquier parte de EndoSys que acceda a los pacientes
debería hacerlo utilizando este module.

  XXX rest/pacientes
  XXX plugins...

Accede siempre a la bbdd de EndoSys Web. Se debería implementar aqui la
funcionalidad de los plugins para cambiar el comportamiento
'''

log = logging.getLogger(__name__)

##class Paciente(object):
##	"""
##	representa un paciente
##	"""
##	def __init__(self):
##		pass
##
##	def from_bbdd(self, reg):
##		pass


def get_by_id(id):
	q = meta.Session.query(Paciente).filter(Paciente.id == id)
	if q.count():
		return q.one()
	else:
		return None

##def get_by_historia(nhc, omitir_deshabilitados = True):
##	q = Session.query(Paciente)
##	if omitir_deshabilitados: q = q.filter(or_(Paciente.deshabilitado == False, Paciente.deshabilitado == None))
##	q = q.filter(Paciente.idunico == nhc)
##	if q.count():
####		paciente = Paciente()
####		paciente.from_bbdd(q.one())
####		return paciente
##		return q.one()
##	else:
##		return None

def get_by_idunico(id_unico, omitir_deshabilitados = True):
	return get_by_idunico_generic(meta.Session, Paciente, id_unico, omitir_deshabilitados)

def get_by_idunico_generic(sess, paciente_class, id_unico,omitir_deshabilitados=True):
	q = sess.query(paciente_class)
	if omitir_deshabilitados: q = q.filter(or_(paciente_class.deshabilitado == False, paciente_class.deshabilitado == None))
	q = q.filter(paciente_class.idunico == id_unico)
	if q.count():
		return q.one()
	else:
		return None


def get_by_nhc_centro(nhc, centro, omitir_deshabilitados = True):
	# FALTA IMPLEMENTAR
	pass


def get_by_cip(cip, omitir_deshabilitados = True):
	q = meta.Session.query(Paciente)
	if omitir_deshabilitados: q = q.filter(or_(Paciente.deshabilitado == False, Paciente.deshabilitado == None))
	q = q.filter(Paciente.CIP == cip)
	if q.count():
##		paciente = Paciente()
##		paciente.from_bbdd(q.one())
##		return paciente
		return q.one()
	else:
		return None

def nuevo_paciente():
	return Paciente()

def guardar_paciente(paciente, hl7Process = None):
	#   XXX utiliza "id" para saber si es un nuevo paciente (id=None) o
	#   un paciente existente que se está modificando (id!=None)

	if paciente.id:

		#   modificando, update
		meta.Session.update(paciente)
		meta.Session.commit()
		log.debug( 'Paciente modificado en lib/pacientes')
		# REGISTRAR
		#   la modificacion del paciente

		registro.nuevo_registro_paciente("sysadmin", hl7Process.ipaddress, paciente, registro.eventos.modificar,
						registro.res.paciente, 'Datos', hl7Process.paciente_updating, paciente, hl7Process.id_hl7_log)
		# ####################
	else:
		#   nuevo, insert
		meta.Session.save(paciente)
		meta.Session.commit()
		log.debug( 'Paciente creado en lib/pacientes')
		# REGISTRAR
		#   la creación del paciente

		registro.nuevo_registro_paciente("sysadmin", hl7Process.ipaddress, paciente, registro.eventos.crear,
								registro.res.paciente, 'Datos', None, paciente, hl7Process.id_hl7_log)

		# #################################

	#   en paciente.id está el nuevo id (en el caso de que fuera un nuevo paciente)

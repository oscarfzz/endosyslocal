"""
se ha añadido una nueva entrada de configuración en el INI:
	"MODO_FUSION_PACIENTES"

Indica la lógica que se seguirá al crearse una nueva fusión. Por defecto es 1.

Los tipos definidos de momento son:

1: (por defecto)

	Utilizado normalmente en integraciones HL7

	NO existe el destino:
		siempre crea el destino.
		Si existe el origen se fusiona moviendo las citas y expls al destino
		creado, y finalmente eliminando el origen.
		(Si no existia el origen no se hace nada mas)

	SI existe el destino:
		siempre actualiza el destino.
		Si existe el origen se fusiona moviendo las citas y expls al destino
		creado, y finalmente eliminando el origen.
		(Si no existia el origen no se hace nada mas)

	En resumen, el destino siempre se crea o actualiza, dependiendo de si ya
	existía, y en el caso de existir el origen se fusiona y se elimina.

	Por lo tanto, siempre se espera que vengan los datos del paciente destino
	para poder crearlo/actualizarlo.

2:

	Utilizado en HUCA

	NO existe el destino:
		Si existe el origen se cambia el numero de historia por el de destino
		(Si no existia el origen no se hace nada mas)

	SI existe el destino:
		Si existe el origen se fusiona moviendo las citas y expls al destino
		creado, y finalmente eliminando el origen.
		(Si no existia el origen no se hace nada mas)

"""
import datetime
import logging
from pylons.i18n import _
from xml.etree.ElementTree import Element, SubElement, tostring
from endotools.model import meta
from endotools.model.fusiones import Fusion
from endotools.model.pacientes import Paciente
from endotools.model.citas import Cita
from endotools.model.exploraciones import Exploracion

from endotools.lib.genericREST import *

from authkit.authorize.pylons_adaptors import authorize
from authkit.permissions import RemoteUser, ValidAuthKitUser, UserIn, HasAuthKitRole, And
from endotools.lib.usuarios.seguridad import roles
from pylons import config

import time
from datetime import date

log = logging.getLogger(__name__)

class FusionesController(GenericRESTController):

	def __init__(self, *args, **kwargs):
		GenericRESTController.__init__(self, *args, **kwargs)
		self.tabla = Fusion
		self.nombre_recurso = 'fusion'
		self.nombre_recursos = 'fusiones'
		self.campos_index = ('id','new_pacient', 'old_pacient')

	@authorize(RemoteUser())
	def index(self, format='xml'):
		return GenericRESTController.index(self, format)

	@authorize(RemoteUser())
	def show(self, id, format='xml'):
		return GenericRESTController.show(self, id, format)


	def _modificarPaciente(self, new_paciente, params):
		if 'historia' in params:
			new_paciente.historia = params['historia']
		if 'direccion' in params:
			new_paciente.direccion = params['direccion']
		if 'provincia' in params:
			new_paciente.provincia = params['provincia']
		if 'sexo' in params:
			new_paciente.sexo = params['sexo']
##		if 'fechaNacimiento' in params:
		if params.get('fechaNacimiento', None):
			t = time.strptime(params['fechaNacimiento'], "%d/%m/%Y")
			valor = date(t.tm_year, t.tm_mon, t.tm_mday)
			new_paciente.fechaNacimiento = valor
			#new_paciente.fechaNacimiento = params['fechaNacimiento']
		if 'codigoPostal' in params:
			new_paciente.codigoPostal = params['codigoPostal']
		if 'nombre' in params:
			new_paciente.nombre = params['nombre']
		if 'poblacion' in params:
			new_paciente.poblacion = params['poblacion']
		if 'apellido1' in params:
			new_paciente.apellido1 = params['apellido1']
		if 'apellido2' in params:
			new_paciente.apellido2 = params['apellido2']

		meta.Session.update(new_paciente)
		meta.Session.commit()

		return new_paciente.id


	def _crearPaciente(self, params):
		new_paciente = Paciente()
		if 'historia' in params:
			new_paciente.historia = params['historia']
		if 'direccion' in params:
			new_paciente.direccion = params['direccion']
		if 'provincia' in params:
			new_paciente.provincia = params['provincia']
		if 'sexo' in params:
			new_paciente.sexo = params['sexo']
##		if 'fechaNacimiento' in params:
		if params.get('fechaNacimiento', None):
			t = time.strptime(params['fechaNacimiento'], "%d/%m/%Y")
			valor = date(t.tm_year, t.tm_mon, t.tm_mday)
			new_paciente.fechaNacimiento = valor
##			new_paciente.fechaNacimiento = params['fechaNacimiento']
		if 'codigoPostal' in params:
			new_paciente.codigoPostal = params['codigoPostal']
		if 'nombre' in params:
			new_paciente.nombre = params['nombre']
		if 'poblacion' in params:
			new_paciente.poblacion = params['poblacion']
		if 'apellido1' in params:
			new_paciente.apellido1 = params['apellido1']
		if 'apellido2' in params:
			new_paciente.apellido2 = params['apellido2']
		meta.Session.save(new_paciente)
		meta.Session.commit()

		return new_paciente.id


	def _doCreate(self, params):
		q1 = meta.Session.query(Paciente).filter(Paciente.historia == params['new_pacient'])
		q2 = meta.Session.query(Paciente).filter(Paciente.historia == params['old_pacient'])

		modo_fusion = str( config.get('MODO_FUSION_PACIENTES', '1') )

		# MODO 1:
		if modo_fusion == '1':
			if q1.count() == 0:
				# NO existe el paciente destino
				#   crear paciente destino
				params['historia'] = params['new_pacient']
				id_new = self._crearPaciente(params)
			else:
				# SI existe el paciente destino
				#   modificar el paciente destino con los nuevos datos
				new_paciente = q1.first()
				params['historia'] = params['new_pacient']
				id_new = self._modificarPaciente(new_paciente, params)

			if q2.count() != 0:
				# SI existe el paciente origen
				#   cambiar las citas y exploraciones del paciente origen al paciente destino
				#   eliminar el paciente origen

				id_old =  q2.first().id

				# mirar si el paciente origen tiene citas
				q = meta.Session.query(Cita).filter(Cita.paciente_id == id_old)
				# si tiene citas se le asignan al paciente destino
				if q.count() > 0:
					citas = q.all()
					for cita in citas:
						cita.paciente_id = id_new
						meta.Session.update(cita)

				# mirar si el paciente origen tiene exploraciones
				q_exp = meta.Session.query(Exploracion).filter(Exploracion.paciente_id == id_old)
				# si tiene exploraciones se le asignan al paciente destino
				if q_exp.count() > 0:
					exploraciones = q_exp.all()
					for exploracion in exploraciones:
						exploracion.paciente_id = id_new
						meta.Session.update(exploracion)

				# eliminamos el paciente origen
				paciente_old = q2.first()
				meta.Session.delete(paciente_old)
				meta.Session.commit()

		# MODO 2:
		elif modo_fusion == '2':
			if q2.count() != 0:
				# SI existe el paciente origen

				if q1.count() == 0:
					# NO existe el paciente destino
					#   modificar el numero de historia del de origen por el de destino
					paciente_old = q2.first()
					id_new = self._modificarPaciente(paciente_old, {'historia': params['new_pacient']} )
				else:
					# SI existe el paciente destino
					#   cambiar las citas y exploraciones del paciente origen al paciente destino
					#   eliminar el paciente origen
					id_new = q1.first().id
					id_old = q2.first().id

					# mirar si el paciente origen tiene citas
					q = meta.Session.query(Cita).filter(Cita.paciente_id == id_old)
					# si tiene citas se le asignan al paciente destino
					if q.count() > 0:
						citas = q.all()
						for cita in citas:
							cita.paciente_id = id_new
							meta.Session.update(cita)

					# mirar si el paciente origen tiene exploraciones
					q_exp = meta.Session.query(Exploracion).filter(Exploracion.paciente_id == id_old)
					# si tiene exploraciones se le asignan al paciente destino
					if q_exp.count() > 0:
						exploraciones = q_exp.all()
						for exploracion in exploraciones:
							exploracion.paciente_id = id_new
							meta.Session.update(exploracion)

					# eliminamos el paciente origen
					paciente_old = q2.first()
					meta.Session.delete(paciente_old)
					meta.Session.commit()


		#crea el registro en la tabla fusiones
		return GenericRESTController._doCreate(self, params)

	@conditional_authorize(RemoteUser())
	def create(self):
		p = request.params
		p['day_insert'] = formatea_valor(datetime.datetime.today().date())
		p['hour_insert'] = formatea_valor(datetime.datetime.today().time())
		return self._doCreate(p)


	@conditional_authorize(RemoteUser())
	def update(self, id):
		response.status_code = 405
		return _('ERROR: No se puede modificar un registro de fusion')#IDIOMAOK

	@conditional_authorize(RemoteUser())
	def delete(self, id):
		response.status_code = 405
		return _('ERROR: No se puede eliminar un registro de fusion')#IDIOMAOK
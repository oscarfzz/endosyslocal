''' clase base para crear un plugin de gestion de citas.

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

from endotools.lib.misc import record
from endotools.lib.plugins.base import obj_from_params, Plugin
from datetime import date

# usar los mismos nombres de campos que en la tabla de citas, asi es mas sencillo
class Cita(object):

	def __init__(self, **kwargs):
		self.id = None
		self._codigo = None
		self.fecha = None
		self.hora = None
		self.observaciones = None
		self.paciente_id = None
		self.paciente = record()
		self.tipoExploracion_id = None
		self.tipoExploracion = record()
		self.sala_id = None
		self.sala = record()
		self.sala.id = None
		self.sala.nombre = None

		self.prioridad_id = None
		self.prioridad = record()
		self.prioridad.id = None
		self.prioridad.codigo = None
		self.prioridad.nombre = None
		self.prioridad.nivel = None

		self.servicio_id = None
		self.servicio = record()
		self.servicio.id = None
		self.servicio.nombre = None

		self.medico_id = None
		self.medico = record()
		self.exploracion_id = None
		self.exploracion = record()
##		self.info = record()	#   utilizado para añadir datos adicionales
		self.ex = record()	#   XXX ya no se usa .info, ahora se usa .ex , simulando citas_ex

		self.agenda_id = None
		self.agenda = record()
		self.agenda.id = None
		self.agenda.codigo = None
		self.agenda.nombre = None

		self.duracion  = None

		for k in kwargs: setattr(self, k, kwargs[k])


# de momento me baso en las mismas operaciones REST
class PluginCitas(Plugin):

	def __init__(self):
		Plugin.__init__(self)

	def index(self, params):
		""" devuelve un list de objetos Cita.
		"""
		# XXX falta definir el formato de params y los valores permitidos (un dict seria lo mejor. incluso usar el **kwargs)
		# o podria ser un mismo objeto Cita, con los campos distintos de None siendo el filtro...
		pass

	def show(self, id):
		""" devuelve un objeto Cita con el id indicado """
		pass

	def create(self, cita):
		""" crea una nueva cita a partir del objeto Cita pasado como parametro.
		devuelve el id
		"""
		pass

	def update(self, id, cita):
		""" modifica una cita con el id indicado a partir de los datos del objeto Cita pasado como parametro.
		devuelve un codigo de estado
		
		Si se reimplementa en el plugin, se usara este update y nada del genericrest.
		"""
		pass

	def cancela_cita(self, id, motivo_id):
		""" se ejecuta cuando se cancela una cita (cancelada=1). Sirve para
		notificar a otro sistema si se ha cancelado una cita
		"""
		pass

	def delete(self, id):
		""" elimina una cita con el id indicado.
		devuelve un codigo de estado
		"""
		pass

	def cita_from_params(self, params):
		""" devuelve un objeto Cita a partir de unos params.
		Se llama desde el update del controller de citas
		"""
		cita = Cita()
		obj_from_params(cita, params)
		return cita

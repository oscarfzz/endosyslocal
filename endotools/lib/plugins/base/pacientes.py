''' clase base para crear un plugin de gestion de pacientes.

posibles errores: (usar los mismos codigos http, por conveniencia)

403 - No permitido: no se permite la operacion
401 - No autorizado: la operacion se permite pero no esta autorizado
400 - parametros incorrectos: los parametros suministrados son incorrectos
404 - no se ha encontrado: no existe ningun paciente con el id o parametros de busqueda indicados
500 - error no especificado

estados correctos:
200 - ok
201 - el paciente se ha creado correctamente

'''

# XXX Mejor usar excepciones?

from endotools.lib.plugins.base import E_NoPermitido, Plugin

# usar los mismos nombres de campos que en la tabla de pacientes, asi es mas sencillo
class Paciente(object):

	def __init__(self, **kwargs):
		self.id = None
		self.idunico = None
		self.DNI = None
		self.CIP = None
		self.nombre = None
		self.apellido1 = None
		self.apellido2 = None
		self.sexo = None
		self.fechaNacimiento = None
		self.direccion = None
		self.poblacion = None
		self.provincia = None
		self.codigoPostal = None
		self.aseguradora = None
		self.numAfiliacion = None
		self.telefono1 = None
		self.telefono2 = None
		self.comentarios = None
		self.numero_expediente = None
		self.deshabilitado = None
		self.centros = []
		for k in kwargs: setattr(self, k, kwargs[k])

# de momento me baso en las mismas operaciones REST
class PluginPacientes(Plugin):

	def __init__(self):
		Plugin.__init__(self)

	def index(self, params):
		""" devuelve un list de objetos Paciente.
		"""
		# XXX falta definir el formato de params y los valores permitidos (un dict seria lo mejor. incluso usar el **kwargs)
		# o podria ser un mismo objeto Paciente, con los campos distintos de None siendo el filtro...
		raise E_NoPermitido('No se permite consultar pacientes')

	def show(self, id):
		""" devuelve un objeto Paciente con el id indicado o None si no existe"""
		raise E_NoPermitido('No se permite consultar un paciente')

	def create(self, paciente):
		""" crea un nuevo paciente a partir del objeto Paciente pasado como parametro.
		devuelve el id
		"""
		raise E_NoPermitido('No se permite crear un nuevo paciente')

	def update(self, id, paciente):
		""" modifica un paciente con el id indicado a partir de los datos del objeto Paciente pasado como parametro.
		devuelve un codigo de estado
		"""
		raise E_NoPermitido('No se permite modificar un paciente')

	def delete(self, id):
		""" elimina un paciente con el id indicado.
		devuelve un codigo de estado
		"""
		raise E_NoPermitido('No se permite eliminar un paciente')

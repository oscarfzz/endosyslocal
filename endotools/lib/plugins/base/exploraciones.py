''' clase base para crear un plugin de gestion de exploraciones.

posibles errores: (usar los mismos codigos http, por conveniencia)

403 - No permitido: no se permite la operacion
401 - No autorizado: la operacion se permite pero no esta autorizado
400 - parametros incorrectos: los parametros suministrados son incorrectos
404 - no se ha encontrado: no existe ninguna exploracion con el id o parametros de busqueda indicados
500 - error no especificado

estados correctos:
200 - ok
201 - la exploracion se ha creado correctamente

'''

# XXX Mejor usar excepciones?

from endotools.lib.plugins.base import Plugin

# usar los mismos nombres de campos que en la tabla de exploraciones, asi es mas sencillo
class Exploracion(object):

    def __init__(self, **kwargs):
        self.id = None
##        self.historia = None
##        self.DNI = None
##        self.nombre = None
##        self.apellido1 = None
##        self.apellido2 = None
##        self.sexo = None
##        self.fechaNacimiento = None
##        self.edad = None
##        self.direccion = None
##        self.poblacion = None
##        self.provincia = None
##        self.codigoPostal = None
##        self.aseguradora = None
##        self.numAfiliacion = None
##        self.telefono1 = None
##        self.telefono2 = None
##        self.comentarios = None
        for k in kwargs: setattr(self, k, kwargs[k])


class Exploracion_DICOM_data(object):

    def __init__(self, **kwargs):

		#   si "stored" se deja en None, el Mirth no dicomizará la exploración.
		#   si de deja en False, se dicomizará y se pondrá a True.
		self.stored = None              #   bool

		#   estos datos se tienen que asignar
		self.accessionNumber = None     #   str
		self.studyInstanceUID = None    #   str
		self.studyID = None    			#   str

		#   mas datos
		self.institutionName = None     #   str
		self.stationName = None     	#   str
		self.studyDescription = None    #   str

		#   si los datos de paciente se dejan en None, se extraerán automaticamente
		#   de la BBDD
		self.patientName = None         #   str
		self.patientBirthDate = None    #   Date o str(8)
		self.patientSex = None    		#   'M' o 'F'

		#   si la fecha y hora se dejan en None, se asignarán la fecha y hora de la expl
		self.studyDate = None           #   Date o str(8)
		self.studyTime = None           #   Time o str(6)

		for k in kwargs: setattr(self, k, kwargs[k])


class PluginExploraciones(Plugin):

    def __init__(self):
        Plugin.__init__(self)

    def inicia_exploracion(self, id, medico, params):
        """ se ejecuta cuando se inicia una exploracion. Sirve para notificar a otro
        sistema que se va a realizar una exploracion, etc...
        """
        pass

    def finaliza_exploracion(self, id, medico):
        """ se ejecuta cuando se finaliza una exploracion (se modifica el estado a 1). Sirve para
        notificar a otro sistema si se ha realizado una exploracion, enviar datos, etc...
        """
        pass

    def cancela_exploracion(self, id, medico):
        """ se ejecuta cuando se cancela una exploracion (se modifica el estado a 2). Sirve para
        notificar a otro sistema si se ha cancelado una exploracion iniciada, enviar datos, etc...
        """
        pass

	def get_datos_dicom(self, id):
		""" Cuando se inicia una exploración, primero se crea un registro en la tabla
		"exploraciones_dicom" con los datos necesarios para dicomizar las imágenes de la
		exploración.
		Esta función puede devolver un dict con estos datos, obtenidos mediante la integración.
		Por defecto, si la exploración tenía una cita, y ésta estaba vinculada aun worklist,
		se rellenan los datos con esa información del worklist.
		"""
		return None
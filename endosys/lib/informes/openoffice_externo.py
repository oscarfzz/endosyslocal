#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os, sys, time, threading, json, getpass, base64, logging, logging.handlers
# para conectarse con el ooffice
import pythoncom, win32api
import win32com.client as win32

#3rd Party
try:
	import Image
except ImportError:
	from PIL import Image

# Lista de variables de imagenes: IMAGEN_1...IMAGEN_64 y ${IMAGEN_1}...${IMAGEN_64}
LISTA_VARS_IMAGENES = map(lambda x: 'IMAGEN_%s' % x, range(1,65)) + map(lambda x: '${IMAGEN_%s}' % x, range(1,65))

LOG_DEBUG = "DEBUG"
LOG_ERROR = "ERROR"
LOG_INFO = "INFO"

class Informe():

	service_manager = None
	document = None
	oodesktop = None
	args = None
	log_handler = None
	logger = None
	returncode = 0
	regex_target = r'\$\{[^}]*\}'	
	index_obj_marca_agua =None
	step_info = "-"
	# sintaxis de reg. exp. en la búsqueda de Open Office.
	# info: http://wiki.openoffice.org/wiki/Documentation/How_Tos/Regular_Expressions_in_Writer
	# esta expr. busca correctamente las cadenas del tipo ${variable}.

	# estos parametros se pueden pasar via linea de comandos. 
	# La funcion _parse_arguments encarga de leerlos
	parameters = {
		'template': None,
		'destination': None,
		'datasource': None,
		'blank_image': 'blank.jpg',
		'not_defined_value': u'(no definido)',
		'yes_value': u'Sí'.upper(),
		'watermark': 0,
		'log': 1,
		'log_path' : '',
		'log_level': 'INFO',
		'debug': 0,
		'pdfa':0
	}

	# aqui se guarda el json que se envia por parametro0
	datasource = None

	def __init__(self, args):
		#import pdb; pdb.set_trace()
		self.returncode = 0
		self.args = args
		self._parse_arguments()
		self._set_log()
		self._read_datasource()
		pythoncom.CoInitialize()

		try:
			self._initializate()
			self._open_document()
			self._process_text()
			self._process_images()

			if int(self.parameters["watermark"])==1:
				watermark_filename = self.parameters["destination"].replace('.pdf', '_marca_agua.pdf')
				self._create_pdf(watermark_filename)	

			# efectua el borrado de esa imagen solo si esta ese objeto
			if self.index_obj_marca_agua != None:
				self.document.GraphicObjects.getByIndex(self.index_obj_marca_agua).dispose()

			self._create_pdf()	
			self._close_document()
		except Exception, e:
			self._write_log(str(e), LOG_ERROR)
			self.returncode = 1
		finally:
			pythoncom.CoUninitialize()

	def get_returncode(self):
		return self.returncode

	def _close_document(self):
		self.step_info = "_close_document"
		"""	Intenta cerrar el documento de openoffice
			y el openoffice
		"""
		try:
			self.document.close(False)
			self.oodesktop.terminate()
		except Exception, e:
			self._write_log("No se pudo hacer el terminate",error)

	def _initializate(self):
		self.step_info = "_initializate"
		""" Inicializa el service manager y el oodesktop 
		"""
		# Service Manager es un objeto OLE de OpenOffice, 
		# que hace de interfaz el API de OpenOffice "UNO".
		self.service_manager = win32.Dispatch("com.sun.star.ServiceManager")
		
		# Para poder obtener structs que luego se han de pasar como parametros, se usa
		# una funcion especial "service_manager.Bridge_GetStruct()", y que antes
		# * http://forum.openoffice.org/en/forum/viewtopic.php?f=45&t=13125
		# * http://forum.openoffice.org/en/forum/viewtopic.php?f=44&t=33951&p=155727&hilit=createStruct#p155727
		# Se tiene que inicializar de esta manera:
		self.service_manager._FlagAsMethod("Bridge_GetStruct")
		self.service_manager._FlagAsMethod("Bridge_GetValueObject")
		# Crear objeto Desktop
		#import pdb; pdb.set_trace()
		self.oodesktop = self.service_manager.createInstance("com.sun.star.frame.Desktop")

		self._write_log("Openoffice incializado",LOG_DEBUG)
	
	def _open_document(self):
		self.step_info = "_open_document"
		""" Abre el template y lo pone dentro de la variable document (objeto openoffice)
		"""
		
		# el template viene en b64, hay que transformarlo
		base64_template = self.parameters['template']
		self.parameters['template'] = base64.b64decode(base64_template).decode("latin_1")

		path = "file:///%s" % self.parameters['template']
		args = []

		# si no hay debug, entonces oculta el openoffice, si hay debug se muestra la ventana del openoffice
		if int(self.parameters['debug']) == 0:
			propertyvalue = self.service_manager.Bridge_GetStruct("com.sun.star.beans.PropertyValue")
			propertyvalue.Name = "Hidden"
			propertyvalue.Value = True
			args = [propertyvalue]

		self.document = self.oodesktop.loadComponentFromURL(path, "_blank", 0, args)
		self._write_log("Template abierto por el openoffice: "+base64_template, LOG_DEBUG)

	# crear el pdf desde un documento
	def _create_pdf(self, custom_file_name = None):
		self.step_info = "_create_pdf"
		""" Crea un pdf desde el objeto document de openoffice
		"""

		if custom_file_name:
			file_name = custom_file_name.replace('\\', '/')
		else:
			file_name = self.parameters['destination'].replace('\\', '/')
		

		propertyValueArray=[]
		propertyvalue = self.service_manager.Bridge_GetStruct("com.sun.star.beans.PropertyValue")
		propertyvalue.Name = "FilterName"
		propertyvalue.Value = "writer_pdf_Export"
		propertyValueArray.append(propertyvalue)
		
		
		# Exportamos el pdf en formato pdf/a
		# Si el documento posee marca de agua, cuando el oo exporta a pdf/a converte el documento a blanco
		# por lo que solo se debe transformar el documento sin  marca de agua.
		if self.parameters['pdfa'] and "marca_agua" not in file_name:
			fdata = []
			fdata1 = self.service_manager.Bridge_GetStruct("com.sun.star.beans.PropertyValue")
			fdata1.Name = "SelectPdfVersion"
			fdata1.Value = 1
			fdata2 = self.service_manager.Bridge_GetStruct("com.sun.star.beans.PropertyValue")
			fdata2.Name = "Quality"
			fdata2.Value = 100
			fdata.append(fdata1)
			fdata.append(fdata2)

			FilterData = self.service_manager.Bridge_GetValueObject()
			FilterData._FlagAsMethod("set")
			FilterData.set('[]com.sun.star.beans.PropertyValue', tuple(fdata))

			propertyvalue2 = self.service_manager.Bridge_GetStruct("com.sun.star.beans.PropertyValue")
			propertyvalue2.Name ="FilterData"
			propertyvalue2.Value = FilterData
			propertyValueArray.append(propertyvalue2)
			self._write_log("generando pdf/a", LOG_DEBUG)


		self.document.storeToURL( "file:///%s" % file_name, propertyValueArray )
		self._write_log("Archivo PDF creado: " + file_name, LOG_DEBUG)

	def _parse_arguments(self):
		self.step_info = "_parse_arguments"
		""" lee los argumentos que llegan por parametro. Recorre la lista de self.parameters
			y se fija si existe en la lista de argumentos que vienen por consola. Si existe, 
			almacena el siguiente valor del argumento como valor de ese parametro
		"""
		for argument in list(self.parameters.keys()):
			full_argument = '--' + argument
			if full_argument in self.args:
				self.parameters[argument] = self.args[self.args.index(full_argument) + 1]

	def _read_datasource(self):
		self.step_info = "_read_datasource"
		""" Abre el JSON con la ruta que llega por el parametro --datasource y lo 
			almacena en el atributo datasource de la clase (diccionario)
		"""
		json_file = open(self.parameters["datasource"])
		self.datasource  = json.load(json_file)		
		self._write_log(self.datasource, LOG_DEBUG)

	def _get_value(self, field):
		""" dado un "field" intenta obtener el valor de ese field en el datasource
		"""
		try:
			field = field.upper()
			val = self.datasource[field]
			return val
		except Exception, e:
			# si no existe o da error se asigna como vacio
			# TODO: hacer log?
			return self.parameters['not_defined_value']

	def _get_image_path(self, num):
		""" intenta obtener la ruta de la imagen con el numero que viene por parametro
			Si no la encuentra le asigna el valor de la imagen en blanco que tambien
			viene por paretro
		"""
		try:
			field = ("imagen_ruta_" + num).upper()
			if field in self.datasource:
				val = self.datasource[field]
			else:
				val = self.parameters["blank_image"]
			return val
		except Exception, e:
			logger._write_log(str(e), LOG_ERROR)
			return self.parameters["blank_image"]

	def _process_text(self):
		self.step_info = "_process_text"
		""" busca todas los codigos que estan en la plantilla y los reemplaza por los
			valores que se encuentran en el atributo datasource de la clase
		"""
		# Configurar la busqueda
		# Se aplica a: todas las paginas, texto del documento, contenido de las tablas (y anidadas),
		# todas las secciones, header, footer y marcos.
		descriptor = self.document.createSearchDescriptor()
		descriptor.setSearchString(self.regex_target)
		descriptor.SearchRegularExpression = True

		# Buscar uno a uno
		found = self.document.findFirst(descriptor)
		while found:
			
			# recuperar el valor correspondiente al campo indicado y asignarlo
			field = found.String[2:-1] # elimina el ${ y el }
			if field.find('@') != -1:
				# Titulo
				# Opcion @: muestra el titulo si hay valor
				title, field = field.split('@')
				val = self._get_value(field)

				if val:
					found.String = title
				else:
					found.String = ''
					# Tambien borra el caracter siguiente (salto de linea)
					found.goRight(1,True)
					found.String = ''

			else:
				# Valor de un campo
				
				# lee opciones
				options = ''
				if field.find(':') != -1:
					field, options = field.split(':')

				# valor
				val = self._get_value(field)
				
				# procesado de opciones antes de asignar el valor
				# :X -> indica que si se trata de un booleano, en vez de si/no devolvera
				#		el titulo del campo o cadena vacia.
				if 'X' in options.upper():
					try:
						#import pdb; pdb.set_trace()
						field_type = self._get_value(field + "____tipo")
						field_title = self._get_value(field + "____titulo")
						if int(field_type) == 4:
							if val.upper() == self.parameters['yes_value'].upper(): 
								val = field_title
							else:
								val = ''
					except Exception, e:
						val = ''

				# asignar el valor
				found.String = val

				# procesado de opciones despues de asignar el valor
				# :N -> indica que NO se borra el caracter siguiente si está vacío.
				if not val and not 'N' in options.upper():
					found.goRight(1, True)
					found.String = ''

			found = self.document.findNext(found.End, descriptor)

	def _process_images(self):
		self.step_info = "_process_images"
		""" Busca las imagens del odt y las reemplaza por las rutas de los archivos.
			Si existe el parametro watermark, deja el grafico MARCA_AGUA sino lo elimina
		"""

		index_obj_marca_agua = None
		for i in range(self.document.GraphicObjects.getCount()):
			graphicobject = self.document.GraphicObjects.getByIndex(i)

			try:
				graphicname = str(graphicobject.Name).upper()

				# comprueba si es IMAGEN_N o ${IMAGEN_N} (de 1 hasta 64)
				if graphicname in LISTA_VARS_IMAGENES:
					
					# extrae el numero de imagen (una forma un tanto peculiar, pero correcta...)
					num = int( filter(lambda c: c in '0123456789', graphicname) or 0 )
					# obtiene la ruta de la imagen
					image_path = self._get_image_path(str(num))	
					
					graphicobject.GraphicURL = "file:///%s" % image_path.replace('\\', '/')  # asegurarse de que las barras son /
					self._resize_image(graphicobject, image_path)

				# Marca de agua
				if graphicname == "MARCA_AGUA":
					# Si el template tiene una objeto con el nombre "marca_agua" 
					# y se pide el informe sin marca de agua, entonces guardar el index de ese 
					# objeto para luego borrarlo.
					self.index_obj_marca_agua = i
			except UnicodeEncodeError, e:
				# si el nombre de la imagen tiene algun acento no se corta la generacion
				error_str = "Imagen tiene acento (" + str(e) + ")"
				self._write_log(error_str, LOG_ERROR) 
	
	def _resize_image(self,image_template, path):
		""" Funcion de yeray. Nuestro compañero fugaz que tambien ha dejado su marca en el EndoTools.
			El era una persona de Tenerife y habia estudiado en La Laguna. No sabiamos mucho de su vida, solo
			que vivia con dos venezolanas es lo unico relevante que recuerdo.
		"""
		img = Image.open(path)
		template_ratio = float(image_template.width) / image_template.height
		image_ratio = float(img.size[0]) / img.size[1]
		if image_ratio > template_ratio:
			image_template.height = float(image_template.width) * img.size[1] / img.size[0]
		else:
			image_template.width = float(image_template.height) * img.size[0] / img.size[1]

	def _set_log(self):
		self.step_info = "_set_log"
		""" Configura el log, su nivel, y el lugar donde se almacena
		"""
		try:
			log_enabled = (int(self.parameters['log']) == 1)
		except Exception, e:
			log_enabled = False

		#import pdb; pdb.set_trace()

		if log_enabled:

			if self.parameters['log_path'] == '':
				filename = '/logs/openoffice.log'
			else:
				filename = self.parameters['log_path']

			log_level = logging.ERROR
			if self.parameters['log_level'] == 'INFO':
				log_level = logging.INFO
			elif self.parameters['log_level'] == 'DEBUG':
				log_level = logging.DEBUG
			
			self.log_handler = logging.handlers.RotatingFileHandler(filename, maxBytes=50485760,backupCount=50)
			formatter = logging.Formatter('[%(levelname)s][%(asctime)s] %(message)s')
			self.log_handler.setFormatter(formatter)
			self.logger = logging.getLogger(__name__)
			self.logger.setLevel(log_level)
			self.logger.addHandler(self.log_handler)
			self._write_log("Nueva generacion de informe", LOG_INFO)
			self._write_log("Parametros: " + str(self.parameters), LOG_DEBUG)

	def _write_log(self, msg, lvl):
		try:
			#import pdb; pdb.set_trace()
			msg = "["+self.step_info+"]"+str(msg)
			if lvl.upper() == LOG_INFO:
				self.logger.info(msg)
			if lvl.upper() == LOG_DEBUG:
				self.logger.debug(msg)
			if lvl.upper() == LOG_ERROR:
				self.logger.error(msg)
		except Exception, e:
			self.logger.error("Error al escribir el LOG: " + str(e))

def show_help():
	print "Parametros generales:"
	print "  --template       		La ruta completa del archivo template.odt en base64"
	print "  --destination     		La ruta completa de donde se quiere generar el .pdf"
	print "  --datasource     		La ruta completa del archivo JSON con los datos"
	print "  --watermark      		Si es =1 entonces genera un archivo con marca de agua"
	print "  --log            		Si es =1 entonces se usará log (por defecto = 1)"
	print "  --log_path       		La ruta donde se guardará el log, por defecto usa el working directory"
	print "  --log_level      		El nivel de log (DEBUG, INFO, ERROR)"
	print "  --debug         		Si es =1 entonces abre el OpenOffice cuando se genera el informe"
	print "  --yes_value      		El valor que se usará para interpretar los valores booleanos iguales a True (defecto=Sí)"
	print "  --not_defined_value 	El valor que se usará para asigar los valores no definidos"
	print "  --blank_image  		La ruta en donde se encuentra la imagen en blanco para reemplazar imagenes que no existen (defecto=blank.jpg)"
	print "Parametros de valores:"

# Ejecuta el programa
if __name__ == '__main__':
	
	#print os.path.dirname(os.path.abspath(sys.argv[0]))
	#args = parse_arguments(sys.argv[1])

	if sys.argv[1] == '--help':
		show_help()
	else:
		informe = Informe(sys.argv)
		sys.exit(informe.get_returncode())


'''
Este codigo es un intento de buscar el proceso de soffice y matarlo si quedo abierto. 
No se pone en funcionamiento porque no se puede obtener bien el usuario que esta ejecutando el python
Esta funcion no da un valor preciso: getpass.getuser()
La parte de matar el proceso funciona correctamente
Ademas esta funcion: self._close_document() en teoria se ocupa de cerrar el openoffice y con esto
deberia ser suficiente.
El codigo iria luego del CoUninitialize del openoffice 
'''
'''
pythoncom.CoInitialize()
try:
	user = getpass.getuser()
	self.logger.info("usuario que ejecuta el script:" + user)
	# Busca en los procesos activos
	wmi = win32.GetObject('winmgmts:')
	processes = wmi.InstancesOf('Win32_Process')
	self.logger.info("mata el proceso")
	self.logger.info(str(len(processes)))
	#process_list = [(p.Properties_("ProcessID").Value, p.Properties_("Name").Value) for p in processes]
	for p in processes:
		self.logger.info(p.Properties_("Name").Value)
		if str(p.Properties_("Name").Value) == 'soffice.exe':
			owner = p.ExecMethod_('GetOwner')  
			#Now I can do things with parms like  
			username = owner.Properties_('User').Value
			logger.info("------" + username)
			if username==user:
				print "matar proceso"
				# Kill the proces using pywin32 and pid
				PROCESS_TERMINATE = 1
				handle = win32api.OpenProcess(PROCESS_TERMINATE, False, p.Properties_("ProcessID").Value)
				win32api.TerminateProcess(handle, -1)
				win32api.CloseHandle(handle)
				self.logger.info("matado")
finally:
	pythoncom.CoUninitialize()
'''

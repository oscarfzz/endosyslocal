# 23/03/2017: Los comentarios sobre Openoffice se trasladaron al final del archivo.
import os
import os.path
from pylons import config
import datetime, time, sys, json, threading, logging, subprocess
try:
    import Image
except ImportError:
    from PIL import Image
import pythoncom
import win32com.client as win32
from valores import get_valores,get_valores_imagenes, construir_objeto_exploracion_test, get_no_definido_value
import endosys.lib.capturas
from endosys.lib.formularios import FormExplData
from endosys.lib.misc import abort_json
import ConfigParser
from pylons.i18n import _
import base64

# CONSTANTES
com_sun_star_awt_FontWeight_BOLD = 150.0 # no se usa
stats_informes_path = "logs/report_generation_stats.cfg"
# Lista de variables de imagenes: IMAGEN_1...IMAGEN_64 y ${IMAGEN_1}...${IMAGEN_64}
LISTA_VARS_IMAGENES = map(lambda x: 'IMAGEN_%s' % x, range(1,65)) + map(lambda x: '${IMAGEN_%s}' % x, range(1,65))
IMAGEN_EN_BLANCO = 'blank' # nombre de la imagen en blanco (blank.jpg...)
DEBUG_MOSTRAR_DOC =	False

lock = threading.Lock()
log = logging.getLogger(__name__)

def generar_informe_openoffice(nombre_archivo, exploracion, plantilla, imagenes = None, marca_agua = False, informe = None):
	"""
	Descripción:
		Generar un informe desde una plantilla de OpenOffice en formato ODT.
		El informe generado es directamente un archivo PDF.

	Parametros:
		nombre_archivo: El nombre de archivo PDF
		exploracion: 	es la exploracion de la que se quiere generar el informe.
					 	Ha de ser un objeto de tipo endosys.model.exploraciones.Exploracion
					 	También puede ser un int, en este caso es el id. de un
					 	tipo de exploración, y se utiliza para comprobar si una plantilla
					 	se generaría correctamente (que no falten campos)
		plantilla: 		el nombre del archivo de plantilla de informe. Sin la ruta base pero
				   		con la extensión. p.e: "GASTROSCOPIA 2 FOTOS.doc"
		imagenes: 		las imágenes a mostrar en el informe. Es un registro sqlalchemy de
				  		rel_Capturas_Informes. También puede ser directamente una lista de
				  		ids (int) de Capturas. Puede ser None. Están ordenadas por el "orden"
				  		de rel_Capturas_Informes.
		marca_agua: 	si marca de agua = true genera un archivo extra con el mismo nombre mas "_marca_agua"
						Primero generara el archivo con marca de agua y luego le quitara la marca y lo guardara
						sin marca
	"""



	tipo_generacion = config.get('INFORMES.OPENOFFICE.GENERACION', 'EXTERNO').upper()
	if tipo_generacion == "EXTERNO":
		# Generacion del informe externa
		try:
			reintentos = int(config.get('INFORMES.OPENOFFICE.GENERACION.EXTERNO.REINTENTOS', 1))
		except Exception, e:
			log.error(e)
			reintentos = 1
		estado, error = generar_informe_openoffice_externo(nombre_archivo, exploracion, plantilla, imagenes, marca_agua, informe)
		while reintentos > 0 and estado==False:
			estado, error = generar_informe_openoffice_externo(nombre_archivo, exploracion, plantilla, imagenes, marca_agua, informe)
			reintentos -=1

		if not estado:
			raise Exception(error)
		else:
			return estado


	else:
		# Generacion del informe externa
		generar_informe_openoffice_interno(nombre_archivo, exploracion, plantilla, imagenes, marca_agua, informe)

# -------------------------------------
# CREACION DE INFORMES DE FORMA EXTERNA
# -------------------------------------
def generar_informe_openoffice_externo(nombre_archivo, exploracion, plantilla, imagenes = None, marca_agua = False, informe = None):
	"""
	Descripción:
		Esta funcion llama a un script externo para que en caso de cuelgue no
	 	afecte al servicio de endosys y no haya que reiniciarlo.
	Parametros:
		Los mismos que generar_informe_oppenoffice_externo
	Retorno:
		@estado boolean Estado de la generacion (True: correcto, False: Incorrecto)
	 	@error string Detalle error
	"""

	#obtiene la configuracion del tiempo de espera desde el INI
	try:
		timeout_generacion = int(config.get('INFORMES.OPENOFFICE.TIMEOUT', '30'))
	except Exception,e:
		log.error(e)
		timeout_generacion = 30

	lock.acquire()
	returncode = 0
	error_str = ""

	try:
		log.info("Comienzo de creación de informe: "+nombre_archivo)

		# crea los valores
		valores = get_valores(exploracion, mays = True, formato = 'TEXT', informe = informe)

		# Obtener los comentarios y rutas de las imagenes y añadirlos a "valores"
		valores = dict(valores.items() + get_valores_imagenes(imagenes).items())

		json_file_name = nombre_archivo+'.json'
		with open(json_file_name, 'w') as json_file:
			json.dump(valores, json_file)

		process_parameters = []

		# Buscamos el interprete de Python. Si se está usando Apache `sys.executable` nos devuelve el
		# ejecutable de Apache (httpd), en ese caso lo construimos desde el `prefix` considerando que estamos usando
		# un entorno de `virtualenv`.
		if sys.executable.replace('.exe', '').endswith('httpd'):
			# NOTA: Distinguir si es entorno PortablePython o virtualenv, segun donde este el ejecutable de python
			if os.path.isfile(sys.exec_prefix + 'python') or os.path.isfile(sys.exec_prefix + 'python.exe'):
				# PortablePython
				process_parameters.append(sys.exec_prefix + 'python')
			else:
				# virtualenv
				process_parameters.append(sys.exec_prefix + 'Scripts/python')
		else:
			process_parameters.append(sys.executable)

		process_parameters.append(os.path.join(config['pylons.paths']['root'], 'lib', 'informes', 'openoffice_externo.py'))
		process_parameters.append('--template')
		# se convierte a base64 para evitar conflictos un bug de subprocess.popen
		plantilla_path = os.path.join(config['pylons.paths']['custom_informes_templ'], plantilla)
		plantilla_path = base64.b64encode(plantilla_path.encode("latin_1"))
		process_parameters.append(plantilla_path)

		process_parameters.append('--datasource')
		process_parameters.append(nombre_archivo+'.json')
		process_parameters.append('--destination')
		process_parameters.append(nombre_archivo)
		process_parameters.append('--blank_image')
		process_parameters.append(os.path.join(config['pylons.paths']['root'], 'res', 'blank.jpg'))
		process_parameters.append('--not_defined_value')
		process_parameters.append(get_no_definido_value())
		process_parameters.append('--pdfa')
		process_parameters.append(config.get('INFORMES.OPENOFFICE.GENERACION.EXTERNO.PDFA','0'))

		marca_agua_bit = '0'
		if marca_agua:
			marca_agua_bit = '1'
			process_parameters.append('--watermark')
			process_parameters.append(marca_agua_bit)

		try:
			log_ini = config.get('INFORMES.OPENOFFICE.GENERACION.EXTERNO.LOG', '1')
			process_parameters.append('--log')
			process_parameters.append(log_ini)
		except Exception,e:
			log.error(e)
			log.info("No se pudo configurar el log del script openoffice externo")

		try:
			log_path = config.get('INFORMES.OPENOFFICE.GENERACION.EXTERNO.LOG_PATH', None)
			process_parameters.append('--log_path')
			if log_path:
				process_parameters.append(log_path)
			else:
				process_parameters.append(os.path.join(config['pylons.paths']['root_parent'], 'logs', 'openoffice.log'))
		except Exception,e:
			log.error(e)
			log.info("No se pudo configurar la ruta del log del script openoffice externo")

		try:
			log_level = config.get('INFORMES.OPENOFFICE.GENERACION.EXTERNO.LOG_LEVEL', 'INFO')
			process_parameters.append('--log_level')
			if log_level:
				process_parameters.append(log_level)
		except Exception,e:
			log.error(e)
			log.info("No se pudo configurar el LEVEL del log del script openoffice externo")

		# lanza el proceso
		#import pdb; pdb.set_trace()
		p = subprocess.Popen(process_parameters)
		seconds = 0
		interval = 0.1
		timeout = _get_timeout()
		while p.poll() is None and seconds < timeout:
			time.sleep(interval)
			seconds += interval

		returncode = p.poll()

		if returncode == 0:
			log.info("El informe se genero en:" + str(seconds))
			_set_estadistica(seconds)
		else:
			if returncode is None:
				_set_estadistica_timeout()
			else:
				_set_estadistica_error()

		try:
			# trata de hacer un terminate por si se quedo abierto
			p.terminate()
		except Exception,e:
			log.error(e)

		try:
			#intenta borrar el archivo json
			os.remove(json_file_name)
		except Exception as e:
			log.error(e)

	except UnicodeEncodeError, e:
		log.error(e)
		error_str = _(u"El nombre de la plantilla tiene caracteres no permitidos")#IDIOMAOK
	except Exception, e:
		log.error(e)
		error_str = "openoffice: Error en generar_informe_openoffice_externo: " + str(e)
	finally:
		lock.release()

	generado = True
	if error_str != "":
		# ocurrio un error en el bloque de codigo de esta funcion
		generado = False
	else:
		#se ejecutó el script externo, se analiza si hay error o no
		if returncode is None:
			generado = False
			error_str = "openoffice: Timeout"
		else:
			if returncode != 0:
				generado = False
				error_str = "openoffice: Error " + str(returncode)

	# retorna 2 valores, estado de generacion y string de error
	if not generado:
		log.error(error_str)

	return [generado, error_str]

def _get_timeout():
	"""
	Obtiene el timeout de la generación de informes externo.
	El timeout puede ser fijo o de dinamico (el promedio + 5 segundos calculado por los tiempo que han tardado los informes anteriores)
	"""

	#obtiene si el timeout se calcula o es fijo con la otra clave
	try:
		timeout_calculado = (config.get('INFORMES.OPENOFFICE.GENERACION.EXTERNO.TIMEOUT.CALCULADO.ENABLED', True) == '1')
	except Exception,e:
		log.error(e)
		timeout_calculado = True

	#Obtener el timeout fijo. Por defecto: 30
	try:
		timeout_fijo = int(config.get('INFORMES.OPENOFFICE.GENERACION.EXTERNO.TIMEOUT.FIJO', 30))
	except Exception, e:
		log.error(e)
		timeout_fijo = 30

	# devolver el timeout
	if not timeout_calculado:
		return timeout_fijo
	else:
		#timeout margen. El timeout es igual a timeout + margen. Por defecto: 5
		try:
			timeout_margen = int(config.get('INFORMES.OPENOFFICE.GENERACION.EXTERNO.TIMEOUT.CALCULADO.MARGEN', 5))
		except Exception, e:
			log.error(e)
			timeout_margen = 5

		#obtener el timeout promedio
		try:
			stats_file = ConfigParser.RawConfigParser()
			stats_file.read(stats_informes_path)
			intentos = int(stats_file.get('Estadisticas', 'realizados'))
			tiempo_total = float(stats_file.get('Estadisticas', 'tiempo_total'))
			promedio = tiempo_total / float(intentos)
			timeout = promedio + timeout_margen
		except Exception as e:
			log.error(e)
			timeout = timeout_fijo

		log.info("Timeout Generación de informes:" + str(timeout))
		return timeout

def _get_estadistica_config():
	stats_file = ConfigParser.RawConfigParser()
	# si no existe crear archivo con valores a 0
	if not os.path.exists(stats_informes_path):
		stats_file.add_section('Estadisticas')
		stats_file.set('Estadisticas', 'realizados', '0')
		stats_file.set('Estadisticas', 'tiempo_total', '0')
		stats_file.set('Estadisticas', 'maximo', '0')
		stats_file.set('Estadisticas', 'error', '0')
		stats_file.set('Estadisticas', 'timeout', '0')
		with open(stats_informes_path, 'wb') as configfile:
			stats_file.write(configfile)

	stats_file.read(stats_informes_path)
	return stats_file

def _set_estadistica(seconds):
	# si no fallo al generar, entonces actualizo la media de generacion de informe
	# para actualizar el timeout
	stats_file = _get_estadistica_config()

	intentos = int(stats_file.get('Estadisticas', 'realizados')) + 1
	maximo = float(stats_file.get('Estadisticas', 'maximo'))
	tiempo_total = float(stats_file.get('Estadisticas', 'tiempo_total')) + float(seconds)

	#actualiza los valores
	stats_file.set('Estadisticas', 'realizados', str(intentos))
	stats_file.set('Estadisticas', 'tiempo_total', str(tiempo_total))

	#actualiza el tiempo maximo
	if seconds > float(maximo):
		maximo = seconds
		stats_file.set('Estadisticas', 'maximo', str(maximo))

	with open(stats_informes_path, 'wb') as configfile:
		stats_file.write(configfile)

def _set_estadistica_error():
	stats_file = _get_estadistica_config()
	cant_error = int(stats_file.get('Estadisticas', 'error')) + 1
	stats_file.set('Estadisticas', 'error', str(cant_error))
	with open(stats_informes_path, 'wb') as configfile:
		stats_file.write(configfile)

def _set_estadistica_timeout():
	stats_file = _get_estadistica_config()
	cant_timeout = int(stats_file.get('Estadisticas', 'timeout')) + 1
	stats_file.set('Estadisticas', 'timeout', str(cant_timeout))
	with open(stats_informes_path, 'wb') as configfile:
		stats_file.write(configfile)

# -------------------------------------
# CREACION DE INFORMES DE FORMA INTERNA
# -------------------------------------
# Solo se usa cuando INFORMES.OPENOFFICE.GENERACION=INTERNO
def generar_informe_openoffice_interno(nombre_archivo, exploracion, plantilla, imagenes = None, marca_agua = False, informe = None):

	def getCampoData(formularios, nombre):
		"""
		Busca un campo por su nombre en la lista de formularios y devuelve
		el CampoData (ver lib/formularios.py)
			nombre	es case-insensitive
		Si no lo encuentra devuelve None
		"""
		nombre = nombre.upper()
		for formulario in formularios:
			for grupoCampos in FormExplData(formulario).gruposCampos:
				for campodata in grupoCampos.campos:
					if (campodata.nombre.upper() == nombre):
						return campodata
		return None

	regex_oo = r'\$\{[^}]*\}'	# sintaxis de reg. exp. en la búsqueda de Open Office.
								# info: http://wiki.openoffice.org/wiki/Documentation/How_Tos/Regular_Expressions_in_Writer
								# esta expr. busca correctamente las cadenas del tipo ${variable}.

	if isinstance(exploracion, int):
		# se trata de id de un tipo de exploración, por lo tanto poner
		# datos ficticios, para chequear la plantilla.
		# En este caso no vendrán imágenes, asi que se generan también unas
		# de prueba.
		exploracion = construir_objeto_exploracion_test(exploracion)
		#imagen_en_blanco = 'test'
	valores = get_valores(exploracion, mays = True, formato = 'TEXT', informe = informe)

	# Obtener los comentarios de las imagenes y añadirlos a "valores", ya que
	# en la plantilla se tratan igual
	valores = dict(valores.items() + get_valores_imagenes(imagenes).items())

	pythoncom.CoInitialize()
	lock.acquire()
	try:
		# Service Manager es un objeto OLE de OpenOffice, que hace de interfaz
		# con el API de OpenOffice "UNO".
		service_manager = win32.Dispatch("com.sun.star.ServiceManager")
		# para poder obtener structs que luego se han de pasar como parametros, se usa
		# una funcion especial "service_manager.Bridge_GetStruct()", y que antes
		#   http://forum.openoffice.org/en/forum/viewtopic.php?f=45&t=13125
		#   http://forum.openoffice.org/en/forum/viewtopic.php?f=44&t=33951&p=155727&hilit=createStruct#p155727
		# se tiene que inicializar de esta manera:
		service_manager._FlagAsMethod("Bridge_GetStruct")
		##service_manager._FlagAsMethod("Bridge_CreateType")
		# crear objeto Desktop
		oodesktop = service_manager.createInstance("com.sun.star.frame.Desktop")

		doc = None
		try:
			# abrir documento plantilla
			#   XXX ojo, es posible que la ruta tenga que ser toda con /, p.e. c:/prueba/plantilla.odt, en vez de \\
			#   XXX ocultar el documento aqui?
			args = []
			if not DEBUG_MOSTRAR_DOC:
				propertyvalue = service_manager.Bridge_GetStruct("com.sun.star.beans.PropertyValue")
				propertyvalue.Name = "Hidden"
				propertyvalue.Value = True
				args = [propertyvalue]
			##			propertyvalue.Name = "ReadOnly"
			doc = oodesktop.loadComponentFromURL(
				"file:///%s" % os.path.join(config['pylons.paths']['custom_informes_templ'], plantilla),
				"_blank", 0, args)

			#oodesktop.addTerminateListener()	# http://markmail.org/message/igzjyacbhjkwq7rx#query:+page:1+mid:uijjnqvhppudce2a+state:results

			# configurar la busqueda
			#   comprobado que se aplica a: todas las paginas, texto del documento,
			#	contenido de las tablas (y anidadas), todas las secciones, header,
			#   footer y marcos.
			descr = doc.createSearchDescriptor()
			descr.setSearchString(regex_oo)
			descr.SearchRegularExpression = True

			# Buscar uno a uno
			found = doc.findFirst(descr)
			while found:
				#found.CharWeight = 150.0
				# recuperar el valor correspondiente al campo indicado y asignarlo
				campo = found.String[2:-1]
				if campo.find('@') != -1:
					# si hay una @, se trata de un titulo de un campo que se mostrará
					# según si dicho campo tiene valor o no
					titulo, campo = campo.split('@')
					campo = campo.upper()
					valor = valores.get(campo, get_no_definido_value())
					if valor:
						found.String = titulo
					else:
						found.String = ''
						# borrar también el caracter siguiente (normalmente un salto de linea)
						found.goRight(1, True)
						found.String = ''
				else:
					# se trata del valor de un campo.
					#  opcion :N a continuación -> indica que NO se borra el caracter siguiente si está vacío.
					#  por defecto si que se borra, util para quitar la linea vacía.
					#  opcion :X a continuación -> indica que si se trata de un booleano, en vez de si/no devolverra
					#  el titulo del campo o cadena vacia.
					opciones = ''
					if campo.find(':') != -1:
						campo, opciones = campo.split(':')
					campo = campo.upper()
					valor = valores.get(campo, get_no_definido_value())
					opciones = opciones.upper()

					# :X
					if 'X' in opciones:
						# Buscar el campo para ver si es booleano y usar el titulo del mismo cuando es True
						campodata = getCampoData(exploracion.formularios, campo)
						if campodata and campodata.tipo == 4: # tipo 4 es booleano
							if valor == u'sí': valor = campodata.titulo #xxx IDIOMA !!! se tendría que traducir el "sí"
							else: valor = ''

					if valor:
						found.String = valor
					else:
						found.String = ''
						if not 'N' in opciones:
							found.goRight(1, True)
							found.String = ''
				found = doc.findNext(found.End, descr)

			# ejemplo de Replace:
			##			#	configurar la busqueda y reemplazo:
			##			descr = doc.createReplaceDescriptor()
			##			descr.setSearchString(regex_oo)
			##			descr.setReplaceString("<VARIABLE>")
			##			descr.SearchRegularExpression = True
			##			#	...además se pone el texto en negrita
			##			propertyvalue = service_manager.Bridge_GetStruct("com.sun.star.beans.PropertyValue")
			##			propertyvalue.Name = "CharWeight"
			##			propertyvalue.Value = com_sun_star_awt_FontWeight_BOLD
			##			descr.setReplaceAttributes( [propertyvalue] )
			##			#	reemplazar
			##			doc.replaceAll(descr)

						# Buscar todas las imágenes.
						#   La forma de identificarlas es por el "Nombre", que se asigna desde
						#   el mismo OpenOffice, e identifica de manera única las imágenes y Marcos.
						#   asi, el nombre tendrá que ser ${imagen_N} o imagen_N
						#   comprobado: se recorren todas las imagenes esten en tablas, headers, etc...
						#		(se puede iterar por nombres o por index... lo haremos por index)
			##			for nombre in doc.GraphicObjects.getElementNames():
			##				graphicobject = doc.GraphicObjects.getByName(nombre)
			index_obj_marca_agua = None
			for i in range(doc.GraphicObjects.getCount()):
				graphicobject = doc.GraphicObjects.getByIndex(i)
				graphicname = str(graphicobject.Name).upper()
				# comprueba si es IMAGEN_N o ${IMAGEN_N} (de 1 hasta 64)
				if graphicname in LISTA_VARS_IMAGENES:
					# extrae el numero de imagen (una forma un tanto peculiar, pero correcta...)
					num = int( filter(lambda c: c in '0123456789', graphicname) or 0 )
					if num and imagenes and num <= len(imagenes):
						if isinstance(imagenes[num-1], int):
							captura_id = imagenes[num-1]
						else:
							captura_id = imagenes[num-1].captura_id

						#ruta = config['pylons.paths']['capturas']
						#ruta_subcategoria = self._construir_ruta(ruta,captura_id)

						s = endosys.lib.capturas._archivo(captura_id)
					else:
						s = os.path.join(config['pylons.paths']['root'], 'res', '%s.jpg' % IMAGEN_EN_BLANCO)
					graphicobject.GraphicURL = "file:///%s" % s.replace('\\', '/')  # asegurarse de que las barras son /
					_resize_image(graphicobject, s)

				if graphicname == "MARCA_AGUA":
					# Si el template tiene una objeto con el nombre "marca_agua"
					# y se pide el informe sin marca de agua, entonces guardar el index de ese
					# objeto para luego borrarlo.
					index_obj_marca_agua = i

			if marca_agua:
				# se pidio que se genere un archivo con marca de agua
				nombre_archivo_marca_agua = nombre_archivo.replace('\\', '/')  # asegurarse de que las barras son /
				# Se cambiara el nombre de archivo para que tenga el _marca_agua al final
				nombre_archivo_marca_agua = nombre_archivo_marca_agua.replace('.pdf', '_marca_agua.pdf')  # asegurarse de que las barras son /
				propertyvalue = service_manager.Bridge_GetStruct("com.sun.star.beans.PropertyValue")
				propertyvalue.Name = "FilterName"
				propertyvalue.Value = "writer_pdf_Export"   # formato .PDF  ("MS Word 97" formato .DOC)
				doc.storeToURL( "file:///%s" % nombre_archivo_marca_agua, [propertyvalue] )

			# efectua el borrado de esa imagen solo si esta ese objeto
			if index_obj_marca_agua != None:
				doc.GraphicObjects.getByIndex(index_obj_marca_agua).dispose()

			# Guardar como PDF
			nombre_archivo = nombre_archivo.replace('\\', '/')  # asegurarse de que las barras son /
			propertyvalue = service_manager.Bridge_GetStruct("com.sun.star.beans.PropertyValue")
			propertyvalue.Name = "FilterName"
			propertyvalue.Value = "writer_pdf_Export"   # formato .PDF  ("MS Word 97" formato .DOC)
			doc.storeToURL( "file:///%s" % nombre_archivo, [propertyvalue] )
			##			# XXX guardar el .odt (sería FilterName=writer8)
			##			doc.storeAsURL( "file:///%s" % (os.path.splitext(nombre_archivo)[0] + '.odt'), [] )
		finally:
			# Cerrar el documento abierto por EndoSys
			# XXX a veces las lineas doc.close(False) y oodesktop.terminate() dan error
			# (" <unknown>.close", "Error en la llamada a procedimiento remoto."...)
			# ponerlas en try...except?
			if not DEBUG_MOSTRAR_DOC:
				if doc: doc.close(False)
				# tambien cierra soffice.exe
				last_close_time = config.get('openoffice.last_close_time', None)

				if config.get('OPENOFFICE.CERRAR', '1') == '1':
					# si han pasado 5 minutos...
					if not last_close_time or ((datetime.datetime.now() - last_close_time) > datetime.timedelta(0, 60*5)):
						# y no hay documentos abiertos...
						if not oodesktop.getComponents().hasElements():
							# cerrar openoffice y guardar la hora en que se ha cerrado
							oodesktop.terminate()	 # esto cierra openoffice totalmente (los procesos soffice.exe y soffice.bin)
							config['openoffice.last_close_time'] = datetime.datetime.now()

	finally:
		lock.release()
		pythoncom.CoUninitialize()

# Solo se usa cuando INFORMES.OPENOFFICE.GENERACION=INTERNO. Cuando es =EXTERNO esta funcion ya esta contenido
# en el openoffice_externo.py
def _resize_image(image_template, path):
	img = Image.open(path)
	template_ratio = float(image_template.width) / image_template.height
	image_ratio = float(img.size[0]) / img.size[1]
	if image_ratio > template_ratio:
		image_template.height = float(image_template.width) * img.size[1] / img.size[0]
	else:
		image_template.width = float(image_template.height) * img.size[0] / img.size[1]


"""
	IMPORTANTE:

	Se requiere OpenOffice 3.4.1.

	En el registro de Windows, en la clave:

	  HKEY_CLASSES_ROOT\CLSID\{82154420-0FBF-11d4-8313-005004526AB4}\LocalServer32

	  (en SO de 64 bits: HKEY_CLASSES_ROOT\Wow6432Node\CLSID\{82154420-0FBF-11d4-8313-005004526AB4}\LocalServer32)

	se puede configurar el comando que lanza OpenOffice (la ruta a soffice.exe). Además
	se pueden añadir parámetros. Es importante añadir estos:
		-norestore	  para evitar que salga el asistente de recuperacion si se ha cerrado incorrectamente
		-headless	   parece que ejecuta OpenOffice en modo "servicio" o algo asi...
						evita que se ejecute el "inicio rapido" en el tray

		otros interesantes: -invisible (creo que mejor -headless)
							-nofirstwizard -> no se muestra el asistente la primera vez...
											  es un arg antiguo no se si aun funciona.

	Además interesa mantener -nodefault y -nologo, para no mostrar la pantalla principal por defecto
	ni el logotipo, respectivamente.

		(con soffice.exe -h se pueden ver todos los posibles parametros)

	NOTA: con -headless , al cerrar el ultimo documento abierto, tambien se cierra
		  el proceso de soffice.exe, por lo que no se si conviene...

	SE RECOMIENDA DEJARLO ASI:

	(...)\soffice.exe -nodefault -nologo -norestore -headless

	-----------------------------------------------------------------------

	Este archivo está basado en msword.py, por lo que mantiene una estructura similar.

	XXX OJO: Controlar el hecho de que el programa OpenOffice podría estar abierto y en
	uso en el equipo. Esto podría ocasionar por ejemplo que se cierre un documento
	que el usuario estaba editando sin guardar los cambios, o que si de alguna forma
	el programa está bloqueado (p.e. un dialogo que tiene abierto el usuario) no se
	pueda generar el informe...
	Se podría estudiar la opción de crear una instancia exclusiva para uso de
	EndoSys, que no interfiera con la posible aplicación abierta por un usuario.

	NOTA:	XXX Con Word ya se controla, si hay algún otro documento abierto sin guardar
			no se cierra Word... hacer lo mismo con OpenOffice!

	información:

		http://www.openoffice.org/api/basic/man/tutorial/tutorial.pdf
		http://www.openoffice.org/udk/common/man/tutorial/office_automation.html
		http://www.openoffice.org/api/docs/common/ref/com/sun/star/frame/XStorable.html#storeAsURL
		http://wiki.openoffice.org/wiki/Documentation/DevGuide/Text/Saving_Text_Documents
		http://forum.openoffice.org/en/forum/viewtopic.php?f=45&t=13125
		http://forum.openoffice.org/en/forum/viewtopic.php?f=44&t=33951&p=155727&hilit=createStruct#p155727

		Extracto de una web ya no disponible:

			I used ADO 2.5 in my last Python project, and had no problems at all.
			Most of the time, ADO access in VB translates almost directly to python
			syntax. Features of ADO I used with no problem include parameterized
			commands, batch updating and client side cursors.

			One thing to keep in mind is the way pythoncom handles out-parameters of
			method calls: These values are returned as part of the method result,
			e.g the Execute method of the Connection object returns a tuple
			consisting of an RecordSet object and the RecordsAffected value (see
			MSDN):

				recordset, affected = db_connect.Execute("select * from ...")

			In VB you would only get the recordset returned and RecordsAffected
			would get stuffed in a reference parameter of the call.

			Another point is handling of date values: They are returned as objects
			with type pywintypes.TimeType. The documentation for this type is very
			terse, and I had to dig into the pythoncom demos to find their
			interface: One useful method is Format(<formatstring>), which will
			return a string from TimeType:

				import pywintypes
				if type(x) == pywintypes.TimeType:
					return x.Format("%d.%m.%Y")

			For more information on COM and Python I recommend Mark Hammond's
			"Python Programming on Win32" (which covers almost the entire COM body,
			albeit sometimes not too deeply: "Advanced Python Programming..." ?),
			which has a chapter on database programming.

"""

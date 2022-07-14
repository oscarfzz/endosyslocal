""" En este archivos hay funciones varias
"""
import time
import datetime
import simplejson
import csv
import os
import logging

import pylons
from pylons import config
from pylons.i18n import _
from sqlalchemy.orm.collections import InstrumentedList
import paste.httpexceptions as httpexceptions
from paste.response import replace_header
from decorator import decorator
from xml.etree.ElementTree import Element, SubElement, tostring

from endosys.model import meta
from endosys.model.medicos import Medico
from endosys.model.configuraciones import Configuracion
from endosys.lib.base import *

log = logging.getLogger(__name__)

class HTTPErrorXML(httpexceptions.HTTPError):

	code = 500

	def __init__(self, status=None, detail=None, style=0, headers=None, comment=None, code=None):
		log.debug('HTTPErrorXML: status=%s, detail=%s', status, detail)
		if status: self.code = status
		self.style = style
		self.endotools_code = code or 0
		httpexceptions.HTTPError.__init__(self, detail, headers, comment)

	# devolver en xml (hago creer a la clase base que lo pide plain...)
	def plain(self, environ):
		return "<error><mensaje>%s</mensaje><estilo>%s</estilo><codigo>%s</codigo></error>" % (self.detail, self.style, self.endotools_code) + ' '*512 # el IE no muestra la pagina 404 si ocupa menos de 512 bytes

	# hago que devuelva el error en XML
	def prepare_content(self, environ):
		environ['is_HTTPErrorXML'] = True	   # con esto evito que se muestren las plantillas de pylons para el 401, 404, etc... (ver config/middleware.py)
		http_accept = None
		if 'HTTP_ACCEPT' in environ: # si el request tenia ACCEPT, guardar el valor original
			http_accept = environ['HTTP_ACCEPT']
		environ['HTTP_ACCEPT'] = 'text/plain'   # que se piense que se pide plain...
		headers, content = httpexceptions.HTTPError.prepare_content(self, environ) # se ejecutara self.plain
		if http_accept:
			environ['HTTP_ACCEPT'] = http_accept	# restauro el valor original
		else:
			del environ['HTTP_ACCEPT'] # si no tenia ACCEPT lo quito
		replace_header(headers, 'content-type', 'text/xml')
		return headers, content

class HTTPErrorJSON(httpexceptions.HTTPError):

	code = 500

	def __init__(self, status=None, detail=None, style=0, headers=None, comment=None, code=None):
		#print 'HTTPErrorJSON: status=%s, detail=%s' % (status, detail)
		if status: self.code = status
		self.style = style
		self.endotools_code = code or 0
		httpexceptions.HTTPError.__init__(self, detail, headers, comment)

	def plain(self, environ):
		return self.detail

	# hago que devuelva el error en JSON
	def prepare_content(self, environ):
		#from nose.tools import set_trace; set_trace()
		#print environ
		environ['is_HTTPErrorJSON'] = True	   # con esto evito que se muestren las plantillas de pylons para el 401, 404, etc... (ver config/middleware.py)
		http_accept = None
		if 'HTTP_ACCEPT' in environ: # si el request tenia ACCEPT, guardar el valor original
			http_accept = environ['HTTP_ACCEPT']
		environ['HTTP_ACCEPT'] = 'text/plain'   # que se piense que se pide plain...
		headers, content = httpexceptions.HTTPError.prepare_content(self, environ) # se ejecutara self.plain
		if http_accept:
			environ['HTTP_ACCEPT'] = http_accept	# restauro el valor original
		else:
			del environ['HTTP_ACCEPT'] # si no tenia ACCEPT lo quito
		replace_header(headers, 'content-type', 'application/json;')
		return headers, content

def abort_xml(status=500, mensaje=None, estilo=1, codigo=None):
	response.content_type = "text/xml"
	raise HTTPErrorXML(status, detail=mensaje, style=estilo, headers=None, comment=None, code=codigo)

def abort_json(status=500, json_or_str=None, error_code=None):
	response.content_type = "application/json"

	data_dict = {}
	
	# Mensaje del error
	if type(json_or_str) is dict:
		data_dict = json_or_str
	else:
		data_dict = {'data': json_or_str}

	# Agrega un codigo de error si viene por parametro para identificar el error en
	# el caso de que una funcion envie el mismo codigo con el mismo error.
	# Ej. Usado en create de exploraciones.js
	try: 
		if error_code:
			data_dict["error_code"] = str(error_code)
	except Exceptions as e:
		log.error(e)

	# transforma a string el json
	data = simplejson.dumps(data_dict)

	raise HTTPErrorJSON(status=status, detail=data, style=None, headers=None, comment=None, code=None)

def abort(format="json", status=500, mensaje=None, error_code=None, estilo=1):
	if format == "json":
		abort_json(status, json_or_str=None, error_code=error_code)
	if format == "xml":
		abort_xml(status, mensaje=mensaje, estilo=estilo, codigo=error_code)
	else:
		abort_xml(status, mensaje=mensaje, estilo=estilo, codigo=error_code)

def generic_abort(frmt="json", status=500, mensaje=None, error_code=None, estilo=1):
	if frmt == "json":
		abort_json(status=status, json_or_str=mensaje, error_code=error_code)
	if frmt == "xml":
		abort_xml(status=status, mensaje=mensaje, estilo=estilo, codigo=error_code)
	else:
		abort_xml(status=status, mensaje=mensaje, estilo=estilo, codigo=error_code)

class record(object):
	def __init__(self, **kwargs):
		for k in kwargs: setattr(self, k, kwargs[k])

	def __repr__(self):
		return 'record(**%r)' % self.__dict__

	def __str__(self):
		return str(self.__dict__)

def registro_by_id(tabla, id):
	""" obtiene un registro a partir de su Id """
	q = meta.Session.query(tabla).filter(tabla.id == id)
	if q.count():
		return q.one()
	else:
		return None

def medico_from_user(username):
	""" obtiene el registro de la tabla medicos
	a partir del username asignado al mismo
	"""
	q = meta.Session.query(Medico)
	q = q.filter(Medico.username == username)
	return q.one()

def formatea_valor(valor):

	"""
	Formatea un valor de un campo de una tabla del tipo que sea
	para asignarlo como texto en un XML
	"""

	# si esta vacio, devolver cadena vacia
	if valor is None:
		return ''

##	# si es una lista de otros campos, recorrerla
##	if isinstance(valor, InstrumentedList):
##		return '(InstrumentedList)'

	# si es un bool, devolver como string, 'si' o 'no'
	# XXX mejor devolver 1 o 0
	if isinstance(valor, bool):
##		return 's\xED' if valor else 'no'
##		return formatea_valor(u'si') if valor else formatea_valor(u'no')
		return u'sí' if valor else u'no'

	# NOTA:	Tomamos como convención que los campos de tipo Date son fechas y los de
	#	   tipo DateTime son horas, aunque en BBDD se guarden ambos como DATETIME.
	#	   (esto se aplica para los valores de campos de sqlalchemy)

	# si es un datetime devolver como string con formato horas:minutos:segundos,
	# ya que convenimos que los datetime de sqlalchemy son horas.
	if isinstance(valor, datetime.datetime):
##		return valor.strftime("%d/%m/%Y %H:%M:%S")
		return valor.strftime("%H:%M:%S")

	# si es un date, devolver como string con formato dia/mes/anyo
	if isinstance(valor, datetime.date):
		return datetostr(valor)

	# si es un time, devolver como string con formato horas:minutos:segundos
	if isinstance(valor, datetime.time):
		return valor.strftime("%H:%M:%S")

	# si es un unicode, devolver tal cual
	if isinstance(valor, unicode):
		return valor

	# si no es un string, convertirlo a string
	if not isinstance(valor, str):
		return str(valor)


	# si es string convertirlo a unicode (latin_1 es el del idioma espanol)
##	#   convertir los #13#10 a #10
##	valor = valor.replace('\x0D\x0A', '\x0A')
	return unicode(valor, 'latin_1')


def formatea_valor_json(valor):

	"""
	Formatea un valor de un campo de una tabla del tipo que sea
	para asignarlo a un objeto para devolver como JSON
	"""

	# None, bools y unicodes, devolver tal cual
	if (valor is None) or isinstance(valor, bool) or isinstance(valor, unicode):
		return valor

	# Fehcas y horas
	# NOTA:	Tomamos como convención que los campos de tipo Date son fechas y los de
	#	   tipo DateTime son horas, aunque en BBDD se guarden ambos como DATETIME.
	#	   (esto se aplica para los valores de campos de sqlalchemy)

	# si es un datetime devolver como string con formato horas:minutos:segundos,
	# ya que convenimos que los datetime de sqlalchemy son horas.
	if isinstance(valor, datetime.datetime):
		return valor.strftime("%H:%M:%S")

	# si es un date, devolver como string con formato dia/mes/anyo
	if isinstance(valor, datetime.date):
		return datetostr(valor)

	# si es un time, devolver como string con formato horas:minutos:segundos
	if isinstance(valor, datetime.time):
		return valor.strftime("%H:%M:%S")
	# ###############

	# si no es un string, convertirlo a string
	if not isinstance(valor, str):
		return str(valor)

	# si es string convertirlo a unicode (latin_1 es el del idioma espanol)
	return unicode(valor, 'latin_1')


def isint(s):
	try:
		int(s)
		return True
	except Exception as e:
		return False

def isiter(o):
	try:
		iter(o)
		return True
	except TypeError as e:
		log.error(e)
		return False
	except Exception as e:
		log.error(e)
		raise

def try_int(v):
	"""
	intenta convertir a int, si no es posible devuelve None
	"""
	try:
		return int(v)
	except Exception as e:
		return None


def datetostr(d):
	if d.year < 1900:
		return d.replace(year=1900).strftime("%d/%m/") + str(d.year)
	else:
		return d.strftime("%d/%m/%Y")

def strtotime(s, d = None):
	"""
	convierte una hora en formato string HH:MM a un tipo DateTime, que es lo
	que se necesita para sql alchemy.
	(de momento solo lo usa rest/citas.py)

	d	parametro opcional, de tipo Date, de donde se extraerá
		la parte de fecha. Si no se indica, se extraerá el dia actual.
	"""
	if not d:
		d = datetime.date.today()
	t = time.strptime(s, "%H:%M")
	return datetime.datetime(d.year, d.month, d.day, t.tm_hour, t.tm_min)

def find(seq, fn, *args):
	"""
	Devuelve el primer item de la secuencia en que fn(item, *args) == True.
	el uso de *args permite pasar params adicionales a la funcion de test, aunque
	el primer parametro siempre será el item.
	Si no haya ninguno, devuelve None.
	"""
	for item in seq:
		if fn(item, *args): return item
	return None

def strday_to_numberday(strday):
	"""
	esta funcion devuelve el numero de dia a partir de una descripcion literal del dia de la semana
	lunes 0
	martes 1...
	"""
	#IDIOMA ???
	if strday == "lunes":
		return 0
	elif strday == "martes":
		return 1
	elif strday == "miercoles":
		return 2
	elif strday == "jueves":
		return 3
	elif strday == "viernes":
		return 4
	elif strday == "sabado":
		return 5
	elif strday == "domingo":
		return 6
	else:
		return None
### comprobacion de usuario "custom", para permitir solo un login simultaneo por usuario
### redefino la que hay en authkit.authenticate.valid_password (la asigno desde config.middleware)
##users_loggedin = []
##
##def valid_password(environ, username, password):
##	if username.lower() in users_loggedin:
##		return False
##	if not environ.has_key('authkit.users'):
##		raise no_authkit_users_in_environ
##	users = environ['authkit.users']
##	if not users.user_exists(username):
##		return False
##	elif users.user_has_password(username.lower(), password):
##		users_loggedin.append(username.lower())
##		return True
##	return False

def valid_date_range(d):
	"""
	Debido a que cada motor de bbdd tiene unos rangos válidos de fechas en los
	tipos DATE, EndoTools siempre limita al mas restrictivo, que es SQL Server,
	del 1/1/1753 al 1/1/9999.
	Los rangos de cada bbdd son:
		SQL Server	 1753 - 9999
		MySQL		 1000 - 9999
		Oracle		-4712 - 9990

	params:
		d   datetime.date o datetime.datetime
	"""
	if isinstance(d, datetime.datetime): d = d.date()
	return (d >= datetime.date(1753, 1, 1)) and (d <= datetime.date(9999, 1, 1))


def calcular_edad(fecha_nacimiento, dia_actual=None):
	"""
	calcula la edad (en anos) dada una fecha de nacimiento y el dia actual.
		fecha_nacimiento	datetime
		dia_actual			datetime	(si se omite se utiliza el dia de hoy)
	"""
	if not dia_actual:
		dia_actual = datetime.datetime.today()

	# restar directamente el ano y luego comprobar por dia y mes si ya ha cumplido el actual o no
	edad = dia_actual.year - fecha_nacimiento.year
	if dia_actual.month < fecha_nacimiento.month:
		edad = edad - 1
	elif dia_actual.month == fecha_nacimiento.month:
		if dia_actual.day < fecha_nacimiento.day:
			edad = edad - 1
	return edad


def jsonify(func, *args, **kwargs):
	"""
	basado en /pylons/decorators/__init__.py
	básicamente, solo cambia el content-type a uno mas compatible para jQuery
	"""
	pylons.response.headers['Content-Type'] = 'application/json'  # jQuery .ajax() funciona mejor con este MIME
	data = func(*args, **kwargs)
	return simplejson.dumps(data)
jsonify = decorator(jsonify)


class obj_to_csv_writer():

	def __init__(self):
		self.data = ''

	def write(self, x):
		self.data = self.data + x

def objeto_to_csv(data,lineterminator=None,opciones={}):

	#obtener todas las columnas posibles de un set de datos
	def completar_row_con_cols(row,cols_posibles):
		row_col_set = set(row.keys())
		diferencia = [key for key in cols_posibles if key not in row_col_set]
		for col in diferencia:
			row[col] = ""
		return row

	def procesar_dict_valores(data,row,cols_posibles,prefix=""):

		for k, v in data.iteritems():
			
			if isinstance(v, dict):
				#si es un diccionario entonces recursivamente recorre ese 
				#diccionario y los inserta en el mismo nivel que el padre
				#se envia un prefix que sirve para identificarlo y para 
				#evitar columnas repetidas
				row = procesar_dict_valores(v,row,cols_posibles,k)
			else:
				if isinstance(v, unicode):
					v = v.encode('latin_1')

				#crea el prefijo de la columna
				col_name = prefix
				if prefix!="":
					col_name = prefix+"__"+k
				else:
					col_name = k
				
				#inserta el valor en la fila
				row[col_name] = v
				
				# si el valor de la columna no existe en en cols_posibles
				# agregar valor a col_posibles si no existe
				if col_name not in cols_posibles:
					cols_posibles.append(col_name)
				
		return row	

	#import pdb
	# Excluir campos del resultado
	excluir = []
	if 'excluir' in opciones.keys():
		excluir = opciones["excluir"]

	# Cambiar los nombres de los headers
	headers = None
	if 'headers' in opciones.keys():
		headers = opciones["headers"]

	# contiene el orden en que estaran las columans
	order_columns = None
	if 'order_columns' in opciones.keys():
		order_columns = opciones["order_columns"]

	csvfile = obj_to_csv_writer()

	#si viene lineterminator se personaliza el cambio de linea del archivo csv
	if lineterminator==None:
		csvwriter = csv.writer(csvfile, delimiter=';', quotechar='"', quoting = csv.QUOTE_MINIMAL , escapechar = '\\')
	else:
		csvwriter = csv.writer(csvfile, delimiter=';', quotechar='"', quoting = csv.QUOTE_MINIMAL , lineterminator=lineterminator, escapechar = '\\')

	# almacena todas las columnas posibles que va a tener el archivo csv
	cols_posibles = []
	
	# Procesa los valores del diccionario para estandarizarlos y tambien
	# completa la informacion en cols_posibles
	rows = []
	for item in data:
		row = procesar_dict_valores(item, {}, cols_posibles,"")
		rows.append(row)
	
	# escribir titulos sirve para escribir el headers del archivo
	escribir_titulos = True
	keys_array = []
	
	#pdb.set_trace()
	for row in rows:
		#completa las columnas faltantes de las filas que tienen menos datos
		#para evitar el desfasamiento
		row = completar_row_con_cols(row,cols_posibles)
		
		# Escribe titulos/headers del archivo-
		# Se ejecuta solo una vez
		if escribir_titulos:
			escribir_titulos = False
			keys_array = row.keys()

			#excluye las columnas que no van a aparecer en el archivo
			for e in excluir:
				try:
					#pdb.set_trace()
					keys_array.remove(e)
				except Exception,err:
					log.error("errrrr: %s", err.message)
					pass

			# ordena las columans
			if order_columns:
				ordered_keys_array = []
				for oc in order_columns:
					#ordena como viene preestablecido 
					if oc in keys_array:
						ordered_keys_array.append(oc)
						keys_array.remove(oc)

					# las columnas que no se configuraron para ser ordenadas
					# las ordena por orden alfabetico
					keys_array = sorted(keys_array)
				keys_array = ordered_keys_array + keys_array
				log.debug(keys_array)


			# - Escribe los headers con sus nombres como se muestran en el endosys
			# - headers puede venir ordenado diferente, por eso se reacomoda el keys_array segun
			#   como venga ordenado el header
			if headers:
				headers_array = []
				for k in keys_array:
					if k in headers.keys():
						headers_array.append(headers[k])
					else:
						headers_array.append(k)
				csvwriter.writerow(headers_array)
			else: # no vienen headers
				csvwriter.writerow(keys_array)
			
		
		#crea un array con items vacios con la cantidad de columnas posibles
		values = [''] * len(row)
		
		# Carga los datos en values en la posicion correcta
		# segun donde esten en el keys_array
		for k,v in row.iteritems():
			
			try:
				index = keys_array.index(k)
				if v == None:
					v = ""
				values[index] = v
			except ValueError as e:
				#no hace nada pq no esta la clave
				log.error(e)

		csvwriter.writerow(values)
		
	return csvfile.data

#dejada por cuestiones de compatibilidad
#TODO: revisar la aplicacion para ver donde se usa y remplazar
def obj_to_csv(data,lineterminator=None):

	def procesar_dict_valores(data):
		row = []
		for k, v in data.iteritems():
			if isinstance(v, dict):
				row = row + procesar_dict_valores(v)
			else:
				if isinstance(v, unicode):
					v = v.encode('latin_1')
				row.append( v ) 
		return row

	def procesar_dict_titulos(data, ruta):
		titulos = []
		for k, v in data.iteritems():
			if isinstance(v, dict):
				titulos = titulos + procesar_dict_titulos(v, ruta + " " + k )
			else:
				titulos.append(ruta + " " + k)

		return titulos

	csvfile = obj_to_csv_writer()

	if lineterminator==None:
		csvwriter = csv.writer(csvfile, delimiter=';', quotechar='"', quoting = csv.QUOTE_MINIMAL , escapechar = '\\')
	else:
		csvwriter = csv.writer(csvfile, delimiter=';', quotechar='"', quoting = csv.QUOTE_MINIMAL , lineterminator=lineterminator, escapechar = '\\')

	if len(data) > 0:
		titulos = procesar_dict_titulos(data[0],"")
		csvwriter.writerow(titulos)
	
	for item in data:
		valores_row = procesar_dict_valores(item)
		csvwriter.writerow(valores_row)
	
	return csvfile.data




def obj_to_xml(data, member_name='item', collection_name='items', attrs=('id', 'href'), collection_member={}):

	"""
	Convierte un objeto en una representacion XML.
	El objeto 'data' tiene el mismo formato usado para "jsonificar"
	"""

	# XXX esta lista seria mejor centralizarla en algun sitio mas accesiblepara facilitar el mantenimiento.
	_collection_member = {
		'permisos': 'permiso',
		'servicios': 'servicio',
		'agendas': 'agenda',
		'medicos': 'medico',
		'salas': 'sala',
		'horas': 'hora',
		'formularios': 'formulario',
		'gruposCampos': 'grupoCampos',
		'valor': 'elemento',	# usado en los valores de un campo de un formulario, de tipo multiselect
        'centros': 'centro',
	}
	_collection_member.update(collection_member)

	def procesar_dict(data, parent):
		# recorrer los keys del dict
		for k, v in data.iteritems():
			if k in attrs:
				# es un atributo, se espera que sea un str
				if isinstance(v, (str, unicode)):
					parent.attrib[k] = v
				# aunque también acepta None
				elif isinstance(v, type(None)):
					parent.attrib[k] = ''
				# si no, error
				else:
					raise Exception(_('Tipo no valido'))#IDIOMAOK
			else:
				# si es una secuencia, rellenar con elementos
				if isinstance(v, (tuple, list)):
					p1 = SubElement(parent, k)
					for item in v:
						p2 = SubElement(p1, _collection_member.get(k, k + '_item')) # o hacer que de error si no esta en "collection_member", en lugar de asignar k + '_item'
						procesar_dict(item, p2)
				# si es un dict, es un solo elemento
				elif isinstance(v, dict):
					p1 = SubElement(parent, k)
					procesar_dict(v, p1)
				# si no, se espera que sea un str
				elif isinstance(v, (str, unicode)):
					SubElement(parent, k).text = v
				# podria ser un bool
				elif isinstance(v, bool):
					SubElement(parent, k).text = {True: '1', False: '0'}[v]
				# tambien podria ser None
				elif isinstance(v, type(None)):
					SubElement(parent, k)
				# si no, error
				else:
					raise Exception(_('Tipo no valido'))#IDIOMAOK

	# si es una secuencia, rellenar con elementos
	if isinstance(data, (tuple, list)):
		root = Element(collection_name)
		for item in data:
			p = SubElement(root, member_name)
			procesar_dict(item, p)
	# si es un dict, es ya un solo elemento
	elif isinstance(data, dict):
		root = Element(member_name)
		procesar_dict(data, root)
	else:
		raise Exception(_('"data" no es de un tipo valido'))#IDIOMAOK
	return root

def eliminar_archivo(ruta):
	try:
		os.remove(ruta)
		return True
	except Exception as e:
		log.error(e)
		return False


def cargar_layout_main(path_html="main_content.html"):
	
	response.content_type = "text/html"
	if path_html != "main_content.html":
		content = open(path_html).read()
	else:
		content = open(os.path.join(config['pylons.paths']['static_files'], 'webapp', 'content', path_html)).read()
		
	# Asignar el idioma
	content = content.replace('ENDOTOOLS:LANG', config.get('lang', 'es'))

	#asignar theme
	content = content.replace('ENDOTOOLS:THEME', config.get('THEME_ENDOTOOLS', 'classic').lower())

	# Asignar la Version
	try:
		version_file = os.path.join(config['pylons.paths']['root_parent'], 'version.txt')
		v_file = open(version_file, 'r')
		first_line = v_file.readline()
		content = content.replace('ENDOTOOLS:VERSION', first_line)
	except Exception as e:
		log.error(e)
		content = content.replace('ENDOTOOLS:VERSION', '')

	# Tags para firma electronica
	if config.get('FIRMA_ELECTRONICA.ACTIVO', '0') in ('1', '2'):
		if config.get('FIRMA_ELECTRONICA.TIPO') == '@firma' :
			content = content.replace('<!--ENDOTOOLS:FIRMA_ELECTRONICA-->',
				"""
				<script type="text/javascript" src="/cliente_firma/deployjava/deployJava-non-minified.js"></script>
				<script type="text/javascript" src="/cliente_firma/miniapplet-1.1u4/miniapplet.js"></script>
				<script type="text/javascript">
				//	cargar applet de firma electronica.
				//	XXX	seria mejor que el almacen de datos (aqui KEYSTORE_WINDOWS) se pueda configurar desde el INI
				MiniApplet.cargarMiniApplet('/cliente_firma/miniapplet-1.1u4', MiniApplet.KEYSTORE_WINDOWS);
				</script>
				<!--	El estilo display:none se pone después de cargar el applet, porque si no no se inicializa	-->
				<style>#deployJavaPlugin, #miniApplet { position:fixed; z-index:0; left:0; top: 0;}</style>
				"""
			)
		elif config.get('FIRMA_ELECTRONICA.TIPO') == 'viafirma' :
			content = content.replace('<!--ENDOTOOLS:FIRMA_ELECTRONICA-->',
				"""
					<script type="text/javascript" src="/cliente_firma/viafirma.pesado.js"></script>
				"""
			)

	return content


def obtener_request_ip(req):
	""" Obtiene la IP del cliente desde el encabezado
		 * Por defecto se usa el encabezado REMOTE_ADDR
		 * Si el servidor pylons esta configurado como proxy
		   del apache se debe usar el encabezado HTTP_X_FORWARDED_FOR. 
		   Para usar este encabezado se debe configurar desde el ini con
		   la clave IP_ENCABEZADO
	
		Parametros:
		 * req: es el objeto request del pylons

	"""
	ip_encabezado = config.get('IP_ENCABEZADO', 'REMOTE_ADDR')	
	ipaddress =	req.environ.get(ip_encabezado, None)
	return ipaddress

def get_extension(filename):
	return os.path.splitext(filename)[1].lower()[1:]

def conditional_authorize(permission):
	if config.get('PERMITIR_API_KEY', "0") == "0":
		return lambda x: x
	else:
		return authorize(permission)

def get_version_txt():
	version_file = os.path.join(config['pylons.paths']['root_parent'], 'version.txt')
	v_file = open(version_file, 'r')
	first_line = v_file.readline()
	return first_line.strip()

	
def update_version_number_db(s):
	# verifica si la fila de version en la tabla de configuraciones esta
	# creada y actualizada
	# ATENCION: EL COMMIT SE DEBE HACER AFUERA
	configuracion = s.query(Configuracion) \
					 .filter(Configuracion.clave=='version')
	if configuracion.count() != 0:
		configuracion = configuracion.first()
		configuracion.valor = get_version_txt()
		s.update(configuracion)
		s.flush()
	else:
		configuracion =Configuracion()
		configuracion.clave = 'version'
		configuracion.valor = get_version_txt()
		s.save(configuracion)
		s.flush()

def byteify(input):
	if isinstance(input, dict):
		return {byteify(key): byteify(value)
			for key, value in input.iteritems()}
	elif isinstance(input, list):
		return [byteify(element) for element in input]
	elif isinstance(input, unicode):
		return input.encode('utf-8')
	else:
		return input
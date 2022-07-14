"""
Controlador REST base para acceder a un recurso
directamente de BBDD (recurso -> tabla)

configurable:
	permisos para cada accion
	clase mapeada a tabla
	nombre tabla, campos
	campo id
"""

# USAR SOLO PARA MAPEAR EL CONTROLADOR AL MODELO DE DATOS
# XXX   controlar que el update y el create funcionen igual a la hora de formatear los valores, asignarlos, etc
# XXX   hay funcionalidad que podria ser comun a un controlador generico REST que no accediera a BBDD: dividir en 2 clases, GenericREST -> Generic_DB_REST

import logging
from pylons.i18n import _
from endotools.model import meta
from xml.etree.ElementTree import Element, SubElement, tostring

from endotools.lib.base import *

from authkit.authorize.pylons_adaptors import authorize
from authkit.permissions import RemoteUser, ValidAuthKitUser, UserIn, HasAuthKitRole, And

from endotools.lib.misc import *
from sqlalchemy.types import Integer, Date, Time, DateTime, Boolean, String
from sqlalchemy.sql import and_
from sqlalchemy.orm import class_mapper
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.exceptions import IntegrityError
from sqlalchemy import desc
from sqlalchemy import or_

from paste.util.multidict import MultiDict, UnicodeMultiDict
from pylons import config

import time
import datetime

import simplejson

import paginate
import sqlalchemy.databases.mssql as mssql
import sqlalchemy.databases.oracle as oracle
import sqlalchemy.databases.mysql as mysql
import threading
import gc

import uuid

log = logging.getLogger(__name__)

class GenericRESTController(BaseController):
	"""REST Controller styled on the Atom Publishing Protocol"""

	def __init__(self, *args, **kwargs):
		BaseController.__init__(self, *args, **kwargs)

		# configurar estos miembros en los descendientes
		self.tabla = None
		self.nombre_recurso = None
		self.nombre_recursos = None
		self.campos_index = None	# secuencia de strings con los nombres de los campos a mostrar al hacer un index
		self.campos_show = None		# secuencia de strings con los nombres de los campos a mostrar al hacer un show
		self.like_filter = ()	 # secuencia de strings con los nombres de los campos en los que se aplicara una comparacion del tipo "campo like valor%" en vez de la normal "campo = valor". O sea, campos de texto
		self.contains_filter = () # secuencia de strings con los nombres de los campos en los que se aplicara una comparacion del tipo "campo like %valor%" en vez de la normal "campo = valor". O sea, campos de texto
		self.campo_orderby = None   # se utiliza para ordenar los resultados por un campo
		self.campo_orderby_tipo = "ASC" #puede tener ASC o DESC
		self.index_vacio = False	# indica si permite hacer un index vacio. Si no se permite devolverá un 404, si se permite procede normal, devolviendo una lista vacia


	def _registro_by_id(self, id):
		reg = registro_by_id(self.tabla, id)
		if reg is None:
			abort(404, _('No se encuentra el registro con id: %s') % id)#IDIOMAOK
		else:
			return reg

	def _anadir_campo_xml(self, parent, registro, campo):
		sub = SubElement(parent, campo)
		# si el campo es una relacion a otro registro de otra tabla, incluir los campos de dicho registro
		if hasattr(getattr(registro, campo), '__dict__'):
			for c, v in vars(getattr(registro, campo)).iteritems():
				if c == 'id':
					sub.attrib[c] = formatea_valor( v )
				elif not(c.startswith('_')):
					SubElement(sub, c).text = formatea_valor( v )
		# si es realmente un campo de la tabla, asignar el valor
		else:
			sub.text = formatea_valor( getattr(registro, campo) )

	def _anadir_campo_obj(self, parent, registro, campo):
		#import pdb
		#pdb.set_trace()
		# si el campo es una relacion a otro registro de otra tabla, incluir los campos de dicho registro
		if hasattr(getattr(registro, campo), '__dict__'):
			parent[campo] = {}
			for c, v in vars(getattr(registro, campo)).iteritems():
				if c == 'id':
					parent[campo][c] = formatea_valor_json( v )
				elif not(c.startswith('_')):
					parent[campo][c] = formatea_valor_json( v )
		# si es realmente un campo de la tabla, asignar el valor
		else:
			parent[campo] = formatea_valor_json( getattr(registro, campo) )


	def _filtrar_index(self, query, format='html'):
		""" si es necesario implementar en descendientes """
		return query

	def _return_doIndex(self, registros, data, format=None):
		""" implementar en descendiente para modificar la info del obj """
		return data

	def _return_index_html(self, registros, format='html'):
		"""
		generar la página HTML con el index.
		Sustituir en descendientes para personalizar la página.
		"""
		mapped_table = class_mapper(self.tabla).mapped_table
		r = ''
		if registros is not None:
			for registro in registros:
				s = ''
				params = []
				for campo in mapped_table.c.keys():
					if campo in self.campos_index:
						s = ' '.join([s, '%s'])
						params.append( getattr(registro, campo) )
				s = '<a href="%s">%s</a>' %\
					(h.url_for('rest_' + self.nombre_recurso, id=registro.id, format=format), s.strip())
				r = r + (s % tuple(params))
		return r


	def respuesta_doIndex(self, registros, data, format='html'):
		response.headers['cache-control'] = "no-cache, no-store, must-revalidate"
		if format == 'html':
			# XXX no se utiliza el formato html por el momento
			response.content_type = "text/html"
			return self._return_index_html(registros, format)
		elif format == 'xml' or format == 'download':
			response.content_type = "text/xml"
			if format == 'download':
				response.headers.add('Content-Disposition', 'attachment;filename="%s.xml"' % self.nombre_recursos)
			return tostring(obj_to_xml(data, self.nombre_recurso, self.nombre_recursos))
		elif format == 'json':
			response.content_type = 'application/json'  # jQuery .ajax() funciona mejor con este MIME
			return simplejson.dumps(data)
		elif format == 'csv':
			response.content_type = 'text/csv'
			response.headers.add('Content-Disposition', 'attachment;filename="%s.csv"' % self.nombre_recursos)
			return obj_to_csv(data)


	def _doIndex(self, params, format='html'):
		# -- Para test
		#import random
		#import time
		#start = time.time()
		#randm = str(random.randrange(0, 101, 2))
		#print "in: "+randm
		#import pdb
		#pdb.set_trace()
		#log.info(">>> Index ("+randm+"): " + str(self.tabla))
		#log.info("params: " +str(params))
		# --

		""" hace una busqueda en la BBDD filtrando segun
		los params indicados y devuelve el resultado en el formato
		especificado (html o xml)
		""" 
		q = meta.Session.query(self.tabla)
		mapped_table = class_mapper(self.tabla).mapped_table

		#genera la lista de filtros pasados por parametros
		lista = self._genera_lista_filter(params)

		#Parametro de paginacion
		if '_pagina' in params:
			self._pagina = int(params['_pagina'])
		else:
			self._pagina = None

		#se aplican los filtros de la lista
		q = self._aplicar_filtros(q, lista, format)

		q = self._aplicar_orden(q)

		if '_limit' in params:
			if params['_limit'].isdigit():
				q = q.limit(int(params['_limit']))

		# si no se encuentra ningun registro, devolver error 404
		if not q.count() and not self.index_vacio:
			response.status_code = 404
			#-- Para test
			#log.info("<<< Index 404 ("+randm+"): " + str(self.tabla))
			return "error"

		#Realizar la paginacion
		#Los otros formatos no tienen que paginarse. Ejemplo: Exportar CSV
		if self._pagina != None and format=="json":

			#si la pagina no esta en el rango de paginas disponibles, devuelve un codigo de error
			if self._pagina < 1:
				response.status_code = 404
				return "error"

			cant_por_pagina = int(config.get('PAGINACION.CANTIDAD', 50))

			if isinstance(meta.engine.dialect, mssql.MSSQLDialect) or isinstance(meta.engine.dialect, oracle.OracleDialect):
				registros = paginate.Page(q.all(), items_per_page=cant_por_pagina, current_page=self._pagina, sqlalchemy_session=meta.Session)
			else: #isinstance(meta.engine.dialect, mysql.MySQLDialect):
				registros = paginate.Page(q, items_per_page=cant_por_pagina, current_page=self._pagina, sqlalchemy_session=meta.Session)
				#registros = registros.all()

			if self._pagina > registros.page_count:
				response.status_code = 404
				return "error"

			#Envia el codigo 206 que corresponde a partial content
			#Si se envia codigo 200 tambien funciona, pero este es el codigo correcto semanticamente
			response.status_code = 206
			#se agrega el header de content-range
			response.headers.add('Content-Range', str(registros.first_item)+'-'+str(registros.last_item)+'/'+str(registros.item_count))

		else:
			registros = q.all()

		#
		data = self._crear_data(registros, format, valid_fields=self.campos_index)

		data = self._return_doIndex(registros, data, format)
		# -- Para test
		#log.info("<<< Index 200 ("+randm+"): " + str(self.tabla))
		#end = time.time()
		#print "out: " + str(randm) + " - time: " + str(end - start)
		return self.respuesta_doIndex(registros, data, format)


	@authorize(RemoteUser())
	def index(self, format='html'):
		"""GET /rest_resources: All items in the collection."""
		# url_for('rest_resources')
		return self._doIndex(request.params, format)

	def _deleted(self, registro):
		""" implementar en descendiente para realizar alguna accion cuando se ha modificado registro """
		pass

	def _updated(self, registro):
		""" implementar en descendiente para realizar alguna accion cuando se ha modificado registro """
		pass

	def _created(self, registro):
		""" implementar en descendiente para realizar alguna accion cuando se ha creado el nuevo registro """
		pass

	def _return_doCreate(self, registro, data, format='xml'):
		""" implementar en descendiente para anadir mas info en el obj """
		return data

	def _doCreate(self, params, format='xml'):
		""" crear un nuevo registro. Se pasan como parametros los
		valores de los campos en un dict
		"""
		mapped_table = class_mapper(self.tabla).mapped_table
		nuevoRegistro = self.tabla()

		# XXX mejor utilizar self.tabla.__dict__, que es como lo hago en el index y el show
##		for campo in self.tabla.c.keys():
		for campo in mapped_table.c.keys():
			if campo == 'id': continue
			if campo in params:
				valor = params[campo]
				# interpretar cadena vacia como null
				log.debug(nuevoRegistro.c[campo].type)

				if valor == '':
					valor = None

				# 2.4.11.2: si es string lo unico que hago es quitar espacios del final
				elif isinstance(nuevoRegistro.c[campo].type, String):
					valor = valor.rstrip()

				#si el valor es '0' o '1' hay que convertirlo para que funcione
				elif isinstance(nuevoRegistro.c[campo].type, Boolean):
					 valor = bool(int(valor)) if valor else None

				# NOTA:	Tomamos como convención que los campos de tipo Date son fechas y los de
				#	   tipo DateTime son horas, aunque en BBDD se guarden ambos como DATETIME.
				#	   El tipo Time ya no se usa, porque no es compatible con Oracle.

				# si el campo es tipo fecha y el valor un string, convertir
				elif isinstance(mapped_table.c[campo].type, Date):
					try:
						t = time.strptime(valor, "%d/%m/%Y")
					except ValueError as e:
						log.error(e)
						abort(400, _('ERROR: el formato de la fecha es incorrecto'))#IDIOMAOK
					valor = datetime.date(t.tm_year, t.tm_mon, t.tm_mday)

				# si el campo es tipo hora y el valor un string, convertir
				# XXX no se usa...
				elif isinstance(mapped_table.c[campo].type, Time):
					try:
						# primero intenta formato HH:MM
						t = time.strptime(valor, "%H:%M")
					except ValueError as e:
						log.error(e)
						try:
							# ...y si falla prueba HH:MM:SS
							t = time.strptime(valor, "%H:%M:%S")
						except ValueError as e:
							log.error(e)
							# ...si vuelve a fallar, es que el formato es incorrecto
							abort(400, _('ERROR: el formato de la hora es incorrecto'))#IDIOMAOK
					valor = datetime.time(t.tm_hour, t.tm_min, t.tm_sec)

				# si el campo es tipo fechahora y el valor un string, convertir
				# por convención, serán horas, aunque aqui se tratan también fecha, fecha+hora, etc...
				elif isinstance(mapped_table.c[campo].type, DateTime):
					try:
						# primero intenta como una fecha
						t = time.strptime(valor, "%d/%m/%Y")
					except ValueError as e:
						log.error(e)
						try:
							# si falla prueba como una hora
							t = time.strptime(valor, "%H:%M")
						except ValueError as e:
							log.error(e)
							try:
								# si falla prueba como una hora con segundos
								t = time.strptime(valor, "%H:%M:%S")
							except ValueError as e:
								log.error(e)
								try:
									# si falla prueba como una fecha y hora
									t = time.strptime(valor, "%d/%m/%Y %H:%M")
								except ValueError as e:
									log.error(e)
									try:
										# ...y si falla prueba como una fecha y hora con segundos
										t = time.strptime(valor, "%d/%m/%Y %H:%M:%S")
									except ValueError as e:
										log.error(e)
										# ...si vuelve a fallar, es que el formato es incorrecto
										abort(400, _('ERROR: el formato de la hora es incorrecto'))#IDIOMAOK
					valor = datetime.datetime(t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec)

				setattr(nuevoRegistro, campo, valor)

		meta.Session.save(nuevoRegistro)

		# XXX controlar excepcion IntegrityError, lanzada cuando algun valor no puede ser nulo
		meta.Session.commit()

		self._created(nuevoRegistro)

		#   devolver como xml o json
		data = { 'id': formatea_valor_json(nuevoRegistro.id) }
		data = self._return_doCreate(nuevoRegistro, data)
		response.status_code = 201
		if format == 'xml':
			response.content_type = "text/xml"
			return tostring(obj_to_xml(data, self.nombre_recurso))
		elif format == 'json':
			response.content_type = 'application/json'
			return simplejson.dumps(data)


	@authorize(RemoteUser())
	def create(self, format='xml'):
		"""POST /rest_resources: Create a new item."""
		# url_for('rest_resources')
		# se hace esto porque hay descendientes que no estan preparados para recibir
		# el parametro format, y suponen que es xml
		if format == 'xml':
			return self._doCreate(request.params)
		else:
			return self._doCreate(request.params, format)


	def _update_registro_from_params(self, registro, params, exclude = []):
		""" actualiza el registro a partir de los params (obtenidos del request).
		si un parametro no existe como campo en la tabla, devuelve error
		"""
		mapped_table = class_mapper(self.tabla).mapped_table
		for campo, valor in params.iteritems():
			# omite los parametros que empiezan por _ , y tambien si hay algun parametro llamado "id"
			if campo.startswith('_'): continue
			if campo == 'id': continue
			# 2.4.10 Un Update nunca puede actualizar campos de borrado logico,
			#        si se quiere implementar la funcionalidad actualizacion del campo borrado
			#        tiene que hacerse desde el rest especifico
			if campo == 'borrado': continue
			if campo == 'borrado_motivo': continue

			# Omite los que son excluidos explicitamente
			if campo in exclude: continue

			if hasattr(registro, campo):
				# cadena vacia se interpreta como null
				if valor == '':
					valor = None

				# 2.4.11.2: si es string lo unico que hago es quitar espacios del final
				elif isinstance(mapped_table.c[campo].type, String):
					valor = valor.rstrip()

				# booleano ('0' o '1')
				elif isinstance(mapped_table.c[campo].type, Boolean):
					valor = bool(int(valor))

				# int
				elif isinstance(mapped_table.c[campo].type, Integer):
					valor = int(valor)

				# si el campo es tipo fecha, convertir
				elif isinstance(mapped_table.c[campo].type, Date):
					try:
						t = time.strptime(valor, "%d/%m/%Y")
					except ValueError as e:
						log.error(e)
						abort(400, _('ERROR: el formato de la fecha es incorrecto'))#IDIOMAOK
					valor = datetime.date(t.tm_year, t.tm_mon, t.tm_mday)

				# resto
				setattr(registro, campo, valor)
			else:
				abort(400, _('ERROR: no existe el campo "%s"') % campo)#IDIOMAOK

		meta.Session.update(registro)



	@authorize(RemoteUser())
	def update(self, id, exclude=[]):
		"""PUT /rest_resources/id: Update an existing item."""
		# Forms posted to this method should contain a hidden field:
		#	<input type="hidden" name="_method" value="PUT" />
		# Or using helpers:
		#	h.form(h.url_for('rest_resource', id=ID),
		#		   method='put')
		# url_for('rest_resource', id=ID)
		registro = self._registro_by_id(id)
		self._update_registro_from_params( registro, request.params, exclude )
		meta.Session.commit()
		self._updated(registro)

	@authorize(RemoteUser())
	def delete(self, id):
		"""DELETE /rest_resources/id: Delete an existing item."""
		# Forms posted to this method should contain a hidden field:
		#	<input type="hidden" name="_method" value="DELETE" />
		# Or using helpers:
		#	h.form(h.url_for('rest_resource', id=ID),
		#		   method='delete')
		# url_for('rest_resource', id=ID)
		registro = self._registro_by_id(id)
		meta.Session.delete( self._registro_by_id(id) )
		meta.Session.commit()
		self._deleted(registro) # XXX   probar bien... aun será valido "registro" si se acaba de eliminar???
##		try:
##			Session.commit()
##		except IntegrityError:
##			abort(403, "No se puede eliminar")


	def _construir_xml_show(self, registro, root):
		"""
		se mantiene para semicompatibilidad con los controllers que aun implementen
		esta funcion, pero la idea es terminar quitándola, y si se tiene que modificar
		la respuesta del show usar _return_show().
		"""
##		root.attrib['id'] = formatea_valor( registro.id )
##		for campo in self.tabla.__dict__:
##			if campo == 'id': continue
##			if isinstance(getattr(self.tabla, campo), InstrumentedAttribute):
##				self._anadir_campo_xml(root, registro, campo)
		pass

	def _return_show(self, registro, data):
		""" implementar en descendiente para modificar la info del obj """
		pass

	def respuesta_show(self, registro, data, format='html'):
		if format == 'html':
			# XXX no utilizado
			response.content_type = "text/html"
			s = ''
			params = []
##			for campo in self.tabla.c.keys():
			for campo in mapped_table.c.keys():
				s = ' '.join([s, '%s'])
				params.append( getattr(registro, campo) )
			s = '<p>%s</p>' % s.strip()
			return s % tuple(params)

		elif format == 'xml' or format == 'download':
			# el formato "download" es igual que "xml" pero fuerza la descarga del mismo
			response.content_type = "text/xml"
			if format == 'download':
				if 'id' in data:
					nombre_descarga = '{0}_{1}.xml'.format(self.nombre_recurso, data['id'])
				else:
					nombre_descarga = '{0}.xml'.format(self.nombre_recurso)
				response.headers.add('Content-Disposition', 'attachment;filename="%s"' % (nombre_descarga))

##			root = Element(self.nombre_recurso)
			root = obj_to_xml(data, self.nombre_recurso, self.nombre_recursos)
			self._construir_xml_show(registro, root)
			return tostring(root)

		elif format == 'json':
			response.content_type = 'application/json'
			return simplejson.dumps(data)


##	@authorize(RemoteUser())
	def show(self, id, format='html'):
		"""GET /rest_resources/id: Show a specific item."""
		# url_for('rest_resource', id=ID)

		# -- Para test
		#import random
		#randm = str(random.randrange(0, 101, 2))
		#log.info(">>> show ("+randm+"): " + str(self.tabla))
		#log.info("id: " +str(id))
		# --
		registro = self._registro_by_id(id)

		# construir el objeto data
		data = self._crear_data(registro, format, valid_fields=self.campos_show)
		# #########
		self._return_show(registro, data)

		#log.info("<<< show ("+randm+"): " + str(self.tabla))

		return self.respuesta_show(registro, data, format)



	# Genera una lista de filtros
	# -------------------------------------------
	# Esta lista se crea solamente si algun param
	# coincide con el nombre de un campo
	def _genera_lista_filter(self, params): # 10/3/2016: He quitado el param format porque no se usa y creo que no tiene sentido en esta función

		lista = []

		# 2.4.10 - si no viene el campo borrado, y existe en la tabla, entonces hace un filtro
		# 		   para que solo devuelva los campos no borrados - Esta es la funcionalidad por defecto -
		if hasattr(self.tabla, "borrado") and (not 'borrado' in params or ('borrado' in params and params["borrado"]!="1")):
			campo = getattr(self.tabla, "borrado")
			# se agrega None para que funcione con las BD anteriores a 2.4.10
			lista.append( or_(campo == 0, campo == None) )

		for param in params:

			# omitir parametros que empiezan por _
			if param.startswith('_'): continue

			campo = getattr(self.tabla, param)
			valor = params[param]

			if param in self.like_filter:
				lista.append( (campo.like(valor + '%')) )
			elif param in self.contains_filter:
				lista.append( (campo.like('%' + valor + '%')) )
			else:
				# si el valor es una cadena vacia, interpretar como null
				if valor == '': valor = None

				# si el campo es tipo fecha y el valor un string, convertir
				if isinstance(self.tabla.c[param].type, Date):
					try:
						t = time.strptime(valor, "%d/%m/%Y")
					except ValueError as e:
						log.error(e)
						abort(400, _('ERROR: el formato de la fecha es incorrecto'))#IDIOMAOK
					valor = datetime.date(t.tm_year, t.tm_mon, t.tm_mday)

				# si el campo es tipo boolean (bit) y el valor un string, intenta convertir "0" o "1" a numero
				if isinstance(self.tabla.c[param].type, Boolean):
					try:
						valor = int(valor)
					except Exception as e:
						log.error(e)

				lista.append( (campo == valor) )

		return lista


	def _aplicar_filtros(self, q, lista, format):

		if lista:
			q = q.filter( and_(*lista) )

		# filtro/s adicionales en descendientes
		q = self._filtrar_index(q, format)

		return q

	def _aplicar_orden(self, q):
		# aplicar order
		if self.campo_orderby:
			if self.campo_orderby_tipo == "DESC":
				q = q.order_by(desc(self.campo_orderby))
			else:
				q = q.order_by(self.campo_orderby)

		return q


	#
	def _crear_data(self, reg, format, valid_fields=None, id_column_name='id'):


		"""
		Convierte una lista de registros a un list de dicts, que luego se puede serializar como JSON.
		También admite un solo registro.

		Pueden ser registro de sqlalchemy o objetos Python con los mismos atributos exactamente que las columnas de BBDD.
		Este segundo caso es el usado por los plugins.

			reg             el registro o lista de registros
			format          formato de la petición: xml/html/json...
			valid_fields    lista de campos (str). si se indica, se limitará a estos campos. Si no, se incluyen todos los campos.
		"""
		if isinstance(reg, (list, tuple)):

			data = []
			for r in reg:
				o = self._crear_data(r, format, valid_fields)
				data.append(o)

		else:
			if isinstance(reg, dict):
				return reg

			data = {
				'id': formatea_valor_json(getattr(reg,id_column_name)),
				'href': h.url_for('rest_' + self.nombre_recurso, id=getattr(reg,id_column_name), format=format) # ANTES SOLO EN INDEX, NO SHOW
			}

			# si es registro de sqlalchemy mejor iterar los atributos de la clase, no de la instancia, para luego identificar cuales son campos
			# si no, se da por hecho que todos son campos (será un objeto de un plugin probablemente).
			if self.tabla and isinstance(reg, self.tabla):
				lista_campos = vars(self.tabla)
			else:
				lista_campos = vars(reg)

			for campo in lista_campos:
				# ...que esten en campos_index/campos_show/valid_fields, excluyendo siempre el id
				if valid_fields and not campo in valid_fields: continue
				if campo == id_column_name: continue

				# si es registro de sqlalchemy comprobar que sea un campo (InstrumentedAttribute), ya que tiene otros atributos que no interesan
				if (self.tabla and isinstance(reg, self.tabla)) and not isinstance(getattr(self.tabla, campo), InstrumentedAttribute): continue

				self._anadir_campo_obj(data, reg, campo)

		return data

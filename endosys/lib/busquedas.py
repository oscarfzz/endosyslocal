"""
clases y funciones para ejecutar búsquedas avanzadas

NOTAS:

TIPOS DE OPERACION DE CADA TIPO DE CAMPO:

	SELECCION
		igual
		distinto
	MULTISELECCION
		contenga
	NUMERO
		entre
	TEXTO/MEMO
		igual
		distinto
		contenga
	BOOLEAN
		"igual"

FORMATO DEL 'valor' DE CADA TIPO DE CAMPO:

	SELECCION
		valor.id (int)
		valor.descripcion (str)
	MULTISELECCION
		valor.id (int)
		valor.descripcion (str)
	NUMERO
		valor (int)
	TEXTO/MEMO
		valor (str)
	BOOLEAN
		valor (bool)

CAMPOS DE PACIENTE:
	SEXO:
		llega M o H en la búsqueda XML. Está almacenado como 0 o 1 en la tabla,
		respectivamente.

IMPORTANTE XXX:

	Las exploraciones que no tengan algunos registros en las tablas de valores
	(suele pasar cuando se añaden nuevos campos existiendo ya exploraciones) pueden
	quedar excluidas de algunas búsquedas. Por ejemplo, en los campos de tipo
	selección, cuando se busca "distinto de", solo se devuelven las exploraciones
	que tienen un registro asignado, distinto del indicado.
	Por lo tanto, habría que ir con cuidado cuando se añaden nuevos campos, y
	crear todos los registros que falten en las tablas de valores.

	!!! -> está solucionado

"""

import types
import logging
import time
import datetime

from pylons.i18n import _
from sqlalchemy.sql import or_, and_, not_
from xml.etree.ElementTree import Element, SubElement, tostring, XML
# Documentación de ElementTree:
# 	http://docs.python.org/library/xml.etree.elementtree.html

from endosys.model.exploraciones import Exploracion, Rel_Formularios_Exploraciones
from endosys.model.pacientes import Paciente
from endosys.model.formularios import Formulario
from endosys.model.campos import Campo
from endosys.model.medicos import Medico
from endosys.model.servicios import Servicio
from endosys.model.aseguradoras import Aseguradora
from endosys.model.tiposExploracion import TipoExploracion
import endosys.model.busquedas
from endosys.model.valores import ValorTexto, ValorSelec, ValorMulti, ValorBool
from endosys.lib.misc import formatea_valor, record, isint, isiter, registro_by_id
import endosys.lib.elementos

log = logging.getLogger(__name__)

TIPO_TEXTO = 1
TIPO_SELEC = 2
TIPO_MULTI = 3
TIPO_BOOL = 4
TIPO_MEMO = 5
TIPO_SEPARADOR = 6
TIPO_NUMERO = 7	# no implementado en campos de formularios
TIPO_FECHA = 8	# no implementado en campos de formularios

CONJUNTO_PACIENTE = 		'PACIENTE'
CONJUNTO_EXPLORACION = 		'EXPLORACION'

BOOL_SI =                   'SI'
BOOL_NO =                   'NO'

CAMPO_ID_SEXO = 			'SEXO'
CAMPO_ID_POBLACION = 		'POBLACION'
CAMPO_ID_PROVINCIA = 		'PROVINCIA'
CAMPO_ID_ASEGURADORA = 		'ASEGURADORA'
CAMPO_ID_FECHA_EXPL =		'FECHA'
CAMPO_ID_MEDICO =			'MEDICO'
CAMPO_ID_TIPO_EXPL =		'TIPOEXPLORACION'
CAMPO_ID_TIENE_IMAGENES =	'TIENE_IMAGENES'
CAMPO_ID_SERVICIO = 		'SERVICIO'
CAMPO_ID_EDAD_PACIENTE = 	'EDAD_PACIENTE'
CAMPO_ID_ASEGURADORAS_ID = 	'ASEGURADORA_ID'

# 1..N valores (excepto OPERACION_IGUAL en tipo BOOL, solo 1 valor)
OPERACION_IGUAL = 			'IGUAL'             # campos tipo: 	texto	selec            numero   fecha   bool
OPERACION_DISTINTO =		'DIFERENTE'         # campos tipo: 	texto	selec            numero   fecha
OPERACION_CONTIENE =		'IN'        		# campos tipo: 	texto			multi
OPERACION_CONTIENE_TODOS =	'EN'        		# campos tipo:                  multi
OPERACION_NO_CONTIENE =		'NOT_IN'       		# campos tipo: 	texto			(multi)

# solo 1 valor
OPERACION_MENOR = 			'MENOR'             # campos tipo:                           numero   fecha
OPERACION_MAYOR = 			'MAYOR'             # campos tipo:                           numero   fecha
OPERACION_MENORIGUAL = 		'MENORIGUAL'        # campos tipo:                           numero   fecha
OPERACION_MAYORIGUAL = 		'MAYORIGUAL'        # campos tipo:                           numero   fecha

# solo 2 valores (min y max)
OPERACION_ENTRE = 			'ENTRE'             # campos tipo:                           numero   fecha
OPERACION_NO_ENTRE = 		'NOENTRE'           # campos tipo:                           numero   fecha

##CLASES_CAMPOBUSQUEDAFIJOS = {
##    CAMPO_ID_SEXO: CampoBusquedaFijoSexo,
##    CAMPO_ID_EDAD: CampoBusquedaFijoEdad
##}
##
# XXX	esto creo que es en común con el controller de CamposFijos...
conjuntos = {

	'PACIENTE': record(
		descripcion = _(u'Datos del paciente'),#IDIOMAOK
		campos = {
			CAMPO_ID_SEXO: record(
				nombre = u'sexo',
				titulo = _(u'Género:Sexo'),#IDIOMAOK
				tipo = TIPO_SELEC,
				valores = {
					1: _('Sexo:Hombre'),#IDIOMAOK
					0: _('Sexo:Mujer')#IDIOMAOK
				}
			),
			CAMPO_ID_POBLACION: record(
				nombre = u'poblacion',
				titulo = _(u'Paciente:Población'),#IDIOMAOK
				tipo = TIPO_TEXTO
			),
			CAMPO_ID_PROVINCIA: record(
				nombre = u'provincia',
				titulo = _(u'Paciente:Provincia'),#IDIOMAOK
				tipo = TIPO_TEXTO
			),
			CAMPO_ID_ASEGURADORA: record(
				nombre = u'aseguradora',
				titulo = _(u'Aseguradora'),#IDIOMAOK
				tipo = TIPO_SELEC
			)
		}
	),

	'EXPLORACION': record(
		descripcion = (u'Datos de la exploración'),#IDIOMAOK
		campos = {
			CAMPO_ID_FECHA_EXPL: record(
				nombre = u'fecha',
				titulo = _(u'Fecha exploración'),#IDIOMAOK
				tipo = TIPO_FECHA
			),
			CAMPO_ID_MEDICO: record(
				nombre = u'medico',
				titulo = _(u'Médico'),#IDIOMAOK
				tipo = TIPO_SELEC
			),
			CAMPO_ID_TIPO_EXPL: record(
				nombre = u'tipoexploracion',
				titulo = _(u'Tipo exploración'),#IDIOMAOK
				tipo = TIPO_SELEC
			),
			CAMPO_ID_TIENE_IMAGENES: record(
				nombre = u'imagenes',
				titulo = _(u'Tiene imágenes'),#IDIOMAOK
				tipo = TIPO_BOOL
			),
            CAMPO_ID_SERVICIO: record(
				nombre = u'servicio',
				titulo = _(u'Servicio'),#IDIOMAOK
				tipo = TIPO_SELEC
			),
            CAMPO_ID_EDAD_PACIENTE: record(
				nombre = u'edad_paciente',
				titulo = _(u'Edad paciente'),#IDIOMAOK
				tipo = TIPO_NUMERO
			),
            CAMPO_ID_ASEGURADORAS_ID: record(
			    nombre = u'aseguradora_id',
				titulo = _(u'Aseguradora'),#IDIOMAOK
				tipo = TIPO_SELEC
			)
		}
	)
}


class CampoBusqueda(object):
	"""
	No crearlo directamente, utilizar Busqueda.addCampo()

	Segun el tipo de campo, cada elemento de "valores" puede ser
	directamente el valor o	un objeto con estos campos:

		valor.id
		valor.descripcion

	"""
	def __init__(self, busqueda):
		self.busqueda = busqueda
		self.id = None
		self.operacion = None
		self.nombre = None
		self.tipo = None
		self.tipo_control = None
		self.titulo = None
		self.conjunto = record()
		self.conjunto.id = None
		self.conjunto.descripcion = None
		self.valores = []

	def ejecutar(self, query):
		# metodo "abstracto" a implementar en descendientes
		return query

	@staticmethod
	def valor_from_xml(e):
		"""
		convierte el valor extraido del xml al valor usado en el objeto Busqueda
		"e" es el elemento XML
		"""
		return e.text

	@staticmethod
	def valor_to_xml(valor, e):
		"""
		convierte el valor usado en el objeto Busqueda al valor necesario para el xml
		"valor" es el valor guardado en el objeto
		"e" es el elemento XML que se ha de rellenar con el valor
		"""
		e.text = formatea_valor(valor)


class CampoBusquedaTexto(CampoBusqueda):
	"""
	Clase base para campos de tipo texto, sean fijos o de form
	(valor_from_xml() y valor_to_xml() heredados de CampoBusqueda)
	"""
	def _condiciones_tipo_texto(self, field):
		"""
		este método lo comparten todos los campos de tipo de texto, ya sean fijos
		o de form, para aplicar las condiciones según cada tipo de operación
		"""
		if self.operacion == OPERACION_CONTIENE:
			condicion = or_(*list( field.contains(v) for v in self.valores )) # contains() es lo mismo que un like('%...%')
		elif self.operacion == OPERACION_NO_CONTIENE:
			condicion = and_(*list( not_(field.contains(v)) for v in self.valores ))
		elif self.operacion == OPERACION_IGUAL:
			condicion = or_(*list( field.like(v) for v in self.valores ))
		elif self.operacion == OPERACION_DISTINTO:
			condicion = and_(*list( not_(field.like(v)) for v in self.valores ))
		else:
			condicion = None # deberia ser una de estas 4
		return condicion


class CampoBusquedaNumero(CampoBusqueda):
	"""
	Clase base para campos de tipo numérico, sean fijos o de form.
	De momento, sólo "edad" (campo fijo de paciente).
	"""
	@staticmethod
	def valor_from_xml(e):
		"""
		El valor debe ser un numero
		"""
		return int(e.text)

	def _condiciones_tipo_numerico(self, field):
		"""
		este método lo comparten todos los campos de tipo de numérico, ya sean fijos
		o de form, para aplicar las condiciones según cada tipo de operación
		"""
		if self.operacion == OPERACION_IGUAL:
			condicion = or_(*list( (field == v) for v in self.valores ))
		elif self.operacion == OPERACION_DISTINTO:
			condicion = and_(*list( not_(field == v) for v in self.valores ))
		# <, <=, > y >= solo pueden tener un valor!
		elif self.operacion == OPERACION_MENOR:
			condicion = (field < self.valores[0])
		elif self.operacion == OPERACION_MENORIGUAL:
			condicion = (field <= self.valores[0])
		elif self.operacion == OPERACION_MAYOR:
			condicion = (field > self.valores[0])
		elif self.operacion == OPERACION_MAYORIGUAL:
			condicion = (field >= self.valores[0])
		# "entre" y "no entre" tienen siempre 2 valores
		elif self.operacion == OPERACION_ENTRE:
			condicion = and_(field >= self.valores[0], field <= self.valores[1])
		elif self.operacion == OPERACION_NO_ENTRE:
			condicion = or_(field < self.valores[0], field > self.valores[1])
		else:
			condicion = None # deberia ser una de las anteriores
		return condicion


class CampoBusquedaFecha(CampoBusquedaNumero):
	"""
	Clase base para campos de tipo fecha, sean fijos o de form.
	De momento, sólo "fecha expl." (campo fijo de exploracion).
	Hereda el mismo funcionamiento que CampoBusquedaNumero, ya que las posibles
	operaciones son las mismas.
	"""
	@staticmethod
	def valor_from_xml(e):
		"""
		El valor debe ser una fecha con el formato d/m/yyyy
		"""
		t = time.strptime(e.text, "%d/%m/%Y")
		d = datetime.date(t.tm_year, t.tm_mon, t.tm_mday)
		return d


class CampoBusquedaSelec(CampoBusqueda):
	"""
	Clase base para campos de tipo selec, sean fijos o de form
	"""
	def _condiciones_tipo_selec(self, field):
		"""
		este método lo comparten todos los campos de tipo de selec, ya sean fijos
		o de form, para aplicar las condiciones según cada tipo de operación
		"""
		if self.operacion == OPERACION_IGUAL:
			condicion = or_(*list( (field == v.id) for v in self.valores ))
		elif self.operacion == OPERACION_DISTINTO:
			condicion = and_(*list( not_(field == v.id) for v in self.valores ))
		else:
			condicion = None # deberia ser una de estas 2
		return condicion

	@staticmethod
	def valor_from_xml(e):
		valor = record()
		valor.id = e.find('id').text.upper()
		valor.descripcion = endosys.lib.elementos.get_by_id(valor.id).nombre
		if e.find('cantidad') is not None:
			valor.cantidad = e.find('cantidad').text
		if e.find('oper') is not None:
			valor.oper = e.find('oper').text
		return valor

	@staticmethod
	def valor_to_xml(valor, e):
		SubElement(e, 'id').text = formatea_valor(valor.id)
		SubElement(e, 'descripcion').text = formatea_valor(valor.descripcion)
		if getattr(valor, "cantidad", None) is not None:
			SubElement(e, 'cantidad').text = formatea_valor(valor.cantidad)
		if getattr(valor, "oper", None) is not None:
			SubElement(e, 'oper').text = formatea_valor(valor.oper)


class CampoBusquedaBool(CampoBusqueda):
	"""
	Clase base para campos de tipo bool, sean fijos o de form.
	"""
	def _condiciones_tipo_bool(self, field):
		"""
		este método lo comparten todos los campos de tipo de bool, ya sean fijos
		o de form, para aplicar las condiciones según cada tipo de operación
		"""
		if self.operacion == OPERACION_IGUAL:
			condicion = (field == self.valores[0])
			#if not self.valores[0]: incluir_sin_valor = True # en los casos en los que no hay valor, los trato como NO/FALSE
		else:
			condicion = None # deberia ser solo la operacion IGUAL
		return condicion

	@staticmethod
	def valor_from_xml(e):
		return {BOOL_SI: True, BOOL_NO: False}.get(e.text.upper(), None)

	@staticmethod
	def valor_to_xml(valor, e):
		e.text = BOOL_SI if valor else BOOL_NO


class CampoBusquedaFijoSexo(CampoBusquedaSelec):
	"""
	Campo fijo, sexo del paciente (Selec)
	"""
	def ejecutar(self, query):
		condicion = self._condiciones_tipo_selec(Paciente.sexo)
		filtro = Exploracion.paciente.has( condicion )
		log.debug('%s %s', filtro, self.valores)
		return query.filter(filtro)

	@staticmethod
	def valor_from_xml(e):
		valor = record()
##		valor.id = {'M': 0, 'H': 1}.get(e.text.upper())
		valor.id = {'M': 0, 'H': 1}.get(e.find('id').text.upper())
		valor.descripcion = conjuntos[CONJUNTO_PACIENTE].campos[CAMPO_ID_SEXO].valores[valor.id]
		return valor

	@staticmethod
	def valor_to_xml(valor, e):
##		e.text = {0: 'M', 1: 'H'}.get(valor.id)
		SubElement(e, 'id').text = {0: 'M', 1: 'H'}.get(valor.id)
		SubElement(e, 'descripcion').text = formatea_valor(valor.descripcion)




class CampoBusquedaFijoPoblacion(CampoBusquedaTexto):
	"""
	Campo fijo, población del paciente (Texto)
	"""
	def ejecutar(self, query):
		condicion = self._condiciones_tipo_texto(Paciente.poblacion)
		filtro = Exploracion.paciente.has( condicion )
		#print filtro, self.valores
		return query.filter(filtro)

##		condicion = self._condiciones_tipo_selec(Paciente.sexo)
##		filtro = Exploracion.paciente.has( condicion )
##		return query.filter(filtro)


class CampoBusquedaFijoProvincia(CampoBusquedaTexto):
	"""
	Campo fijo, provincia del paciente (Texto)
	"""
	def ejecutar(self, query):
		condicion = self._condiciones_tipo_texto(Paciente.provincia)
		filtro = Exploracion.paciente.has( condicion )
		return query.filter(filtro)

class CampoBusquedaFijoAseguradora(CampoBusquedaSelec):
	"""
	Campo fijo, aseguradora del paciente (Selec)
	"""
	def ejecutar(self, query):
		condicion = self._condiciones_tipo_selec(Paciente.aseguradora_id)
		filtro = Exploracion.paciente.has( condicion )
		return query.filter(filtro)

class CampoBusquedaFijoFechaExpl(CampoBusquedaFecha):
	"""
	Campo fijo, fecha de la exploración (Fecha)
	"""
	def ejecutar(self, query):
		condicion = self._condiciones_tipo_numerico(Exploracion.fecha)
		filtro = condicion
		log.debug('%s %s', filtro, self.valores)
		return query.filter(filtro)

class CampoBusquedaFijoMedico(CampoBusquedaSelec):
	"""
	Campo fijo, médico que realiza la exploración (Selec)
	"""
	@staticmethod
	def valor_from_xml(e):
		valor = record()
		valor.id = e.find('id').text.upper()
		valor.descripcion = registro_by_id(Medico, valor.id).nombre
		return valor

	def ejecutar(self, query):
		condicion = self._condiciones_tipo_selec(Exploracion.medico_id)
		filtro = condicion
		return query.filter(filtro)

class CampoBusquedaFijoTipoExpl(CampoBusquedaSelec):
	"""
	Campo fijo, tipo de la exploración (Selec)
	"""
	@staticmethod
	def valor_from_xml(e):
		valor = record()
		valor.id = e.find('id').text.upper()
		valor.descripcion = registro_by_id(TipoExploracion, valor.id).nombre
		return valor

	def ejecutar(self, query):
		condicion = self._condiciones_tipo_selec(Exploracion.tipoExploracion_id)
		filtro = condicion
		return query.filter(filtro)

class CampoBusquedaFijoTieneImagenes(CampoBusquedaBool):
	"""
	Campo fijo, indica si la exploración tiene imágenes (Bool)
	"""
	def ejecutar(self, query):
		if (self.operacion == OPERACION_IGUAL) and (self.valores[0]):
			filtro = Exploracion.capturas.any()
		else:
			filtro = not_(Exploracion.capturas.any())
		log.debug('%s %s', filtro, self.valores)
		return query.filter(filtro)


class CampoBusquedaFijoServicio(CampoBusquedaSelec):
	"""
	Campo fijo, tipo de la exploración (Selec)
	"""
	@staticmethod
	def valor_from_xml(e):
		valor = record()
		valor.id = e.find('id').text.upper()
		valor.descripcion = registro_by_id(Servicio, valor.id).nombre
		return valor

	def ejecutar(self, query):
		condicion = self._condiciones_tipo_selec(Exploracion.servicio_id)
		filtro = condicion
		return query.filter(filtro)

class CampoBusquedaFijoAseguradoraId(CampoBusquedaSelec):
	"""
	Campo fijo, aseguradora asignada a la exploración(Selec)
	"""
	@staticmethod
	def valor_from_xml(e):
		valor = record()
		valor.id = e.find('id').text.upper()
		valor.descripcion = registro_by_id(Aseguradora, valor.id).nombre
		return valor

	def ejecutar(self, query):
		condicion = self._condiciones_tipo_selec(Exploracion.aseguradora_id)
		filtro = condicion
		return query.filter(filtro)

class CampoBusquedaFijoEdadPaciente(CampoBusquedaNumero):
	"""
	Campo fijo, edad del paciente (Numero) en exploracion
	"""
	def ejecutar(self, query):
		condicion = self._condiciones_tipo_numerico(Exploracion.edad_paciente)
		filtro = condicion
		return query.filter(filtro)

class CampoBusquedaFormTexto(CampoBusquedaTexto):
	"""
	Un campo que no es fijo, sino que es de un formulario, de tipo texto
	"""
	def ejecutar(self, query):
		condicion = self._condiciones_tipo_texto(ValorTexto.valor)

		filtro = Exploracion.valoresTexto.any(
					and_(
						( ValorTexto.campo_id == self.id ),
						condicion
					)
				)

		if self.operacion == OPERACION_DISTINTO:
			# esto soluciona el problema en los casos de las exploraciones
			# que no tienen registros para algunos campos en alguna tabla de valores
			filtro = or_( (Exploracion.valoresTexto == None), filtro)

		return query.filter(filtro)


class CampoBusquedaFormSelec(CampoBusquedaSelec):
	"""
	Un campo que no es fijo, sino que es de un formulario, de tipo selección
	"""
	def ejecutar(self, query):
		condicion = self._condiciones_tipo_selec(ValorSelec.elemento_id)

		filtro = Exploracion.valoresSelec.any(
					and_(
						( ValorSelec.campo_id == self.id ),
						condicion
					)
				)

		if self.operacion == OPERACION_DISTINTO:
			filtro = or_( (Exploracion.valoresSelec == None), filtro)

		return query.filter(filtro)


class CampoBusquedaFormMulti(CampoBusquedaSelec):
	"""
	Un campo que no es fijo, sino que es de un formulario, de tipo selección múltiple
	De momento no hace falta definir una clase base CampoBusquedaMulti, ya que solo
	hay los de form, y comparte valor_from_xml() y valor_to_xml() con los de selec
	"""
	def _condiciones_tipo_multicantidad(self, field):
		if field.oper == "MAYOR":
			condicion = (ValorMulti.cantidad > field.cantidad)
		elif field.oper == "MAYORIGUAL":
			condicion = (ValorMulti.cantidad >= field.cantidad)
		elif field.oper == "MENORIGUAL":
			condicion = (ValorMulti.cantidad <= field.cantidad)
		elif field.oper == "MENOR":
			condicion = (ValorMulti.cantidad < field.cantidad)
		else:
			condicion = (ValorMulti.cantidad == field.cantidad)
		return condicion

	def _incluye_el_cero(self, field):
		if field.oper == "MAYORIGUAL" and field.cantidad <= 0:
			return True
		elif field.oper == "MENORIGUAL" and field.cantidad >= 0:
			return True
		elif field.oper == "MENOR" and field.cantidad > 0:
			return True
		elif field.oper == "IGUAL" and field.cantidad == 0:
			return True
		else:
			return False


	def ejecutar(self, query):
		
		if self.operacion == OPERACION_CONTIENE:
			lista = []
			for v in self.valores:
				if getattr(v, "cantidad", None) is not None and int(v.cantidad) >= 0:
					condicion = self._condiciones_tipo_multicantidad(v)
					lista.append(and_(ValorMulti.elemento_id == v.id,
										  condicion))
				else:
					lista.append((ValorMulti.elemento_id == v.id))
			condicion = or_(*list(lista))
			filtro = Exploracion.valoresMulti.any(
						condicion
					)

		elif self.operacion == OPERACION_CONTIENE_TODOS:
			lista = []
			for v in self.valores:
				if getattr(v, "cantidad", None) is not None and int(v.cantidad) >= 0:
					condicion = self._condiciones_tipo_multicantidad(v)
					lista.append(
						Exploracion.valoresMulti.any(
							and_(
								( ValorMulti.campo_id == self.id ),
								( ValorMulti.elemento_id == v.id ),
								condicion
							)
						)
					)
				else:
					lista.append(
						Exploracion.valoresMulti.any(
							and_(
								(ValorMulti.campo_id == self.id),
								(ValorMulti.elemento_id == v.id)
							)
						)
					)
			filtro = and_(*lista)

		else:
			filtro = None # deberia ser una de estas 2

		#print self.operacion, filtro, self.valores
		return query.filter(filtro)

	"""
	# ESTE CODIGO FUNCIONA MAL, presente en las versiones 2.4.10 a 2.4.11.1 inclusive
	# Es para que las busquedas avanzadas tengas busqueda por cantidades
	@staticmethod
	def valor_from_xml(e):
		valor = record()
		valor.id = e.find('id').text.upper()
		valor.descripcion = endosys.lib.elementos.get_by_id(valor.id).nombre
		
		# Estructura ejemplo
		# valores
		#   valor 										// del multiselect
		#		id    									// ejemplo: material
		#		operacion = MENOR, ENTRE, IGUAL, ETC
		#		valores
		#			valor 								/// de las cantidades ej: 1

		# extraccion de cantidades
		cantidades = e.find('valores')
		if not cantidades:
			valor.operacion = OPERACION_IGUAL
			valor.valores = [1,1]
			print "sin cantidades"
		else:
			valor.operacion = e.find("operacion").text.upper()
			valor.valores = []
			for cantidad in cantidades.findall('valor'):
				valor.valores.append(cantidad.text.upper())	

			print "con cantidades"

		return valor

	@staticmethod
	def valor_to_xml(valor, e):
		SubElement(e, 'id').text = formatea_valor(valor.id)
		SubElement(e, 'descripcion').text = formatea_valor(valor.descripcion)
		
		#agrega los valores de las cantidades
		SubElement(e, 'operacion').text = formatea_valor(valor.operacion)
		valores_xml = SubElement(e, 'valores')
		for valor in valor.valores:
			valor_xml = SubElement(valores_xml, 'valor')
			valor_xml.text = formatea_valor(valor)


	def _condiciones_tipo_numerico(self, field):
		
		#este método lo comparten todos los campos de tipo de numérico, ya sean fijos
		#o de form, para aplicar las condiciones según cada tipo de operación
		if self.operacion == OPERACION_IGUAL:
			condicion = or_(*list( (field == v) for v in self.valores ))
		elif self.operacion == OPERACION_DISTINTO:
			condicion = and_(*list( not_(field == v) for v in self.valores ))
		# <, <=, > y >= solo pueden tener un valor!
		elif self.operacion == OPERACION_MENOR:
			condicion = (field < self.valores[0])
		elif self.operacion == OPERACION_MENORIGUAL:
			condicion = (field <= self.valores[0])
		elif self.operacion == OPERACION_MAYOR:
			condicion = (field > self.valores[0])
		elif self.operacion == OPERACION_MAYORIGUAL:
			condicion = (field >= self.valores[0])
		# "entre" y "no entre" tienen siempre 2 valores
		elif self.operacion == OPERACION_ENTRE:
			condicion = and_(field >= self.valores[0], field <= self.valores[1])
		elif self.operacion == OPERACION_NO_ENTRE:
			condicion = or_(field < self.valores[0], field > self.valores[1])
		else:
			condicion = None # deberia ser una de las anteriores
		return condicion

	def ejecutar(self, query):

		if self.operacion == OPERACION_CONTIENE:

			# crea las condiciones para cada item del multiselect con el filtro de cantidades
			condiciones_cantidad = []
			for v in self.valores:
				
				field_cantidad = record()
				field_cantidad.valores = v.valores
				field_cantidad.operacion = v.operacion
				condicion_cantidad = and_(
											( ValorMulti.elemento_id == v.id),
											( self._condiciones_tipo_numerico(field_cantidad) )
										)
				condiciones_cantidad.append(condicion_cantidad)

			# agrupa todas esas condificiones en un OR
			condicion = or_(*list( cond for cond in condiciones_cantidad ))

			# Agrupa todas las condificiones en el AND global
			filtro = Exploracion.valoresMulti.any(
						and_(
							( ValorMulti.campo_id == self.id ),
							condicion
						)
					)

		# XXX Falta hacer
		elif self.operacion == OPERACION_CONTIENE_TODOS:
			lista = []
			for v in self.valores:
				lista.append(
					Exploracion.valoresMulti.any(
							and_(
								( ValorMulti.campo_id == self.id ),
								( ValorMulti.elemento_id == v.id )
							)
					)
				)
			filtro = and_(*lista)

		else:
			filtro = None # deberia ser una de estas 2

		print self.operacion, filtro, self.valores
		return query.filter(filtro)
	"""


class CampoBusquedaFormBool(CampoBusquedaBool):
	"""
	Un campo que no es fijo, sino que es de un formulario, de tipo boolean
	"""
	def ejecutar(self, query):
		condicion = self._condiciones_tipo_bool(ValorBool.valor)
		filtro = Exploracion.valoresBool.any(
					and_(
						( ValorBool.campo_id == self.id ),
						condicion
					)
				)

		# en los casos en los que no hay valor, los trata como NO/FALSE
		incluir_sin_valor = (self.operacion == OPERACION_IGUAL) and	(not self.valores[0])
		if incluir_sin_valor:
			filtro = or_( (Exploracion.valoresBool == None), filtro)

		log.debug('%s %s', filtro, self.valores)
		return query.filter(filtro)

##		# siempre tendrá un solo valor (SI o NO), y la operación siempre es IGUAL
##		condicion = None
##		incluir_sin_valor = False
##		if self.operacion == OPERACION_IGUAL:
##			condicion = (ValorBool.valor == self.valores[0])
##			if not self.valores[0]: incluir_sin_valor = True # en los casos en los que no hay valor, los trato como NO/FALSE
##		else:
##			pass # deberia ser solo la operacion IGUAL
##
##		filtro = Exploracion.valoresBool.any(
##					and_(
##						( ValorBool.campo_id == self.id ),
##						condicion
##					)
##				)
##
##		if incluir_sin_valor:
##			filtro = or_( (Exploracion.valoresBool == None), filtro)
##
##		return query.filter(filtro)



class Busqueda(object):
	"""
	"""

	def __init__(self, xml = None):
		self._clear()
		if xml:
			self.from_xml(xml)

	def _clear(self):
		self.campos = []

	def addCampo(self, tipo_campo, campo_id, conjunto_id):
		# dependiendo de los ids crea la clase de CampoBusqueda correspondiente
		C = None

		# es de Formulario
		if isint(conjunto_id):
##			C = CampoBusquedaForm
			if tipo_campo in (TIPO_TEXTO, TIPO_MEMO):
				C = CampoBusquedaFormTexto
			elif tipo_campo == TIPO_SELEC:
				C = CampoBusquedaFormSelec
			elif tipo_campo == TIPO_MULTI:
				C = CampoBusquedaFormMulti
			elif tipo_campo == TIPO_BOOL:
				C = CampoBusquedaFormBool
			else:
				raise Exception(_(u'No se ha podido identificar el tipo de campo para la búsqueda. Tipo de campo = %s') % tipo_campo)#IDIOMAOK

		# es de Conjunto (paciente, exploración)
		else:
			if campo_id == CAMPO_ID_SEXO:
				C = CampoBusquedaFijoSexo
			elif campo_id == CAMPO_ID_POBLACION:
				C = CampoBusquedaFijoPoblacion
			elif campo_id == CAMPO_ID_PROVINCIA:
				C = CampoBusquedaFijoProvincia
			elif campo_id == CAMPO_ID_ASEGURADORA:
				C = CampoBusquedaFijoAseguradora
			elif campo_id == CAMPO_ID_FECHA_EXPL:
				C = CampoBusquedaFijoFechaExpl
			elif campo_id == CAMPO_ID_MEDICO:
				C = CampoBusquedaFijoMedico
			elif campo_id == CAMPO_ID_TIPO_EXPL:
				C = CampoBusquedaFijoTipoExpl
			elif campo_id == CAMPO_ID_TIENE_IMAGENES:
				C = CampoBusquedaFijoTieneImagenes
			elif campo_id == CAMPO_ID_SERVICIO:
				C= CampoBusquedaFijoServicio
			elif campo_id == CAMPO_ID_EDAD_PACIENTE:
				C= CampoBusquedaFijoEdadPaciente
			elif campo_id == CAMPO_ID_ASEGURADORAS_ID:
				C= CampoBusquedaFijoAseguradoraId

			else:
				raise Exception(_('No se ha podido identificar el campo para la búsqueda. Id del campo = %s') % campo_id)#IDIOMAOK

		c = C(self)
		self.campos.append(c)
		return c


	def from_xml(self, xml):
		"""
		convierte una busqueda en formato XML a un objeto de Python.

		Formato del objeto Busqueda:

			Busqueda.campos[] (1..n)
				campo.id
				campo.operacion
				campo.conjunto.id
				campo.conjunto.descripcion
				campo.nombre
				campo.tipo
				campo.titulo
				campo.valores[] (1..n):

				  segun el tipo de campo puede ser directamente el valor o
				  un objeto con estos campos:

					valor.id
					valor.descripcion
		"""
		self._clear()
		xml = xml.encode('utf_8')   # XXX
		xml = XML(xml)
		for campo_xml in xml:
			campo_id =			campo_xml.find('campo_id').text.upper()
			conjunto_id = 		campo_xml.find('conjunto_id').text.upper()
			tipo_campo =        int( campo_xml.find('tipo_campo').text )
			try:
				tipo_control =		int( campo_xml.find('tipo_control').text )
			except ValueError as e:
				log.error(e)
				tipo_control = None
			except AttributeError as e:
				log.error(e)
				tipo_control = None

			campo = self.addCampo(tipo_campo, campo_id, conjunto_id)

			if campo_xml.find('tipo_control'):
				campo.tipo_control = int( campo_xml.find('tipo_control').text )
			else:
				campo.tipo_control = 0

	##		campo = record()
			campo.id =			campo_id
			campo.operacion =	campo_xml.find('operacion').text.upper()

			# CONJUNTO/FORMULARIO
			campo.conjunto = record()
			campo.conjunto.id = conjunto_id

			# es de Formulario
			if isint(campo.conjunto.id):
				formulario_reg = registro_by_id(Formulario, campo.conjunto.id) # xxx guardar la referencia al registro?
				if not formulario_reg:
					raise Exception(_(u'El formulario indicado por el id. de conjunto no se ha encontrado'))#IDIOMAOK
				campo.conjunto.descripcion = formulario_reg.titulo
			# es de Conjunto (paciente, exploración)
			else:
				campo.conjunto.descripcion = conjuntos[campo.conjunto.id].descripcion

			# CAMPO
			# es de Formulario
			if isint(campo.conjunto.id):
				# XXX   en vez de cogerlos del XML mejor consultarlo de bbdd
				campo.nombre =	campo_xml.find('nombre_campo').text
				campo.tipo =	tipo_campo
				campo.control = tipo_control
				campo.titulo =	campo_xml.find('titulo_campo').text
			# es de Conjunto (paciente, exploración)
			else:
				campo.nombre =	conjuntos[campo.conjunto.id].campos[campo.id].nombre
				campo.tipo =	conjuntos[campo.conjunto.id].campos[campo.id].tipo
				campo.titulo =	conjuntos[campo.conjunto.id].campos[campo.id].titulo

			# OPERACION
			# (nada mas)

			# VALORES
			campo.valores = []
			for v in campo_xml.find('valores').findall('valor'):
				valor = campo.valor_from_xml(v)
				campo.valores.append(valor)


	def to_xml(self, detail = False):
		"""
		convierte una busqueda en el formato de objeto de Python a XML

		detail: indica si se generará un XML mas detallado, util para cliente (js)
		"""
		campos_xml = Element('campos')
		for campo in self.campos:
			campo_xml = SubElement(campos_xml, 'campo')
			SubElement(campo_xml, 'campo_id').text = 				formatea_valor(campo.id)
			SubElement(campo_xml, 'nombre_campo').text = 			formatea_valor(campo.nombre)
			SubElement(campo_xml, 'titulo_campo').text = 			formatea_valor(campo.titulo)
			SubElement(campo_xml, 'tipo_campo').text = 				formatea_valor(campo.tipo)
			if getattr(campo, "control", None) is not None:
				SubElement(campo_xml, 'tipo_control').text = 			formatea_valor(campo.control)

			SubElement(campo_xml, 'conjunto_id').text = 			formatea_valor(campo.conjunto.id)
			SubElement(campo_xml, 'descripcion_conjunto').text =	formatea_valor(campo.conjunto.descripcion)

			SubElement(campo_xml, 'operacion').text = 				formatea_valor(campo.operacion)

			valores_xml = SubElement(campo_xml, 'valores')
			for valor in campo.valores:
				valor_xml = SubElement(valores_xml, 'valor')
				campo.valor_to_xml(valor, valor_xml)

		return tostring(campos_xml)


	def ejecutar(self, query):
		"""
		aplicar los filtros necesarios a un query de sqlalchemy para
		ejecutar la busqueda avanzada indicada.

		query:	  es el objeto Session.Query ejecutado sobre la tabla de
		exploraciones sobre el que se trabajará. Y viene filtrado por fechaini,
		fechafin y dicom_stored.
		"""
		# iterar los campos y aplicar sucesivamente todas las condiciones
		for campo in self.campos:
			query = campo.ejecutar(query)

		return query




def ejecutar_busqueda(busqueda, query):
	"""
	aplicar los filtros necesarios a un query de sqlalchemy para
	ejecutar la busqueda avanzada indicada.

	busqueda:	es la busqueda avanzada a ejecutar. Es lo mismo que llega
	al controlador REST. puede ser un int, indicando el id. de una búsqueda,
	o el xml de la búsqueda a ejecutar.

	query:	  es el objeto Session.Query ejecutado sobre la tabla de
	exploraciones sobre el que se trabajará. Y viene filtrado por fechaini,
	fechafin y dicom_stored.
	"""

	# extraer la busqueda a ejecutar, en xml
	if isint(busqueda):
		busqueda_reg = registro_by_id(endosys.model.busquedas.Busqueda, busqueda)
		if busqueda_reg:
			busqueda_xml = busqueda_reg.xml
		else:
			raise Exception(_(u'No se encuentra la búsqueda avanzada con id = %s') % busqueda)#IDIOMAOK
	else:
		busqueda_xml = busqueda

	# XXX   atención: se espera que la búsqueda xml tenga el formato correcto
	# documentado, si falta algún campo o la estructura es diferente puede dar
	# error

	# convertir el XML a objeto Busqueda, que es mas fácil de tratar con él
	return Busqueda(busqueda_xml).ejecutar(query)

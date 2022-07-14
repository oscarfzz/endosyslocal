''' clase base para crear un plugin de campos.

El plugin de campos sirve para añadir campos aparte de los normales de EndoSys.
Los valores de estos campos se obtienen y modifican de una forma externa al resto
de campos.

tipos de campos: texto, selec

XXX: seria interesante que se puedan usar mas de 1 plugin de campos simultaneamente.
XXX: que solo añada los campos a la primera prestacion!

el id de los campos de plugin es alfanumerico emepzando por '_'. (no puede ser '_rand')
el id de los campos normales es siempre un int


posibles errores: (usar los mismos codigos http, por conveniencia)

403 - No permitido: no se permite la operacion
401 - No autorizado: la operacion se permite pero no esta autorizado
400 - parametros incorrectos: los parametros suministrados son incorrectos
404 - no se ha encontrado: no existe ninguna cita con el id o parametros de busqueda indicados
500 - error no especificado

estados correctos:
200 - ok
201 - se ha creado correctamente

'''


from endosys.lib.misc import *
from endosys.lib.plugins.base import *
from endosys.model import meta
import endosys.model
from sqlalchemy.sql import and_

class Campo(object):

	def __init__(self, **kwargs):
		self.id = None
		self.nombre = None
		self.titulo = None
		self.tipo = None
		self.columnas = None
		self.orden = None
		self.solo_lectura = None
		self.grupoCampos_id = None
		self.grupoCampos_nombre = None
		self.grupoCampos_columnas = None
		for k in kwargs: setattr(self, k, kwargs[k])

class Elemento(object):

	def __init__(self, **kwargs):
		self.id = None
##		self.campo_id = None
		self.codigo = None
		self.nombre = None
		self.activo = True
		for k in kwargs: setattr(self, k, kwargs[k])


class PluginCampos(Plugin):

	def __init__(self):
		Plugin.__init__(self)

		#   "campos_actualizables" puede ser un dict de campos para los que se ejecutará
		#   la funcion "actualizar_elementos_campo".
		#   Se ha de indicar con este formato:
		#	   identificador_campo = nombres_campos
		#   siendo "identificador_campo" el nombre al que hará referencia la implementacion
		#   del plugin, y "nombres_campos" una lista de nombres que tienen los campos en endosys web.
		#   esto permite configurar estos campos independientemente del nombre que se les haya dado
		#   en endosys web y sin modificar el plugin.
		#   (no diferencia mays/mins, se hace un uppercase de todo)

		#   XXX podria ser interesante permitir asignar una lista de nombre de campos de endosys web...

		self.campos_actualizables = None
		self._dict_campos_actualizables_uppercased = False


	def _uppercase_dict_campos_actualizables(self):
		if self._dict_campos_actualizables_uppercased:
			return
		_temp = {}
		if self.campos_actualizables:
			for k, v in self.campos_actualizables.iteritems():
				_temp[k.upper()] = []
				for n in v:
					_temp[k.upper()].append(n.upper())
		self.campos_actualizables = _temp
		self._dict_campos_actualizables_uppercased = True


	def get_campos(self, prestacion):
		""" devuelve la lista de campos del plugin """
		""" prestacion es un registro. No usar las props de relaciones, como p.e. exploracion (usar exploracion_id) """
		pass

	def get_valor_campo(self, prestacion, campo_id):
		""" devuelve los valores de un campo. devuelve un iterable, aunque solo haya 1 valor.

		cada valor tendrá el formato siguiente segun el tipo:

		texto: str
		bool: bool
		selec: (int, str) (id, nombre)
		multi: (int, str) (id, nombre)

		si no hay valores se ha de devolver o uniterable vacio o None.

		p.e. un campo tipo multi con dos valores:
			( (1, 'valor uno'), (2, 'valor dos') )

		p.e. un campo tipo texto, por lo tanto 1 solo valor
			( 'valor del campo', )

		"""
		pass

	def set_valor_campo(self, prestacion, campo_id, valor):
		""" asigna un valor a un campo """
		pass

	def get_elementos_campo(self, campo_id):
		""" devuelve la lista de elementos si se trata de un campo de tipo selec """
		pass

	def get_elemento_campo(self, campo_id, elemento_id):
		""" devuelve un elemento de un campo por su id """
		for e in self.get_elementos_campo(campo_id):
			if e.id == elemento_id:
				return e
		return None

	def _do_actualizar_elementos_campo(self, campo_id):
		"""
		actualiza la lista de elementos si se trata de un campo de tipo selec.
		Sirve para que un campo se comporte de forma normal, guardando los elementos
		en la bbdd de endosys web, pero permitiendo obtenerlos de una fuente externa,
		sincronizandolos.
		"""
		# comprobar que el campo esté en la lista.
		campo = registro_by_id(endosys.model.Campo, campo_id)
		if campo:
			self._uppercase_dict_campos_actualizables()
			for k, v in self.campos_actualizables.iteritems():
				if campo.nombre.upper() in v:

					#   comprobar que sea un campo de tipo selec
					if not(campo.tipo in (2, 3)):	# los tipos 2 y 3 son de seleccion y multiseleccion, respectivamente
						raise E_ParamIncorrecto(u'El campo indicado no es de tipo selección')

					# obtener la lista actualizada, y actualizar los elementos del campo
					elementos = self.actualizar_get_elementos_campo(k)
					for codigo, nombre in elementos.iteritems():
						# si ya existe el elemento con el codigo indicado, actualizarlo
						q = meta.Session.query(endosys.model.Elemento).filter(
										and_(*[
											(endosys.model.Elemento.codigo == codigo),
											(endosys.model.Elemento.campo_id == campo_id)
										])
							)
						if q.count() > 0:
							elemento = q.one()
							elemento.nombre = nombre
							meta.Session.update(elemento)
						else:
							elemento = endosys.model.Elemento()
							elemento.campo_id = campo_id
							elemento.codigo = codigo
							elemento.nombre = nombre
							elemento.activo = True
							meta.Session.save(elemento)

					# marcar como no activos los elementos que ya no estan en la lista actualizada
					q = meta.Session.query(endosys.model.Elemento).filter(endosys.model.Elemento.campo_id == campo_id)
					lista = q.all()
					for elemento in lista:
						if elemento.codigo in elementos:
							elemento.activo = True
						else:
							elemento.activo = False
						meta.Session.update(elemento)

					meta.Session.commit()
					break
		else:
			raise E_ParamIncorrecto('El id. de campo indicado no es correcto')

	def actualizar_get_elementos_campo(self, identificador_campo):
		"""
		este es el metodo que se ha de "overridear" que ya ha pasado el filtro
		de la lista de campos actualizables.
		"nombre_campo" siempre es en MAYS
		tiene que devolver una lista de los registros, por ejemplo obtenidos de
		una fuente externa. La lsita es un dict, con la forma:
			codigo: descripcion
		"""
		return {}

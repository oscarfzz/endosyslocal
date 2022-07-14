import time
from datetime import date

import logging
log = logging.getLogger(__name__)

class PluginException(Exception):
	http_status = 500
	endotools_errorcode = 0
	def __init__(self, *args, **kwargs):
		#   XXX	si los params son unicode los paso a str...
		#   aunque esto seria mejor hacerlo a otro nivel para que sirve para
		#	cualquier excepcion (creo que en lib.middleware.error -> EndoTools_ErrorHandler)

		if 'codigo' in kwargs:
			self.endotools_errorcode = kwargs['codigo']

		_args = []
		for a in args:
			if isinstance(a, unicode): a = a.encode('utf-8')
			_args.append(a)
		#   #######################
		Exception.__init__(self, *_args)


class E_ErrorServidor(PluginException):
	http_status = 500
	def __init__(self, *args, **kwargs):
		log.debug(args)
		if args == (): args = ('Error en el servidor',)
		PluginException.__init__(self, *args, **kwargs)

class E_NoPermitido(PluginException):
	http_status = 403
	def __init__(self, *args, **kwargs):
		log.debug(args)
		if args == (): args = ('Operación no permitida',)
		PluginException.__init__(self, *args, **kwargs)

class E_NoAutorizado(PluginException):
	http_status = 401
	def __init__(self, *args, **kwargs):
		if args == (): args = ('Operación no autorizada',)
		PluginException.__init__(self, *args, **kwargs)

class E_ParamIncorrecto(PluginException):
	http_status = 400
	def __init__(self, *args, **kwargs):
		if args == (): args = ('Parámetros incorrectos',)
		PluginException.__init__(self, *args, **kwargs)

class E_NoEncontrado(PluginException):
	http_status = 404
	def __init__(self, *args, **kwargs):
		if args == (): args = ('No se han devuelto valores',)
		PluginException.__init__(self, *args, **kwargs)


_plugins = []

class Plugin(object):

	def __init__(self):
		_plugins.append(self)
		self._dependencies = []
		self.preprocess_mode = False

	def __del__(self):
		_plugins.remove(self)

	def _add_dependence(self, plugin_class):
		self._dependencies.append(plugin_class)

	def check_dependencies(self):
		log.debug('comprobar dependencias de %s:', type(self).__name__)
		if not self._dependencies:
			log.debug('   sin dependencias')
		for plugin_class in self._dependencies:
			plugins = filter(lambda p: isinstance(p, plugin_class), _plugins)
			if not plugins:
				raise Exception('No se ha encontrado la dependencia requerida (%s) para el plugin (%s)' % (plugin_class.__name__, type(self).__name__))
			if len(plugins) > 1:
				raise Exception('Existen más de una instancia del plugin (%s). Sólo puede haber una instancia de cada plugin' % (plugin_class.__name__))
			log.debug(' - dependencia correcta (%s)', plugin_class.__name__)
		print ''


def check_dependencies():
	for plugin in _plugins:
		plugin.check_dependencies()


def obj_from_params(obj, params):
	""" actualiza el objeto a partir de los params (obtenidos del request).
	se utiliza para el update y create
	"""
	for campo, valor in params.iteritems():
		# omite los parametros que empiezan por _ , y tambien si hay algun parametro llamado "id"
		if campo.startswith('_'): continue
		if campo == 'id': continue
		if hasattr(obj, campo):
			# cadena vacia se interpreta como null
			if valor == '':
				valor = None

			# booleano ('0' o '1')
			elif isinstance( getattr(obj, campo), bool ):
				valor = bool(int(valor))

			# int
			elif isinstance( getattr(obj, campo), int ):
				valor = int(valor)

			# si el campo es tipo fecha, convertir
			elif isinstance(getattr(obj, campo), date):  # ojo, datetime.date, no sqlalchemy.types.Date!
##				try:
				t = time.strptime(valor, "%d/%m/%Y")
##				except ValueError:
##					abort(400, "ERROR: el formato de la fecha es incorrecto")
				valor = date(t.tm_year, t.tm_mon, t.tm_mday)

			# resto
			setattr(obj, campo, valor)
		else:
			pass	# XXX deberia lanzar una excepcion?
##			abort(400, "ERROR: no existe el campo '%s'" % campo)

import time
from paste.deploy.converters import asbool
from pylons.error import PylonsEvalException
##from pylons import *
##from pylons.decorators import jsonify

__view_original = None

def EndoTools_ErrorHandler(app, global_conf, **errorware):
	global __view_original
	if asbool(global_conf.get('debug')):
		from pylons.error import PylonsEvalException
		PylonsEvalException.summary = __summary;	# sustituyo la funcion summary por una propia ( * ver explicacion abajo de todo del archivo)
		__view_original = PylonsEvalException.view
		PylonsEvalException.view = __view
		app = PylonsEvalException(app, global_conf, **errorware)
	else:
		#   XXX creo que se tendria que hacer algo parecido a lo de arriba del
		#	PylonsEvalException pero con el ErrorMiddleware,
		#   para tratar los casos que la excepcion tenga un message unicode...
		from endosys.config.errormiddleware import CustomErrorMiddleware
		if 'error_template' in errorware:
			del errorware['error_template']
		app = CustomErrorMiddleware(app, global_conf, **errorware)
	return app



def __format(item):
	from endosys.lib.base import h
	import simplejson
	exception = item.exc_value
	if isinstance(exception, Exception):
		exception = exception.message
		try:
			exception = exception.decode('latin-1') # el Valme (Oracle) daba un error al mostrar las excepciones, con esto se soluciona...
			if isinstance(exception, unicode):
				exception = exception.encode('utf-8')
		except Exception, e:
			exception = 'Ocurrio un error'
	o = {
		'uri': item.view_uri,
		'created': h.escape_once( time.strftime('%c', time.gmtime(item.created)) ),
		'exception_type': h.escape_once( str(item.exc_type) ),
		'exception':  h.escape_once( exception )
		}
	return o


def __summary(self, environ, start_response):
	import simplejson

	username = environ.get('REMOTE_USER', '')
	if not username.upper() == "SYSADMIN":
		start_response('403 FORBIDDEN', [('Content-type', 'text/plain')])
		return 'error'

	start_response('200 OK', [('Content-type', 'text/x-json')])
	items = self.debug_infos.values()
	items.sort(lambda a, b: cmp(a.created, b.created))
	o = [__format(item) for item in items]

	return simplejson.dumps(o)
__summary.exposed = True


def __view(self, environ, start_response):

	username = environ.get('REMOTE_USER', '')
	if not username.upper() == "SYSADMIN":
		start_response('403 FORBIDDEN', [('Content-type', 'text/plain')])
		return 'error'

	return __view_original(self, environ, start_response)
__view.exposed = True

##	username = environ.get('REMOTE_USER', '')
##	if not username.upper() == "SYSADMIN":
##		start_response('403 FORBIDDEN', [('Content-type', 'text/plain')])
##		return 'error'
##
##	start_response('200 OK', [('Content-type', 'text/x-json')])
##	items = self.debug_infos.values()
##	items.sort(lambda a, b: cmp(a.created, b.created))
##	o = [__format(item) for item in items]
##
##	return simplejson.dumps(o)


##class EndoToolsEvalException(PylonsEvalException):
##
##	def __format(self, item):
##		from endosys.lib.base import h
##		import simplejson
##		o = {
##			'uri': item.view_uri,
##			'created': h.escape_once( time.strftime('%c', time.gmtime(item.created)) ),
##			'exception_type': h.escape_once( str(item.exc_type) ),
##			'exception':  h.escape_once( str(item.exc_value) )
##			}
##		return o
##
##	def summary(self, environ, start_response):
##
##		"""
##		Returns a JSON-format summary of all the cached exception reports.
##		mas informacion en paste\evalexception\middleware.py,
##		clases EvalException y DebugInfo.
##		"""
##		import simplejson
##
##		start_response('200 OK', [('Content-type', 'text/x-json')])
##		items = self.debug_infos.values()
##		items.sort(lambda a, b: cmp(a.created, b.created))
##		o = [self.__format(item) for item in items]
##
##		return simplejson.dumps(o)
##	summary.exposed = True
##


# * primero lo habia hecho con una nueva clase "EndoToolsEvalException" que heredaba
# de 'PylonsEvalException', pero esta ultima utiliza en el metodo 'media' la funcion
# 'super' y parece que entonces no devolvia su padre (EvalException) sino a si misma,
# ya que se llamaba desde su hija (EndoToolsEvalException)

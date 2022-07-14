''' clase base para crear un plugin de informes.

posibles errores: (usar los mismos codigos http, por conveniencia)

403 - No permitido: no se permite la operacion
401 - No autorizado: la operacion se permite pero no esta autorizado
400 - parametros incorrectos: los parametros suministrados son incorrectos
404 - no se ha encontrado: no existe ningún informe con el id o parametros de busqueda indicados
500 - error no especificado

estados correctos:
200 - ok
201 - el informe se ha creado correctamente

'''

# XXX Mejor usar excepciones?

from endosys.lib.plugins.base import Plugin

class Informe(object):

	def __init__(self, **kwargs):
		self.id = None
		for k in kwargs: setattr(self, k, kwargs[k])


class PluginInformes(Plugin):

	def __init__(self):
		Plugin.__init__(self)

##	def informe_generado(self, id, contenido_informe, medico):
	def informe_generado(self, informe, medico):
		""" se ejecuta cuando se ha generado un nuevo informe. Sirve para notificarlo
		o enviarlo a otro sistema.
##		id  				es el id. del informe (en bbdd)
##        contenido_informe   string, es el contenido en HTML del archivo de informe generado

        informe             registro de sql alchemy del Informe
		"""
		pass

	def informe_borrado(self, informe, medico):
		""" se ejecuta cuando se ha borrado un informe. Sirve para notificarlo
		o enviarlo a otro sistema.
##		id  				es el id. del informe (en bbdd)
##        contenido_informe   string, es el contenido en HTML del archivo de informe generado

        informe             registro de sql alchemy del Informe
		"""
		pass

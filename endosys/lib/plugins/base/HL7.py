''' clase base para crear un plugin de HL7.

A diferencia del resto de plugins, no "sustituye" la funcionalidad de un controller REST,
sino que permite modificar o filtrar los mensajes HL7 de entrada y de salida. Se
usa cuando no es suficiente con Mirth Connect.
En principio no se encarga del transporte.
'''

##from endosys.lib.misc import record
from endosys.lib.plugins.base import obj_from_params, Plugin
##from datetime import date

#   De momento son las mismas funciones que en hl7_process, con algunos parametros
#   adicionales
class PluginHL7(Plugin):

	def __init__(self):
		Plugin.__init__(self)

	def enviar_captura_actividad(self, msgs, cita, estado, motivo_id=None):
		"""
		Se llama después de generar los mensajes ORR/ORM/ADT, justo antes de
		enviarlos por HTTP al Mirth.

		msgs						Es un dict que tiene los items 'msg_order' y
									'msg_ADT', que son los mensajes (string) generados
									que se van a enviar. Pueden ser None (si no se envían).
									Se puede modificar su valor, o poner a None
									para que no se envíen.

		cita, estado y motivo_id	Son los mismos parametros recibidos en la
									función hl7_process.enviar_captura_actividad()
		"""
		pass

import logging

import os
from endosys.lib.base import *
from pylons import config
from datetime import date
from endosys.lib.checks import check_cache_dir
from endosys.lib.misc import *
from authkit.authorize.pylons_adaptors import authorize
from authkit.permissions import RemoteUser, ValidAuthKitUser, UserIn, HasAuthKitRole, And
from endosys.lib.hl7_wrapper.receiving import Hl7Process

log = logging.getLogger(__name__)


class Hl7Controller(BaseController):

	#@authorize(UserIn(['sysadmin']))
	def process(self):
		"""
		Recibir un nuevo mensaje HL7, guardarlo y procesarlo.
		Se espera en formato XML (tal como lo genera Mirth Connect)

		Mensajes que reconoce:
			ADT - A04   Nuevo paciente
			ADT - A08   Modificar paciente
			ADT - A¿?   Fusionar pacientes (por NHC)
			ORM - O01   Nueva cita (petición) o cancelación
			SIU - S12   Nueva cita
			SIU - S13   modificar cita
			SIU - S14   modificar cita (información administrativa, NO hora, prestación, etc...)
			SIU - S15   cancelar cita

		  method=POST

		NO:
		  content-type=text/xml
		  content=(mensaje hl7 en formato xml)

		asi:
		  content-type=text/plain
		  content=(mensaje hl7 en formato pipe)
		y usar python-hl7 para procesarlo

		"""
		ipaddress = request.environ['REMOTE_ADDR']
		msg = request.body.read()
		hl7_process = Hl7Process(msg)
		hl7_process.ipaddress = ipaddress
		hl7_process.procesar_mensaje()
		response.status_code = 200
		return "ACK ok"

	#@authorize(UserIn(['sysadmin']))
	def config(self):
		"""
		XXX
		Interfaz para poder configurar el "parseo" de mensajes HL7 desde
		Endosys App. Por ejemplo, podría servir para indicar qué campo
		de los mensajes ORM se utiliza como identificador, si se han de
		omitir algunos campos del segmento PID, etc...
		Mirth Connect podría llamar a config() en el deploy. La configuración
		debería ser persistente, por si se reinicia el servidor de EndoSys
		"""
		pass
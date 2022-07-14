import logging
import os
import csv
from datetime import datetime

from pylons.i18n import _
from pylons import config

from authkit.authorize.pylons_adaptors import authorize
from sqlalchemy.sql import and_, or_, not_

from endosys.lib.usuarios.seguridad import roles
from endosys.config.plugins import pluginPacientes
import endosys.lib.registro as registro
from endosys.lib.base import CommandController
from endosys.lib.capturas import _mover_capturas_ruta_correcta
from endosys.lib.tareas import nueva_tarea, crear_hilo

log = logging.getLogger(__name__)

class OrganizarInformesController(CommandController):

	#file_path = os.path.join(config['pylons.paths']['custom'], 'csv\import_pacientes.csv')

	def run_command(self):
		
		tarea = nueva_tarea("sysadmin",'ORG_INF')
		#crea el hilo para realizar la tarea
		crear_hilo(tarea,{})

	def get(self, request):
		a_volver = u'<a href="/admin"> << Volver </a> <br>'
		h1 = u'<h1>Reorganización de informes</h1>'
		descripcion = u'Mueve los informes que se ubican en la raiz de la carpeta de informes a su estructura correcta con el formato /año/mes'
		form = u'<form method="post"><button type="submit">Ejecutar Tarea</button></form>'
		return u'<html><head></head><body>'+a_volver+h1+'<div>'+descripcion+u'</div><br />'+form+u'</body></html>'

	def post_message(self):
		a_volver = u'<a href="/admin"> << Volver </a> <br>'
		return a_volver + u'<p>Comando Ejecutado. Ingrese a "Tareas" del EndoSys para ver el estado de la misma.</p>'
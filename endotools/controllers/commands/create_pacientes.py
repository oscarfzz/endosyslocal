import logging
import os
import csv
from datetime import datetime

from pylons.i18n import _
from pylons import config
from authkit.authorize.pylons_adaptors import authorize
from sqlalchemy.sql import and_, or_, not_

from endotools.model.session import meta
from endotools.model.pacientes import Paciente, t_pacientes
from endotools.lib.usuarios.seguridad import roles
from endotools.config.plugins import pluginPacientes
from endotools.lib.pacientes import get_by_historia, nuevo_paciente
import endotools.lib.registro as registro
from endotools.lib.base import CommandController

log = logging.getLogger(__name__)


class CreatePacientesController(CommandController):

	file_path = os.path.join(config['pylons.paths']['custom'], 'csv\import_pacientes.csv')

	def run_command(self):
		with open(self.file_path) as csvfile:	
			reader = csv.DictReader(csvfile, delimiter=';', quotechar='"')
			count = 0
			for row in reader:
				count += 1
				if not count % 1000:
					log.debug( 'Inserting ' + row['historia'])
				insert_statement = t_pacientes.insert().values(**row)
				try:
					meta.Session.execute(insert_statement)
				except Exception as e:
					log.error('Error importing ' + row['historia'])
					log.error(str(e))
			meta.Session.commit()

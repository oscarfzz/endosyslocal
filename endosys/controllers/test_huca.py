import logging

import os
from endosys.lib.base import *
from pylons import config
from datetime import date
from pylons.decorators import jsonify
from endosys.lib.misc import formatea_valor

from authkit.authorize.pylons_adaptors import authorize
from authkit.permissions import RemoteUser, ValidAuthKitUser, UserIn, HasAuthKitRole, And
from endosys.lib.usuarios.seguridad import roles

log = logging.getLogger(__name__)


class TestHucaController(BaseController):

	@jsonify
	@authorize(UserIn(['sysadmin']))
	def run_sql(self):
		if not 'sql' in request.params:
			return {}
		sql = request.params['sql']
		from custom.HUCA.plugins.informix_db import ejecutar_sql
		import custom.HUCA.plugins.config
		result, description = ejecutar_sql(sql)

		# devuelve el resultado en formato JSON (para cargar en el datatable de YUI)
		if result:
			rs = []
			for row in result:
				r = {}
				cont = 0
				for col in description:
					r[col[0]] = formatea_valor( row[cont] )
					cont += 1
				rs.append(r)
			return {
				'columns': [col[0] for col in description],
				'rows': rs
				}
		else:
			return {}


	@jsonify
	@authorize(UserIn(['sysadmin']))
	def citas(self):
		from custom.HUCA.plugins.informix_db import get_citas
		import custom.HUCA.plugins.config
		import datetime
		lista = get_citas(datetime.date.today(), custom.HUCA.plugins.config.salas)

		# devuelve el resultado en formato JSON (para cargar en el datatable de YUI)
		rs = []
		for c in lista:
			r = {
				'numicu': 					formatea_valor(c.info.codigo_cita),
				'historia': 				formatea_valor(c.paciente.historia),
				'hora': 					formatea_valor(c.hora),
				'codigo_prestacion': 		formatea_valor(c.info.codigo_prestacion),
				'descripcion_prestacion': 	formatea_valor(c.info.descripcion_prestacion),
				'nombre': 					formatea_valor(c.paciente.nombre),
				'apellido1': 				formatea_valor(c.paciente.apellido1),
				'apellido2': 				formatea_valor(c.paciente.apellido2)
			}
			rs.append(r)
		return {
			'columns': ['numicu', 'historia', 'hora', 'codigo_prestacion',
						'descripcion_prestacion', 'nombre', 'apellido1', 'apellido2'],
			'rows': rs
			}


	@jsonify
	@authorize(UserIn(['sysadmin']))
	def paciente(self):
		if not 'nhc' in request.params:
			return {}
		nhc = request.params['nhc']
		from custom.HUCA.plugins.informix_db import get_paciente
		import custom.HUCA.plugins.config
		p = get_paciente(nhc)
		if not p: return {}

		# devuelve el resultado en formato JSON (para cargar en el datatable de YUI)
		rs = []
		r = {
			'historia': 				formatea_valor(p.historia),
			'nombre': 					formatea_valor(p.nombre),
			'apellido1': 				formatea_valor(p.apellido1),
			'apellido2': 				formatea_valor(p.apellido2),
			'sexo': 					formatea_valor(p.sexo),
			'fecha_nac':				formatea_valor(p.fechaNacimiento),
			'num_ss':					formatea_valor(p.numAfiliacion)
		}
		rs.append(r)
		return {
			'columns': ['historia',	'nombre', 'apellido1', 'apellido2', 'sexo',
						'fecha_nac', 'num_ss'],
			'rows': rs
			}


	@jsonify
	@authorize(UserIn(['sysadmin']))
	def informe(self):
		if not 'numicu' in request.params:
			return {}
		numicu = request.params['numicu']
		from custom.HUCA.plugins.informix_db import get_informe
		import custom.HUCA.plugins.config
		i = get_informe(numicu)
		if not i: return {}

		# devuelve el resultado en formato JSON (para cargar en el datatable de YUI)
		rs = []
		r = {
			'numicu': 				formatea_valor(i[0]),
			'numerohc':				formatea_valor(i[1]),
			'informe':				formatea_valor(i[2]),
			'imagenes':				formatea_valor(i[3]),
			'fecha': 				formatea_valor(i[4]),
			'hora': 				formatea_valor(i[5]),
			'numexp':				formatea_valor(i[6]),
			'numinf':				formatea_valor(i[7]),
			'tipexp':				formatea_valor(i[8]),
			'tipo':					formatea_valor(i[9])
		}
		rs.append(r)
		return {
			'columns': ['numicu', 'numerohc', 'informe', 'imagenes', 'fecha', 'hora', 'numexp',
						'numinf', 'tipexp', 'tipo'],
			'rows': rs
			}


	@jsonify
	@authorize(UserIn(['sysadmin']))
	def total_informes(self):
		numicu = request.params.get('numicu', None)
		if not numicu: numicu = None
		from custom.HUCA.plugins.informix_db import get_total_informes
		import custom.HUCA.plugins.config
		i = get_total_informes(numicu)

		# devuelve el resultado en formato JSON (para cargar en el datatable de YUI)
		rs = []
		r = {
			'total': 				formatea_valor(i)
		}
		rs.append(r)
		return {
			'columns': ['total',],
			'rows': rs
			}

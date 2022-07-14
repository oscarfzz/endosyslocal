"""
-Añadir un chequeo de las plantillas de informes. Que intente generar un informe
 con cada plantilla de cada tipo de exploración, y devuelva cuáles se generan bien
 y cuales fallan (si fallan debería ser por variables que no existen en la plantilla)

XXX Se ha anulado la funcionalidad de chequeo de plantillas por el momento, ya
	que se tiene que estudiar cómo se implementa usando MS Word.
"""

import logging

import os
from endosys.lib.base import *
from pylons import config
from datetime import date

from endosys.model import meta
from endosys.lib.informes import generar_informe
from endosys.lib.checks import check_cache_dir
from endosys.lib.misc import *
from authkit.permissions import RemoteUser, ValidAuthKitUser, UserIn, HasAuthKitRole, And

log = logging.getLogger(__name__)

class CheckController(BaseController):

	@authorize(UserIn(['sysadmin']))
	def index(self):
		"""
		realiza algunos checks en la configuración de Endosys App, debido a
		las modificaciones realizadas a partir del 15-6-2012
		"""
		response.content_type = "text/html"
		s = '<html><head></head><body>'

		# lista de variables de configuración
		s += '<h2>Configuración</h2>'
		s += '<table border=1>'
		s += '<tr><td>archivo INI</td><td>%s</td></tr>' % config['__file__']
		s += '<tr><td>pylons.paths root</td><td>%s</td></tr>' % config['pylons.paths']['root']
		s += '<tr><td>pylons.paths root_parent</td><td>%s</td></tr>' % config['pylons.paths'].get('root_parent', '<i>(no definido)</i>')
		s += '<tr><td>cache_dir</td><td>%s</td></tr>' % config.get('pylons.cache_dir', '<i>(no definido)</i>')
		s += '</table>'

		# comprobaciones
		s += '<h2>Comprobaciones</h2>'
		s += '<ul>'
		#   'cache_dir', comprobar que NO sea '/data'
		if check_cache_dir():
			s += '<li style="color: green;">'
			s += 'La carpeta de cache de Pylons (cache_dir) está configurada en /cache '
			s += '(u otra carpeta distinta a /data). '
			s += 'Esta es la configuración correcta, de forma que las capturas e informes se '
			s += 'almacenarán en las carpetas /data/capturas y /data/informes </li>'
			s += '</li>'
		else:
			s += '<li style="color: red;">'
			s += '<b>La carpeta de cache de Pylons (cache_dir) está configurada en /data. '
			s += 'Esta es la configuración antigua (por defecto de Pylons), ahora se debe utilizar '
			s += 'la carpeta /cache. Se debe cambiar esto en el archivo INI, hasta que no se corrija '
			s += 'no se utilizará la carpeta /data para guardar las capturas e informes, y se seguirán '
			s += 'almacenando en /endotools/capturas y /endotools/informes</b>'
			s += '</li>'

		s += '</ul>'

		# carpetas que se utilizarán
		s += '<h2>Carpetas</h2>'
		s += '<table border=1>'
		s += '<tr><td>Capturas</td><td>%s</td></tr>' % config['pylons.paths'].get('capturas', '<i>(no definido)</i>')
		s += '<tr><td>Informes</td><td>%s</td></tr>' % config['pylons.paths'].get('informes', '<i>(no definido)</i>')
		s += '<tr><td>Custom</td><td>%s</td></tr>' % config['pylons.paths'].get('custom', '<i>(no definido)</i>')
		s += '<tr><td>Custom - plantillas</td><td>%s</td></tr>' % config['pylons.paths'].get('custom_informes_templ', '<i>(no definido)</i>')
		s += '<tr><td>Custom - plantillas (recursos)</td><td>%s</td></tr>' % config['pylons.paths'].get('custom_informes_res', '<i>(no definido)</i>')
		s += '<tr><td>Custom - plugins</td><td>%s</td></tr>' % config['pylons.paths'].get('custom_plugins', '<i>(no definido)</i>')
		s += '</table>'

		s += '</body></html>'

		return s


	@authorize(UserIn(['sysadmin']))
	def test_plantilla(self):
		"""
		params:
			tipo_exploracion_id     int
			plantilla               str
			formato                 str puede ser "PDF" o "HTML" (por defecto PDF)
		"""
		formato = request.params.get('formato', 'PDF').upper()
		if formato == 'HTML':
			# devolver en HTML
			tipo_exploracion_id = request.params['tipo_exploracion_id']
			plantilla = request.params['plantilla']
			response.content_type = "text/html"
			return generar_informe(int(tipo_exploracion_id), plantilla, allow_undefined_vars = True)
		elif formato == 'PDF':
			# devolver en PDF
			tipo_exploracion_id = request.params['tipo_exploracion_id']
			plantilla = request.params['plantilla']
			informe = generar_informe(int(tipo_exploracion_id), plantilla, local = True, allow_undefined_vars = True)

			import sx.pisa3 as pisa
			import StringIO
			result = StringIO.StringIO()
			pdf = pisa.CreatePDF(informe, result, None, debug = 1)
			if pdf.err:
				abort_xml(500, 'Error convirtiendo el informe a formato PDF (%s)')
			response.content_type = "application/pdf"
			response.content_length = result.len
			return result.getvalue()
		else:
			abort_xml(400, u'Formato de previsualización de plantilla de informe no soportado: %s' % formato)


	@authorize(UserIn(['sysadmin']))
	def plantillas(self):
		"""
		Por cada tipo de exploración comprueba si se genera correctamente
		cada plantilla de informe

		XXX esto puede tardar, hacerlo de forma asincrona... (AJAX)
		"""

		#   XXX anulado temporalmente
		response.content_type = "text/html"
		return '<p>Esta funcionalidad ha sido deshabilitada a partir de la versión 2.2.0</p>'
		# 	#########

		from endotools.model.tiposExploracion import TipoExploracion
		from endotools.lib.misc import registro_by_id, formatea_valor
		from endotools.model import meta
		from endotools.lib.formularios import FormExplData
		from endotools.lib.informes import get_plantillas

		response.content_type = "text/html"
		s = u'<h1>Comprobar plantillas de informes</h1>'
		#		s += u'<select><option value="PDF" selected="selected">PDF</option><option value="HTML">HTML</option></select>'

		plantillas = get_plantillas()
		tiposexpl = meta.Session.query(TipoExploracion).all()
		# Tipos de exploración
		for t in tiposexpl:
			s += u'<h2>%s</h2>' % formatea_valor(t.nombre)
			s += u'<table>'
			for plantilla in plantillas:
				# intenta generar el informe para ver si falla o no
				resultado = '<span style="color: green;">Ok</span>'
				try:
					generar_informe(t.id, plantilla, allow_undefined_vars = False)
				except Exception as e:
					log.error(e)
					resultado = '<span style="color: red;">Error</span>'
				s += u'<tr><td>%s</td><td>%s</td><td><a href="%s">PDF</a></td><td><a href="%s">HTML</a></td></tr>' %\
					( plantilla, resultado,
					h.url_for(controller='check', action='test_plantilla', formato='PDF', tipo_exploracion_id=t.id, plantilla=plantilla),
					h.url_for(controller='check', action='test_plantilla', formato='HTML', tipo_exploracion_id=t.id, plantilla=plantilla) )
			s += u'</table>'

		return s



	@authorize(UserIn(['sysadmin']))
	def test(self):
		"""
		prueba, de momento no se usa
		"""
		from endosys.model.tiposExploracion import TipoExploracion
		from endosys.lib.misc import registro_by_id, formatea_valor
		from endosys.model import meta
		from endosys.lib.formularios import FormExplData

		response.content_type = "text/html"
		s = u'<h1>Tipos de exploración: Formularios y grupos de campos</h1>'
		tiposexpl = meta.Session.query(TipoExploracion).all()
		# Tipos de exploración
		for t in tiposexpl:
			s += u'<h2>%s</h2>' % t.nombre

			# Formularios
			s += u'<ul>'
			for f in t.formularios:
				s += u'<li>'
				s += u'<h3>%s</h3>' % formatea_valor(f.formulario.titulo)

				formexpldata = FormExplData(f.formulario)

				# Grupos de campos
				s += u'<ul>'
				for g in formexpldata.gruposCampos:
					s += u'<li>'
					s += u'<h4>%s</h4>' % g.nombre

					# Campos
					s += u'<ul>'
					for c in g.campos:
						s += u'<li>%s</li>' % formatea_valor(c.titulo)
					s += u'</ul>'
					s += u'</li>'
				s += u'</ul>'
				s += u'</li>'
			s += u'</ul>'
		return s
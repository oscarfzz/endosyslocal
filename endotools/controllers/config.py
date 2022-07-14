"""
-Añadir un chequeo de las plantillas de informes. Que intente generar un informe
 con cada plantilla de cada tipo de exploración, y devuelva cuáles se generan bien
 y cuales fallan (si fallan debería ser por variables que no existen en la plantilla)
"""

import logging

import os
from endotools.lib.base import *
from pylons import config
from datetime import date
# ConfigObj preserva comentarios, espacios, etc... mientras que ConfigParser no.
from configobj import ConfigObj

from authkit.authorize.pylons_adaptors import authorize
from authkit.permissions import RemoteUser, ValidAuthKitUser, UserIn, HasAuthKitRole, And

from endotools.lib.checks import check_cache_dir
from endotools.lib.misc import *

log = logging.getLogger(__name__)



class ConfigController(BaseController):

	@authorize(UserIn(['sysadmin']))
	def index(self):
		"""
		consultar y modificar la configuración (INI) de Endosys App.
		el parametro "modo=basico|avanzado|completo" indica si se mostrará la
		config básica, avanzada o completa.
		La config completa muestra todas las claves del INI, mientras que la
		básica muestra sólo unas predefinidas básicas, y la avanzada muestra un
		conjunto más amplio.
		Por defecto se muestra la config básica.
		"""

		CLAVES_BASICAS = [
            'HL7.CONSULTA_PACIENTES.ACTIVO',
			'COLUMNAS_CITAS',
			'ENVIAR_ORR.ACTIVO',
			'ENVIAR_ORR.DESTINO',
			'ENVIAR_ORU.ACTIVO',
			'ENVIAR_ORU.VERSIONES',
			'ENVIAR_ORU.DESTINO',
			'ENVIAR_ORU.LINKS.HOST',
			'FORMATO_INFORMES',
			'INFORME_PDF.GUARDAR',
			'INFORME_PDF.CARPETA',
			'GRUPOS_CAMPOS_USAR_TABS',
			'USAR_LDAP',
			'LDAP_DNS_NAME',
			'LDAP_PORT',
			'LDAP_DOMAIN',
			'PORT',
			'FIRMA_ELECTRONICA.ACTIVO',
            'CITAS_PENDIENTES_MODO',
			'CITAS_PENDIENTES_REFRESCO',
            'CITAS_PENDIENTES_MODO'
		]

		CLAVES_AVANZADAS = [
			'CARPETA_CUSTOM',
			'MOSTRAR_PRESTACION_EN_CITAS',
			'MOSTRAR_BOTONES_MODIFICACION_PACIENTES',
			'MOSTRAR_OPCION_NUEVA_EXPLORACION',
			'MOSTRAR_OPCION_GESTION_CITAS',
			'PERMITIR_CAMBIAR_TIPO_EXPLORACION_DE_CITA',
			'DEBUG',
			'SQLALCHEMY.URL',
			'CACHE_DIR',
			'ENTORNO'
		]

		modo_config = {'BASICA': 0, 'AVANZADA': 1, 'COMPLETA': 2}.get(request.params.get('modo', 'BASICA').upper(), 'BASICA')
		ini = ConfigObj(config['__file__'], list_values = False, interpolation = False)

		response.content_type = "text/html"
		s = '<html><head>'
##		s += '<script type="text/javascript" src="/lib/jquery/js/jquery-1.8.2.js"></script>'
		s += '<script data-main="/web/" type="text/javascript" src="/lib/jquery/require-jquery.js"></script>'


		s += '<style type="text/css">'
		s += 'table {width: 100%;} '
		s += '.valor {width: 100%;} '
		s += '.key_col {width: 30%;} '
		s += '.value_col {width: 70%;} '
		s += '.modificado {color: red;} '
		s += '#cambia {float: right;} '
##		s += 'th {text-align: left;} '
##		s += '.section_row {} '
		s += '</style>'

		s += '</head><body>'

##		s += '<p>IP cliente: ' + request.environ.get('X_FORWARDED_FOR', request.environ['REMOTE_ADDR']) + '</p>'
		s += '<p>IP cliente: ' + request.environ['REMOTE_ADDR'] + '</p>'

		if modo_config == 0:
			s += '<h1>Configuración básica</h1>'
			s += '<div id="cambia">'
			s += '<a href="%s">avanzada</a>' % h.url_for(controller='config', modo='AVANZADA')
			s += '<br>'
			s += '<a href="%s">completa</a>' % h.url_for(controller='config', modo='COMPLETA')
			s += '</div>'
		elif modo_config == 1:
			s += '<h1>Configuración avanzada</h1>'
			s += '<div id="cambia">'
			s += '<a href="%s" id="cambia">básica</a>' % h.url_for(controller='config', modo='BASICA')
			s += '<br>'
			s += '<a href="%s" id="cambia">completa</a>' % h.url_for(controller='config', modo='COMPLETA')
			s += '</div>'
		else:
			s += '<h1>Configuración completa</h1>'
			s += '<div id="cambia">'
			s += '<a href="%s" id="cambia">básica</a>' % h.url_for(controller='config', modo='BASICA')
			s += '<br>'
			s += '<a href="%s" id="cambia">avanzada</a>' % h.url_for(controller='config', modo='AVANZADA')
			s += '</div>'
		s += '<p>%s</p>' % config['__file__']
		s += '<button id="guardar" disabled="disabled">Guardar cambios</button>'

		# mostrar todas las claves de todas las secciones (o solo las básicas)
		s += '<table border=1>'
		for section in ini:
			s2 = '<tr class="section_row"><td colspan=2><h2>%s</h2></td></tr>' % section
	##		s2 = '<tr><th colspan=2>%s</th></tr>' % section
			alguna = False
			for key, value in ini[section].iteritems():
				if modo_config == 0 and not(key.upper() in CLAVES_BASICAS): continue
				elif modo_config == 1 and not(key.upper() in CLAVES_BASICAS or key.upper() in CLAVES_AVANZADAS): continue
				alguna = True
				s2 += '<tr><td class="key_col">%s</td><td class="value_col"><input class="valor" autocomplete="off" type="text" value="%s"></td></tr>' % (key, value)
			if alguna: s += s2

		s += '</table>'

		# script jquery para:
		#   marcar los valores modificados y activar/desactivar botón
		#   evento click del botón para enviar las modificaciones
		s += '<script>'
		s += """
			$(function() {

				var modificado = false;

				$('.valor').change(function(e) {
					modificado = true;
					$('#guardar').removeAttr('disabled');
					$(this).addClass('modificado');
				});

				$('#guardar').click(function(e) {

					var v = [];

					$('.valor.modificado').each( function(a) {

						//  el parent del input es un TD, y el TD de delante tiene el nombre de la clave
						var clave = $(this).parent().prev().text();

						//  obtener la sección a la que corresponde el input
						var seccion = $(this).parent().parent().prevAll('.section_row').first().find('h2').text();

						v.push( '[' + seccion + ']' + clave + '=' + $(this).val() );
					});

					//  enviar mediante POST ajax
					v = v.join('&');
					$.ajax({
						type: 'POST',
						url: '/config/guardar',
						data: v,
						processData: false,
						//contentType: 'text/plain; charset=UTF-8',
						contentType: 'application/x-www-form-urlencoded; charset=UTF-8',
						success: function(data) {
							modificado = false;
							$('#guardar').attr('disabled', 'disabled');
							$('.valor').removeClass('modificado');
						},
						failure: function(data) {
						}
					});

				});

			});
		"""
		s += '</script>'

		s += '</body></html>'
		return s


##	def guardar(self):
##		"""
##		params:
##			__section__	 str	 nombre de la sección
##			[key]		   str		valor de la clave
##			...
##		"""
##		ini = ConfigObj(config['__file__'], list_values = False, interpolation = False)
####		ini.filename = '.'.join((config['__file__'], 'ini'))
##
##		section = request.params.get('__section__', None)
##		if section:
##			for k, v in request.params.iteritems():
##				if k == '__section__': continue
##				print k, v
##				ini[section][k] = v
##			ini.write()
	@authorize(UserIn(['sysadmin']))
	def guardar(self):
		"""
		Los parametros recibidos tienen esta forma:

			[seccion]clave=valor&[seccion]clave=valor...

		asi se permite recibir varios valores de distintas secciones.
		ojo, si no vienen EXACTAMENTE asi puede dar error...
		"""
		ini = ConfigObj(config['__file__'], list_values = False, interpolation = False)
##		ini.filename = '.'.join((config['__file__'], 'ini'))

		for k, v in request.params.iteritems():
			section = k[ 1 : k.index(']') ]
			k = k[ k.index(']')+1 : ]
			print section, k, v
			ini[section][k] = v
		ini.write()

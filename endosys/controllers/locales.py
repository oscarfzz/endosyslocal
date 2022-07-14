import logging

import os
from endosys.lib.base import *
##from pylons import config
##from datetime import date
##from configobj import ConfigObj

from authkit.authorize.pylons_adaptors import authorize
from authkit.permissions import RemoteUser, ValidAuthKitUser, UserIn, HasAuthKitRole, And

from endosys.lib.misc import *

from pylons.i18n import _, N_, set_lang

import simplejson

log = logging.getLogger(__name__)



class LocalesController(BaseController):

	def translation(self, lang="es", format="json"):
		"""
        lang    Es el lenguaje. Puede ser el languageCode o el languageCode y el countryCode. p.ej:
					es
					es-ES
				o
					en
					en-US

				ojo mays y mins!

				el lenguaje "dev" es una alternativa para desarrollo... en principio será
				lo mismo que español (es).

		format  json, po?, mo?
				El formato json deberá ser compatible con la librería i18next de javascript,
				ya que es lo que usamos en web.
				El format po/mo es el estandar usado por "gettext", que es la libreria
				usada por pylons.
				Existe una utilidad para i18next para convertir de po/mo a json
				(http://i18next.com/pages/ext_i18next-conv.html)

				OBVIAR LO DE ARRIBA... no se devuelve el PO convertido a JSON.
		"""
		#   de momento se omite el countryCode
		set_lang(lang[:2])

##		#   aqui es donde se traducen de forma "dinámica" y se añaden al resultado
##		#   que se devolverá al cliente (en principio) en formato JSON
##		data = {}
##		for s in public_locale_strings:
##			data[s] = _(s)

		# Convertir todo el catalogo (archivo MO) a JSON
		# excluir la cadena vacia, porque se asigna al header del catalog, con metadatos...
##		data = pylons.translator._catalog
		data = pylons.translator._catalog.copy()
		if '' in data: del data['']
		# ##############################################

		if format == 'json':
			response.content_type = 'application/json'
			return simplejson.dumps(data)



###   NOTA: con _N() se marcan las cadenas como traducibles, pero no se traducen...
###       de esta manera se marcan para que aparezcan en el .POT, y luego de forma
###       dinámica se traducen.
##public_locale_strings = (
### ##############################################################################
### Lista de cadenas traducibles que se usan en web
### ##############################################################################
##	N_('Atras'),
##	N_('Continuar'),
###   PACIENTES
##	N_('fin')
### ##############################################################################
##)

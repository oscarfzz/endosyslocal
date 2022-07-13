import logging

import os
from endotools.lib.base import *
from pylons import config
from datetime import date
from pylons.decorators import jsonify
from endotools.lib.misc import formatea_valor

from authkit.authorize.pylons_adaptors import authorize
from authkit.permissions import RemoteUser, ValidAuthKitUser, UserIn, HasAuthKitRole, And
from endotools.lib.usuarios.seguridad import roles

from endotools.model import meta

log = logging.getLogger(__name__)


class SqlController(BaseController):

	@jsonify
	@authorize(UserIn(['sysadmin']))
	def run(self):
		# devuelve el resultado en formato JSON (para cargar en el datatable de YUI)
		if not 'sql' in request.params:
			return {}
		sql = request.params['sql']
		log.debug(sql)
		result = meta.Session.execute(sql)

		if hasattr(result, 'keys'): # es un select
			rs = []
			for row in result:
				r = {}
				for col in result.keys: r[col] = formatea_valor( str(row[col]) )
				rs.append(r)
			return {
				'columns': [col for col in result.keys],
				'rows': rs
				}
		else:   # no es un select
			meta.Session.commit()
			return {}
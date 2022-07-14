import os
import logging
from pylons.i18n import _
from xml.etree.ElementTree import Element, SubElement, tostring

from endosys.lib.genericREST import *


from authkit.authorize.pylons_adaptors import authorize,authorized
from authkit.permissions import RemoteUser, ValidAuthKitUser, UserIn, HasAuthKitRole, And
from authkit.users.sqlalchemy_driver import UsersFromDatabase
from endosys.lib.usuarios.seguridad import roles, roles_details
from endosys.lib.misc import obj_to_xml
import simplejson

log = logging.getLogger(__name__)

class PermisosController(BaseController):

	def __init__(self, *args, **kwargs):
		BaseController.__init__(self, *args, **kwargs)

	@authorize(RemoteUser())
	def index(self, format='xml'):

		data = []
		users = request.environ['authkit.users']
		for role in users.list_roles():
			#se mostraran todos los permisos al sysadmin, usuarios con el permiso admin_server
			#en el caso de que no sea ninguno de los dos, solo se mostrarán los no restringidos
			if authorized( UserIn(['sysadmin']) ) or authorized( HasAuthKitRole(roles.admin_usuarios) ) \
			or not roles_details[role].restringido:
				data.append({
					'id': formatea_valor(role),
					'nombre': formatea_valor( roles_details[role].nombre ),
					'descripcion': formatea_valor( roles_details[role].descripcion ),
	                'restringido': formatea_valor( roles_details[role].restringido )
				})


		response.headers['cache-control'] = "no-cache, no-store, must-revalidate"
		if format == 'xml':
			response.content_type = "text/xml"
			return tostring(obj_to_xml(data, 'permiso', 'permisos'))
		elif format == 'json':
			response.content_type = 'application/json'
			return simplejson.dumps(data)


	@authorize(RemoteUser())
	def show(self, id, format='xml'):
		if format == 'xml':
			if not id in roles_details: abort_xml(404, _('El permiso no existe'), 2)#IDIOMAOK
			response.content_type = "text/xml"
			response.headers['cache-control'] = "no-cache, no-store, must-revalidate"
			root = Element('permiso')
			#   XXX comprobar antes que exista el permiso!
			SubElement(root, 'nombre').text = formatea_valor( roles_details[id].nombre )
			SubElement(root, 'descripcion').text = formatea_valor( roles_details[id].descripcion )
			return tostring(root)

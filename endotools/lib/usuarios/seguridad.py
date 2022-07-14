"""
control de permisos de acceso de los usuarios
"""

from pylons.i18n import _

# XXX
# Para que al importarse desde websetup (setup-app) no de error por la i18n...
def _(msg):
	return msg
# XXX

import logging
from pylons import config
from endotools.config.environment import load_environment

log = logging.getLogger(__name__)

class RoleDetails:

	def __init__(self, nombre, descripcion, restringido = False):
		self.nombre = nombre
		self.descripcion = descripcion
		self.restringido = restringido


class roles:
	""" Clase que solo contiene vars con los permisos disponibles
	"""

	##################################	REALIZAR EXPLORACIONES
	realizar_exploraciones = 'realizar_exploraciones'
	# implica tener el role: "consultar_citas_user" por eso ya no lo defino

	##################################	CONSULTAR EXPLORACIONES
	consultar_exploraciones_todas = 'consultar_exploraciones_todas'

	##
	modificar_exploraciones_todas = 'modificar_exploraciones_todas'
	##

	informes_exploraciones_user = "informes_exploraciones_user"
	##
	informes_exploraciones_todas = "informes_exploraciones_todas"
	##

	##################################	CITAS
	crear_modif_citas = "crear_modif_citas"
	##


	##################################	GESTION PACIENTES
	crear_modif_pacientes = "crear_modif_pacientes"
	##

	##################################	GESTION TABLAS
	crear_elementos = "crear_elementos"
	baja_elementos = "baja_elementos"

	##################################	ADMIN. USUARIOS
	admin_usuarios = "admin_usuarios"
	admin_usuarios_restringido = "admin_usuarios_restringido"  # permitir crear usuarios s?lo a partir de plantillas, sin asignar/quitar roles

	##################################	ADMIN. GENERAL
	admin_organizacion = "admin_organizacion"   # permite acceder ejecutar consultas SQL a la BBDD, acceder a los errores del server...

	##################################	ADMIN. TIPOS EXPLORACION
	admin_tipos_exploracion = "admin_tipos_exploracion"

	################################## Puede borrar, consultar borrados, y recuperar exploraciones borradas.
	borrado_logico = "borrado_logico"


roles_details = {
	roles.realizar_exploraciones:
		RoleDetails(_(u'Realizar exploraciones'),#IDIOMAOK
					_(u'Permiso que autoriza al usuario a realizar exploraciones. También hace que se muestre la opción “Nueva exploración” en el menú de la aplicación, para que esta opción esté disponible, se ha de indicar en la configuración del Endotools.')),#IDIOMAOK
	roles.consultar_exploraciones_todas:
		RoleDetails(_(u'Consultar todas las exploraciones'),#IDIOMAOK
					_(u'Permiso que autoriza a un usuario a consultar todas las exploraciones. El comportamiento por defecto, es que cada usuario solo pueda consultar solo sus exploraciones.')),#IDIOMAOK
	roles.modificar_exploraciones_todas:
		RoleDetails(_(u'Modificar todas las exploraciones'),#IDIOMAOK
					_(u'Permiso que autoriza a un usuario a modificar todas las exploraciones. El comportamiento por defecto, es que cada usuario solo puede modificar solo sus exploraciones.')),#IDIOMAOK
	roles.informes_exploraciones_user:
		RoleDetails(_(u'Informes de las exploraciones del usuario'),#IDIOMAOK
					_(u'Permiso que autoriza a un usuario a generar informes de sus propias exploraciones.')),#IDIOMAOK
	roles.informes_exploraciones_todas:
		RoleDetails(_(u'Informes de todas las exploraciones'),#IDIOMAOK
					_(u'Permiso que autoriza a un usuario a realizar informes de cualquier exploración, aunque la exploración pertenezca a otro usuario. Esta opción no da permisos para cancelar informes. Los informes solo se pueden cancelar por el médico de la exploración o el sysadmin.')),#IDIOMAOK
	roles.crear_modif_citas:
		RoleDetails(_(u'Crear y modificar citas'),#IDIOMAOK
					_(u'Permiso que autoriza al usuario a crear y modificar las citas. En el caso de que las citas estén integradas, este permiso debería estar desactivado. Para mayor seguridad, la opción “Gestión Agenda” del menú de la aplicación, desde donde se permiten crear, modificar y eliminar citas, se activa o desactiva desde la configuración de Endotools.')),#IDIOMAOK
	roles.crear_modif_pacientes:
		RoleDetails(_(u'Crear y modificar pacientes'),#IDIOMAOK
					_(u'Permiso que autoriza al usuario a crear y modificar los pacientes. En caso de que los pacientes estén integrados, este permiso debería estar desactivado. Por mayor seguridad, la gestión de pacientes se activa o desactiva desde la configuración de Endotools.')),#IDIOMAOK
	roles.crear_elementos:
		RoleDetails(_(u'Crear elementos de las tablas'),#IDIOMAOK
					_(u'Permiso que permite añadir valores a los campos tipo seleccionables o multiselección que se visualizan en los formularios, también permite añadir textos predefinidos en los campos tipo descripción (Memo) que se visualizan en los formularios.')),#IDIOMAOK
	roles.baja_elementos:
		RoleDetails(_(u'Dar de baja elementos en las tablas'),#IDIOMAOK
					_(u'Permiso que permite eliminar valores a los campos tipo seleccionables o multiselección que se visualizan en los formularios, también permite eliminar textos predefinidos en los campos tipo descripción (Memo) que se visualizan en los formularios.')),#IDIOMAOK
	roles.admin_usuarios_restringido:
		RoleDetails(_(u'Administrar usuarios restringido'),#IDIOMAOK
					_(u'Permiso que permite crear, modificar y eliminar usuarios, también permite asignar y desasignar permisos no restringidos, estos permisos son los de menor seguridad. Este permiso te permite visualizar la opción “Gestión usuarios” del menú de la aplicación.')),#IDIOMAOK
	roles.admin_usuarios:
		RoleDetails(_(u'Administrar usuarios'),#IDIOMAOK
					_(u'Permiso restringido que permite crear, modificar y eliminar usuarios, también permite asignar y desasignar permisos restringidos, estos permisos son los de mayor seguridad. Este permiso te permite visualizar la opción “Gestión usuarios” del menú de la aplicación.'), True),#IDIOMAOK
	roles.admin_organizacion:
		RoleDetails(_(u'Administrar organización'),#IDIOMAOK
					_(u'Permiso restringido que permite crear, modificar y eliminar la organización del hospital y otros parámetros de configuración de Endotools. Los parámetros a configurar desde esta opción son los siguientes: Centros, Servicios, Salas, Agendas, Motivos de cancelación y Prioridades. Este permiso te permite visualizar la opción “Administrar organización” del menú de la aplicación.'), True),#IDIOMAOK
	roles.admin_tipos_exploracion:
		RoleDetails(_(u'Administrar tipos de exploración'),#IDIOMAOK
					_(u'Permiso restringido que permite administrar los tipos de exploración y todos lo que compone un tipo de exploración: Formularios, Campos y Grupo de campos. Este permiso te permite visualizar la opción “Editor de tipos de exploración” del menú de la aplicación.'), True),#IDIOMAOK
	roles.borrado_logico:
		RoleDetails(_(u'Borrar exploraciones e informes. Consultar y recuperar exploraciones borradas'),#IDIOMAOK
					_(u'Permite a un usuario borrar exploraciones e informes realizados. Permite a un usuario Consultar y Recuperar exploraciones que ya han sido borradas.'), True),#IDIOMAOK
}

# DEPRECATED
deprecated_roles = (
	'consultar_exploraciones_user',
	'modificar_exploraciones_user',
	'importar_capturas',
	'consultar_citas_todas',
	'realizar_estadisticas_user',
	'realizar_estadisticas_todas',
	'consultar_pacientes_datos_privados',
	'exportar_capturas',
	'admin_server'
)


def delete_deprecated_roles_BBDD(users):
	log.info(_('Eliminar permisos no utilizados'))#IDIOMAOK
	usuarios = users.list_users()
	for role in deprecated_roles:
		if not users.role_exists(role): continue
		for usuario in usuarios:
			if not users.user_has_role(usuario, role): continue
			log.info(_('Quitar el permiso "%s" asignado al usuario "%s"') % (role, usuario))#IDIOMAOK
			users.user_remove_role(usuario, role)
		log.info(_('Eliminar permiso "%s"') % role)#IDIOMAOK
		users.role_delete(role)
	log.info(_('Se han eliminado los permisos no utilizados'))#IDIOMAOK


def crear_roles_BBDD(users):
	for role in filter(lambda r: not r.startswith('__') , vars(roles)):
		if not users.role_exists(role):
			users.role_create(role)

	# XXX eliminarlos, ya no se utilizan
##	if not users.role_exists("administrator"):
##		users.role_create("administrator")
##	if not users.role_exists("user"):
##		users.role_create("user")

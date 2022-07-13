# info. adicional a la tabla users

import sqlalchemy as sa
from sqlalchemy import orm

from endotools.model import meta

t_usuarios = sa.Table("Usuarios", meta.metadata,
    sa.Column("username", sa.types.String(255), sa.ForeignKey('users.username'), primary_key=True),
    sa.Column("ldap", sa.types.Boolean),
    sa.Column("activo", sa.types.Boolean, nullable=True, default=True),
    sa.Column("tipo", sa.types.Integer, nullable=True, default=0), # 0 (medico) | 1 (administrador)
	sa.Column("clave", sa.types.String(255), nullable=True)
)

class Usuario(object):
    pass

orm.mapper(Usuario, t_usuarios)

def get_usuario(**kwargs):
	"""
	obtiene un registro 'Usuario' a partir del username.
	el username se ha de pasar como keyword argument, ejem: username="admin".
	"""

	q = meta.Session.query(Usuario)
	if 'username' in kwargs:
		q = q.filter( Usuario.username == kwargs['username'] )
	else:
		raise Exception(u'la funcion "get_usuario" debe tener 1 solo parametro "username"')
	if q.count():
		return q.one()
	else:
		return None
'''
id
codigo
nombre
'''

import sqlalchemy as sa
from sqlalchemy import orm
from sqlalchemy.orm import relation, backref

from endosys.model import meta

t_centros = sa.Table("Centros", meta.metadata,
	sa.Column("id", sa.types.Integer, sa.schema.Sequence('secuencia_centros'), primary_key=True),
	sa.Column("codigo", sa.types.String(50), nullable=True),   # de uso para integraciones
	sa.Column("nombre", sa.types.String(50), nullable=False),
	useexisting=True
	)

class Centro(object):
	pass

orm.mapper(Centro, t_centros)

def get_centro(**kwargs):
	"""
	obtiene un registro 'Centro' a partir del codigo.
	el codigo se ha de pasar como keyword argument, ejem: codigo="CHUS".
	"""
	q = meta.Session.query(Centro)
	if 'codigo' in kwargs:
		q = q.filter( Centro.codigo == kwargs['codigo'] )
	else:
		raise Exception(u'la función "get_centro" debe tener 1 solo parámetro "codigo"')


	if q.count():
		return q.one()
	else:
		return None


def get_centro_id(**kwargs):
	"""
	igual que el anterior, pero devuelve el id o None
	"""
	centro = get_centro(**kwargs)
	if centro:
		return centro.id
	else:
		return None

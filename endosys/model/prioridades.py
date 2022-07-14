

import sqlalchemy as sa
from sqlalchemy import orm

from endosys.model import meta


t_Prioridades = sa.Table("Prioridades", meta.metadata,
    sa.Column("id", sa.types.Integer,  sa.schema.Sequence('secuencia_Prioridades'), primary_key=True),
    sa.Column("codigo", sa.types.String(50), nullable=True),
    sa.Column("nombre", sa.types.String(50), nullable=True),
    sa.Column("nivel", sa.types.Integer, nullable=True)
    )

class Prioridad(object):
    pass

orm.mapper(Prioridad, t_Prioridades)

def prioridad_by_codigo(codigo):
	"""
	obtiene el registro prioridad segun el codigo de la prioridad
	"""
	if codigo == None: return None
	
	q = meta.Session.query(Prioridad).filter(Prioridad.codigo == codigo)
	if q.count():
		return q.one()
	else:
		return None

def prioridad_id_by_codigo(codigo):
	"""
	obtiene el id del registro prioridad segun el codigo de la prioridad
	"""
	prioridad = prioridad_by_codigo(codigo)
	if prioridad:
		return prioridad.id
	else:
		return None

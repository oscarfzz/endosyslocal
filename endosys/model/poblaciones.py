

import sqlalchemy as sa
from sqlalchemy import orm

from endosys.model import meta


t_Poblaciones = sa.Table("Poblaciones", meta.metadata,
    sa.Column("id", sa.types.Integer,  sa.schema.Sequence('secuencia_Poblaciones'), primary_key=True),
    sa.Column("codigo", sa.types.String(20), nullable=True),
    sa.Column("nombre", sa.types.String(75), nullable=True)
    )

class Poblacion(object):
    pass

orm.mapper(Poblacion, t_Poblaciones)

def poblacion_nombre_by_codigo(codigo):
	"""
	obtiene el registro poblacion segun el codigo de la poblacion
	"""
	if codigo == None: return None
	q = meta.Session.query(Poblacion).filter(Poblacion.codigo == codigo)
	if q.count():
		return q.one().nombre
	else:
		return None

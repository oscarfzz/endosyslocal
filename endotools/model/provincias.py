

import sqlalchemy as sa
from sqlalchemy import orm

from endotools.model import meta


t_Provincias = sa.Table("Provincias", meta.metadata,
    sa.Column("id", sa.types.Integer,  sa.schema.Sequence('secuencia_Provincias'), primary_key=True),
    sa.Column("codigo", sa.types.String(20), nullable=True),
    sa.Column("nombre", sa.types.String(50), nullable=True)
    )

class Provincia(object):
    pass

orm.mapper(Provincia, t_Provincias)

def provincia_nombre_by_codigo(codigo):
	"""
	obtiene el registro provincia segun el codigo de la provincia
	"""
	if codigo == None: return None

	q = meta.Session.query(Provincia).filter(Provincia.codigo == codigo)
	if q.count():
		return q.one().nombre
	else:
		return None

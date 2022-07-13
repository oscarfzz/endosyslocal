

import sqlalchemy as sa
from sqlalchemy import orm

from endotools.model import meta


t_MotivosCancelacion = sa.Table("MotivosCancelacion", meta.metadata,
    sa.Column("id", sa.types.Integer,  sa.schema.Sequence('secuencia_MotivosCancelacion'), primary_key=True),
    sa.Column("codigo", sa.types.String(50), nullable=True),
    sa.Column("nombre", sa.types.String(50), nullable=True)
    )

class MotivoCancelacion(object):
    pass

orm.mapper(MotivoCancelacion, t_MotivosCancelacion)

def motivo_by_id(id):
	"""
	obtiene el nombre de un motivo a partir de su Id
	si el id es None o no se encuentra, devuelve None
	"""
	
	q = meta.Session.query(MotivoCancelacion).filter(MotivoCancelacion.id == id)
	if q.count():
		return q.one().nombre
	else:
		return None


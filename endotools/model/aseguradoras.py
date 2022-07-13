import sqlalchemy as sa
from sqlalchemy import orm

from endotools.model import meta

t_aseguradoras = sa.Table("Aseguradoras", meta.metadata,
    sa.Column("id", sa.types.Integer, sa.schema.Sequence('secuencia_aseguradoras'), primary_key=True),
    sa.Column("nombre", sa.types.String(50), nullable=False),
    sa.Column("activo", sa.types.Boolean, nullable=True)
    )

class Aseguradora(object):
    pass

orm.mapper(Aseguradora, t_aseguradoras)

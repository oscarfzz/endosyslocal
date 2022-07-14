'''
id
nombre
'''

import sqlalchemy as sa
from sqlalchemy import orm

from endosys.model import meta

t_gruposCampos = sa.Table("GruposCampos", meta.metadata,
    sa.Column("id", sa.types.Integer, sa.schema.Sequence('secuencia_gruposcampos'), primary_key=True),
    sa.Column("nombre", sa.types.String(50), nullable=False),
    sa.Column("columnas", sa.types.Integer, nullable=False)
    )

class GrupoCampos(object):
    pass

orm.mapper(GrupoCampos, t_gruposCampos)

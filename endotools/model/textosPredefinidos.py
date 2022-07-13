'''
id
nombre
'''

import sqlalchemy as sa
from sqlalchemy import orm, ForeignKey
from sqlalchemy.orm import relation, backref

from endotools.model import meta, Campo

t_textosPredefinidos = sa.Table("TextosPredefinidos", meta.metadata,
    sa.Column("id", sa.types.Integer, sa.schema.Sequence('secuencia_textospredef'), primary_key=True),
    sa.Column("campo_id", sa.types.Integer, nullable=True),
    sa.Column("nombre", sa.types.String(128), nullable=False),
    sa.Column("texto", sa.types.Text, nullable=True),
  #  sa.Column("nombre", sa.types.Unicode(128), nullable=False),
   # sa.Column("texto", sa.types.UnicodeText, nullable=True),
    sa.Column("activo", sa.types.Boolean, nullable=True)
    )

class TextoPredefinido(object):
    pass

orm.mapper(TextoPredefinido, t_textosPredefinidos)

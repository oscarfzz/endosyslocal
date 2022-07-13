'''
id
nombre
'''

import sqlalchemy as sa
from sqlalchemy import orm, ForeignKey
from sqlalchemy.orm import relation, backref

from endotools.model import meta, Campo, Servicio

t_elementos = sa.Table("Elementos", meta.metadata,
    sa.Column("id", sa.types.Integer, sa.schema.Sequence('secuencia_elementos'), primary_key=True),
    sa.Column("campo_id", sa.types.Integer, sa.ForeignKey('Campos.id')),
    sa.Column("codigo", sa.types.String(50), nullable=True),
    sa.Column("nombre", sa.types.String(1000), nullable=False),
    sa.Column("activo", sa.types.Boolean, nullable=False),
    sa.Column("orden", sa.types.Integer, nullable=True),
    sa.Column("servicio_id", sa.types.Integer, sa.ForeignKey('Servicios.id'), nullable=True),
    )

class Elemento(object):
    pass

orm.mapper(Elemento, t_elementos, properties = {
    "campo": orm.relation(Campo, backref=backref('elementos', viewonly=True, order_by='id')),
    "servicio": orm.relation(Servicio, backref=backref('elementos', viewonly=True, order_by='id'))
    })

# -*- coding: utf-8 -*-
'''
id
descripcion
xml
'''

import sqlalchemy as sa
from sqlalchemy import orm, ForeignKey
from sqlalchemy.orm import relation, backref

from endosys.model import meta

# Niveles de acceso a las búsquedas:
#   0: público global (accesible desde todo el mundo y en todos los servicios)
#   1: público de servicio (accesible desde usuarios conectados a un servicio concreto)
#   2: protegido global (accesible desde todo el mundo *y en todos los servicios*, editable solo por el propietario)
#   3: protegido de servicio (accesible desde usuarios conectados a un servicio concreto, *editable solo por el propietario*)
#   4: privada (solo accesible *y editable por* el propietario que esta definido en la tabla como username)

t_busquedas = sa.Table("Busquedas", meta.metadata,
    sa.Column("id", sa.types.Integer, sa.schema.Sequence('secuencia_busquedas'), primary_key=True),
    sa.Column("descripcion", sa.types.String(128), nullable=False),
    sa.Column("xml", sa.types.Text, nullable=True),
    sa.Column("nivel", sa.types.Integer, nullable=True),
    sa.Column("username", sa.types.String(255), sa.ForeignKey('users.username'), nullable=True),
    sa.Column("servicio_id", sa.types.Integer, sa.ForeignKey('Servicios.id'), nullable=True),
    sa.Column("comentario", sa.types.Text, nullable=True)
    )

class Busqueda(object):
    pass

orm.mapper(Busqueda, t_busquedas)

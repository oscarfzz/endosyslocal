'''
Cada sala pertenece a un solo centro, y puede pertenecer a varios
servicios (de ese centro).

Cada sala puede pertenecer a varias agendas (las agendas deben estar asignadas
a servicios a los que pertenezca la sala)
'''

import sqlalchemy as sa
from sqlalchemy import orm
from sqlalchemy.orm import relation, backref

from endosys.model import meta, Centro, Servicio, Agenda

t_salas = sa.Table("Salas", meta.metadata,
    sa.Column("id", sa.types.Integer,  sa.schema.Sequence('secuencia_salas'), primary_key=True),
    sa.Column("nombre", sa.types.String(50), nullable=False),
	sa.Column("centro_id", sa.types.Integer, sa.ForeignKey('Centros.id'))
    )

t_rel_Salas_Servicios = sa.Table("rel_Salas_Servicios", meta.metadata,
    sa.Column("servicio_id", sa.types.Integer, sa.ForeignKey('Servicios.id'), primary_key=True),
    sa.Column("sala_id", sa.types.Integer, sa.ForeignKey('Salas.id'), primary_key=True)
    )

t_rel_Salas_Agendas = sa.Table("rel_Salas_Agendas", meta.metadata,
    sa.Column("agenda_id", sa.types.Integer, sa.ForeignKey('Agendas.id'), primary_key=True),
    sa.Column("sala_id", sa.types.Integer, sa.ForeignKey('Salas.id'), primary_key=True)
    )


class Sala(object):
    pass

class Rel_Salas_Servicios(object):
    pass

class Rel_Salas_Agendas(object):
    pass


orm.mapper(Sala, t_salas, properties = {
    "centro": orm.relation(Centro, backref=backref('salas', viewonly=True, order_by='id')),
    'servicios': orm.relation(Rel_Salas_Servicios, viewonly=True, backref = "sala"),
    'agendas': orm.relation(Rel_Salas_Agendas, viewonly=True, backref = "sala")
})

orm.mapper(Rel_Salas_Servicios, t_rel_Salas_Servicios, properties={
    'servicio': orm.relation(Servicio, backref = backref("salas", viewonly=True))
})

orm.mapper(Rel_Salas_Agendas, t_rel_Salas_Agendas, properties={
    'agenda': orm.relation(Agenda, backref = backref("salas", viewonly=True))
})

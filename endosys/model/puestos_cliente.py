'''
Registro de puestos cliente de EndoSys que se han conectado en alguna ocasión,
identificados por la IP.

Para poder guardar una configuración de un equipo cliente debería estar
configurado con una IP estática.

ip              la IP es también la clave primaria
host            opcionalmente se puede guardar el nombre de host

agenda_id       agenda, servicio y centro por defecto del cliente. Se utilizan
servicio_id     en ese orden de preferencia, según si tienen valor asignado y
centro_id       si el usuario dispone de la agenda o servicio. Se usa por ejemplo
				en Citas Pendientes.
'''

import sqlalchemy as sa
from sqlalchemy import orm
from sqlalchemy.orm import relation, backref

from endosys.model import meta, Centro, Servicio, Agenda

t_puestos_cliente = sa.Table("Puestos_cliente", meta.metadata,
    sa.Column("ip",			sa.types.String(50), primary_key=True), # prever funcionamiento con IPV6
    sa.Column("host",		sa.types.String(50), nullable=True),
    sa.Column("agenda_id",	sa.types.Integer,	sa.ForeignKey('Agendas.id'), nullable=True),
    sa.Column("servicio_id", sa.types.Integer,	sa.ForeignKey('Servicios.id'), nullable=True),
    sa.Column("centro_id",	sa.types.Integer,	sa.ForeignKey('Centros.id'), nullable=True)
)


class Puesto_cliente(object):
    pass

orm.mapper(Puesto_cliente, t_puestos_cliente, properties = {
    "agenda":	orm.relation(Agenda, backref=backref('puestos_cliente', viewonly=True, order_by='ip')),
    "servicio": orm.relation(Servicio, backref=backref('puestos_cliente', viewonly=True, order_by='ip')),
    "centro":	orm.relation(Centro, backref=backref('puestos_cliente', viewonly=True, order_by='ip')),
})

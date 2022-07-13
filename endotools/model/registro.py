
import sqlalchemy as sa
from sqlalchemy import orm, ForeignKey
from sqlalchemy.orm import relation, backref

from endotools.model import meta, Paciente, Exploracion, Hl7_log, Workstation

t_registro = sa.Table("Registro", meta.metadata,
	# info sobre registro
    sa.Column("id",				sa.types.Integer,	sa.schema.Sequence('secuencia_registro'), primary_key=True),
    sa.Column("username",		sa.types.String(255), sa.ForeignKey('users.username'), nullable=False),
    sa.Column("ip",				sa.types.String(20), nullable=False),
    sa.Column("hostname",		sa.types.String(128), nullable=True),

    sa.Column("fechahora",		sa.types.DateTime,	nullable=False),    # se guardara la fecha Y la hora. Tanto en SQLServer (tipo DateTime) como en Oracle (tipo DATE) se puede

	# qué suceso se registro
    sa.Column("evento",			sa.String(15),		nullable=False),    # MODIFICAR, CREAR, ELIMINAR, MOSTRAR

	# data
    sa.Column("res",			sa.String(64),		nullable=False),    # identificador del recurso al que pertenece el dato: PACIENTE, EXPLORACION, CAPTURA, INFORME...
    sa.Column("data",			sa.String(64),		nullable=True),     # identificador del dato que se registra (nombre de campo, etc...) (puede ser NULL en el caso de creacion, eliminacion...)
    sa.Column("old",			sa.Text,			nullable=True),     # valor anterior del dato (puede ser NULL)
    sa.Column("new",			sa.Text,			nullable=True),     # valor nuevo del dato (puede ser NULL)

	# datos obtenibles a traves de los ids, pero importantes para ver directamente
	#sa.Column("nhc",			sa.String(50),		nullable=False),
    sa.Column("idunico",			sa.String(50),		nullable=True),
    sa.Column("nhc_centro",			sa.String(50),		nullable=True),
    sa.Column("centro_id",          sa.types.Integer,   sa.ForeignKey('Centros.id'), nullable=True),

	# ids
##    sa.Column("paciente_id",	sa.types.Integer,	sa.ForeignKey('Pacientes.id'), nullable=False),
    sa.Column("paciente_id",	sa.types.Integer,	nullable=False), # XXX he quitado el foreign key porque impide borrar el paciente cuando hay una fusion... revisar esto! XXX
    sa.Column("exploracion_id",	sa.types.Integer,	sa.ForeignKey('Exploraciones.id'), nullable=True),	# en principio siempre se registrarán sucesos que
    																									# afecten a datos de una exploracion y paciente.
																										# "exploracion_id" puede ser NULL, para registrar p.ej. acceso a datos de paciente
    sa.Column("hl7_log_id", sa.types.Integer, sa.ForeignKey('Hl7_logs.id'), nullable=True),
    sa.Column("workstation_id", sa.types.Integer,   sa.ForeignKey('Workstations.id'), nullable=True),
    )

class Registro(object):
    pass

orm.mapper(Registro, t_registro, properties = {
##    "paciente": orm.relation(Paciente, backref=backref('registros', order_by='id')),
    "exploracion": orm.relation(Exploracion, backref=backref('registros', viewonly=True, order_by='id')),
    "hl7_log": orm.relation(Hl7_log, backref=backref('registros', viewonly=True, order_by='id')),
    "workstation": orm.relation(Workstation, backref=backref('registros', viewonly=True, order_by='id')),
    })

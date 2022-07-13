import sqlalchemy as sa
from sqlalchemy import orm, ForeignKey
from sqlalchemy.orm import relation, backref

from endotools.model import meta



t_hl7_logs = sa.Table("Hl7_logs", meta.metadata,
	sa.Column("id", sa.types.Integer, sa.schema.Sequence('secuencia_hl7_logs'), primary_key=True),
	sa.Column("fechahora", sa.types.DateTime, nullable=True),
	sa.Column("sender",		sa.types.String(128), nullable=True),
	sa.Column("tipo_mensaje",			sa.String(7),		nullable=True),
	sa.Column("message_control_id",		sa.types.String(128), nullable=True),
	#sa.Column("nhc", sa.types.String(50), nullable=True),
	sa.Column("idunico",			sa.String(50),		nullable=True),
	sa.Column("cip", sa.types.String(50), nullable=True),
	sa.Column("numero_cita", sa.types.String(50), nullable=True),
	sa.Column("numero_peticion", sa.types.String(50), nullable=True),
	sa.Column("hl7_msg", sa.types.Text, nullable=True),
	sa.Column("exploracion_id", sa.types.Integer, sa.ForeignKey('Exploraciones.id'), nullable=True),
	sa.Column("canal", sa.types.String(50), nullable=True), #INPUT / OUTPUT
	sa.Column("estado_envio", sa.types.Integer, nullable=True) # 0 - EN CURSO, 1 - ENVIADO, 2 - ERROR

	)

class Hl7_log(object):
	pass

orm.mapper(Hl7_log, t_hl7_logs)


import sqlalchemy as sa
from sqlalchemy import orm, ForeignKey
from sqlalchemy.orm import relation, backref

from endotools.model import meta, Aseguradora

# NOTA:	Tomamos como convención que los campos de tipo Date son fechas y los de
#	   tipo DateTime son horas, aunque en BBDD se guarden ambos como DATETIME.

t_fusiones = sa.Table("Fusiones", meta.metadata,
	sa.Column("id", sa.types.Integer, sa.schema.Sequence('secuencia_fusiones'), primary_key=True),
	#sa.Column("nhc_origen", sa.String(50), nullable=True),
	#sa.Column("nhc_destino", sa.String(50), nullable=True),
	sa.Column("id_origen", sa.String(50), nullable=True),
	sa.Column("id_destino", sa.String(50), nullable=True),
	#sa.Column("cip_origen", sa.String(50), nullable=True),
	#sa.Column("cip_destino", sa.String(50), nullable=True),
	sa.Column("idunico_origen", sa.String(50), nullable=True),
	sa.Column("idunico_destino", sa.String(50), nullable=True),
	sa.Column("day_insert", sa.types.Date, nullable=True),
	sa.Column("hour_insert", sa.types.DateTime, nullable=True)
	)

class Fusion(object):
	pass

orm.mapper(Fusion, t_fusiones)

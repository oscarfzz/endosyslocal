import sqlalchemy as sa
from sqlalchemy import orm, ForeignKey
from sqlalchemy.orm import relation, backref
from endotools.model import meta, Usuario

t_notificaciones = sa.Table("Notificaciones", meta.metadata,
	sa.Column("id", sa.types.Integer, sa.schema.Sequence('secuencia_notificaciones'), primary_key=True),
	sa.Column("username_origen", sa.types.String(255), sa.ForeignKey('users.username'), nullable=True),
	sa.Column("username_destino", sa.types.String(255), sa.ForeignKey('users.username'), nullable=False),
	sa.Column("fecha", sa.types.Date, nullable=False),
	sa.Column("hora", sa.types.DateTime, nullable=False),
	sa.Column("tipo_notificacion", sa.types.String(10), nullable=False),
	sa.Column("contenido", sa.types.String(1000), nullable=False),
	sa.Column("meta_informacion", sa.types.String(1000), nullable=True),
	sa.Column("leida", sa.types.Boolean, nullable=False, default=False),
	sa.Column("importante", sa.types.Boolean, nullable=False, default=False),
	sa.Column("eliminada", sa.types.Boolean, nullable=False, default=False)
	)

class Notificacion(object):
	pass

orm.mapper(Notificacion, t_notificaciones)
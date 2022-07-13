import sqlalchemy as sa
from sqlalchemy import orm, ForeignKey
from sqlalchemy.orm import relation, backref
from endotools.model import meta, Usuario

t_tareas = sa.Table("Tareas", meta.metadata,
	sa.Column("id", sa.types.Integer, sa.schema.Sequence('secuencia_tareas'), primary_key=True),
	sa.Column("fecha_comienzo", sa.types.Date, nullable=False),
	sa.Column("hora_comienzo", sa.types.DateTime, nullable=False),
	sa.Column("fecha_fin", sa.types.Date, nullable=True),
	sa.Column("hora_fin", sa.types.DateTime, nullable=True),
	sa.Column("tipo_tarea", sa.types.String(10), nullable=False), #EXP: exportaciones
	sa.Column("username", sa.types.String(255), sa.ForeignKey('users.username'), nullable=False),
	sa.Column("descripcion", sa.types.String(255), nullable=True),
	sa.Column("resultado", sa.types.String(255), nullable=True),
	sa.Column("resultado_descripcion", sa.types.String(1000), nullable=True),
	sa.Column("estado", sa.types.Integer, nullable=False),
	sa.Column("descargable", sa.types.Boolean, nullable=True),
	sa.Column("eliminada", sa.types.Boolean, nullable=False, default=False)
	)

class Tarea(object):
	pass

orm.mapper(Tarea, t_tareas)
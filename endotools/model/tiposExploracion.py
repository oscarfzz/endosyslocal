import sqlalchemy as sa
from sqlalchemy import orm
from sqlalchemy.orm import relation, backref

from endotools.model import meta, GrupoCampos, Formulario, Servicio
##from endotools.model.campos import Campo

t_tiposExploracion = sa.Table("TiposExploracion", meta.metadata,
    sa.Column("id", sa.types.Integer, sa.schema.Sequence('secuencia_tiposexpl'), primary_key=True),
    sa.Column("codigo", sa.types.String(50), nullable=True),
    # NO SE USA MAS EN 2.4.10. Aunque todavia sigue en el modelo porque sirve para hacer la migracion de datos
    # cuando se actualiza a la 2.4.10 ya que si hay datos en este campo, se crea un registro en la BD de relacion.
    # y si es un null, para ese tipo de exploracion se crean tantas relaciones como servicios haya.
    sa.Column("servicio_id", sa.types.Integer, sa.ForeignKey('Servicios.id'), nullable=True),
    sa.Column("nombre", sa.types.String(50), nullable=False),
    sa.Column("color", sa.types.String(50), nullable=False),
    sa.Column("activo", sa.types.Boolean, nullable=False),
    sa.Column("orden", sa.types.Integer, nullable=True),
    sa.Column("duracion", sa.types.Integer, nullable=True, default=0),
    )

#t_rel_Formularios_TiposExploracion = sa.Table('rel_Formularios_TiposExploracion', meta.metadata,
t_rel_Formularios_TiposExploracion = sa.Table('rel_Forms_TiposExpl', meta.metadata,    # XXX ORACLE: El nombre de tabla "rel_Formularios_TiposExploracion" es demasiado largo
    sa.Column('tipoExploracion_id', sa.types.Integer, sa.ForeignKey('TiposExploracion.id'), primary_key=True),
    sa.Column('formulario_id', sa.types.Integer, sa.ForeignKey('Formularios.id'), primary_key=True),
    sa.Column('orden', sa.types.Integer),
    sa.Column('predefinido', sa.types.Boolean)
    )

t_rel_Servicios_TiposExploracion = sa.Table("rel_Serv_TiposExpl", meta.metadata,
    sa.Column("servicio_id", sa.types.Integer, sa.ForeignKey('Servicios.id'), primary_key=True),
    sa.Column("tipoExploracion_id", sa.types.Integer, sa.ForeignKey('TiposExploracion.id'), primary_key=True),
)

##t_rel_Campos_TiposExploracion = sa.Table("rel_Campos_TiposExploracion", meta.metadata,
##    sa.Column("campo_id", sa.types.Integer, sa.ForeignKey('Campos.id'), primary_key=True),
##    sa.Column("tipoExploracion_id", sa.types.Integer, sa.ForeignKey('TiposExploracion.id'), primary_key=True),
##    sa.Column("orden", sa.types.Integer, nullable=False),
##    sa.Column("grupoCampos_id", sa.types.Integer, sa.ForeignKey('GruposCampos.id'), primary_key=True),
##    )

class TipoExploracion(object):
    pass

class Rel_Formularios_TiposExploracion(object):
    pass

class Rel_Servicios_TiposExploracion(object):
    pass

orm.mapper(Rel_Formularios_TiposExploracion, t_rel_Formularios_TiposExploracion, properties={
    'formulario': orm.relation(Formulario, backref = backref("tiposExploracion", viewonly=True, order_by="orden"))
})


orm.mapper(Rel_Servicios_TiposExploracion, t_rel_Servicios_TiposExploracion, properties={
    'servicio': orm.relation(Servicio, backref = backref('tiposExploracion', viewonly=True))
})


orm.mapper(TipoExploracion, t_tiposExploracion, properties={
    'formularios': orm.relation(Rel_Formularios_TiposExploracion, viewonly=True, backref = "tipoExploracion", order_by='orden'),
    'servicios': orm.relation(Rel_Servicios_TiposExploracion, viewonly=True, backref = "tipoExploracion"),
})


##mapper(Child, right_table)



# http://www.sqlalchemy.org/docs/05/mappers.html#association-object


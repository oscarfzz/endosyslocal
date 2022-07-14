import sqlalchemy as sa
from sqlalchemy import orm, ForeignKey
from sqlalchemy.orm import relation, backref

from endosys.model import meta, Campo, GrupoCampos

t_formularios = sa.Table("Formularios", meta.metadata,
    sa.Column("id", sa.types.Integer, sa.schema.Sequence('secuencia_formularios'), primary_key=True),
    sa.Column("titulo", sa.types.String(50)),
    )

t_rel_Campos_Formularios = sa.Table("rel_Campos_Formularios", meta.metadata,
    sa.Column("formulario_id", sa.types.Integer, sa.ForeignKey('Formularios.id'), primary_key=True),
    sa.Column("grupoCampos_id", sa.types.Integer, sa.ForeignKey('GruposCampos.id'), primary_key=True),
    sa.Column("campo_id", sa.types.Integer, sa.ForeignKey('Campos.id'), primary_key=True),
    sa.Column("orden", sa.types.Integer, nullable=False),
    sa.Column("ancho", sa.types.Integer, nullable=False),
    sa.Column("alto", sa.types.Integer, nullable=False),
    sa.Column("posx", sa.types.Integer, nullable=False),
    sa.Column("posy", sa.types.Integer, nullable=False),
    sa.Column("campo_rel_id", sa.types.Integer, nullable=True)
)

t_rel_GruposCampos_Formularios = sa.Table("rel_GruposCampos_Formularios", meta.metadata,
    sa.Column("formulario_id", sa.types.Integer, sa.ForeignKey('Formularios.id'), primary_key=True),
    sa.Column("grupoCampos_id", sa.types.Integer, sa.ForeignKey('GruposCampos.id'), primary_key=True),
##    sa.Column("columnas", sa.types.Integer, nullable=False),
    sa.Column("orden", sa.types.Integer, nullable=False)
    )

# de esta forma se asignan distintos valores por defecto a los campos para cada formulario.
t_valoresPorDefecto = sa.Table("ValoresPorDefecto", meta.metadata,
    sa.Column("formulario_id", sa.types.Integer, sa.ForeignKey('Formularios.id'), primary_key=True),
    sa.Column("campo_id", sa.types.Integer, sa.ForeignKey('Campos.id'), primary_key=True),
    sa.Column("valor", sa.types.String(1000), nullable=False)
    )


class Formulario(object):
    pass

class Rel_Campos_Formularios(object):
    pass

class Rel_GruposCampos_Formularios(object):
    pass

class ValorPorDefecto(object):
    pass

orm.mapper(Formulario, t_formularios, properties={
    'campos': orm.relation(Rel_Campos_Formularios, backref = "formulario", order_by = [t_rel_Campos_Formularios.c.grupoCampos_id, t_rel_Campos_Formularios.c.orden]),
    'valoresPorDefecto': orm.relation(ValorPorDefecto, backref = "formulario", order_by = [t_valoresPorDefecto.c.campo_id]),
    'gruposCampos': orm.relation(Rel_GruposCampos_Formularios, backref = "formulario", order_by = [t_rel_GruposCampos_Formularios.c.orden])
})

orm.mapper(Rel_Campos_Formularios, t_rel_Campos_Formularios, properties={
    "campo": orm.relation(Campo, viewonly=True, backref = backref('formularios', viewonly=True)),
    "grupoCampos": orm.relation(GrupoCampos),
})

orm.mapper(Rel_GruposCampos_Formularios, t_rel_GruposCampos_Formularios, properties={
    'grupoCampos': orm.relation(GrupoCampos, backref = backref('formularios', viewonly=True))
})

orm.mapper(ValorPorDefecto, t_valoresPorDefecto, properties={
##    'campo': orm.relation(Campo, backref = "...")
    'campo': orm.relation(Campo)
})

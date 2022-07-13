#   todas las tablas que almacenan los valores de los campos en cada exploracion realizada
#   cada tipo de campo almacena sus valores en una tabla distinta

import sqlalchemy as sa
from sqlalchemy import orm, ForeignKey, ForeignKeyConstraint
from sqlalchemy.orm import relation, backref
from sqlalchemy.sql import and_

from endotools.model import meta, Campo, Elemento, Rel_Formularios_Exploraciones
from endotools.model.exploraciones import t_rel_Formularios_Exploraciones
from endotools.model import Exploracion, Formulario


# campos de tipo texto (Campos.tipo = 1 y 5)
t_valoresTexto = sa.Table("ValoresTexto", meta.metadata,
    sa.Column("exploracion_id", sa.types.Integer, sa.ForeignKey('Exploraciones.id'), primary_key=True),
    sa.Column("formulario_id", sa.types.Integer, sa.ForeignKey('Formularios.id'), primary_key=True),
    sa.Column("campo_id", sa.types.Integer, sa.ForeignKey('Campos.id'), primary_key=True),
    sa.Column("valor", sa.types.Text(4000), nullable=True),
    ForeignKeyConstraint(['exploracion_id', 'formulario_id'], ['rel_Formularios_Exploraciones.exploracion_id', 'rel_Formularios_Exploraciones.formulario_id'])  # con ForeignKeyConstraint se pueden crear foreignkeys a tablas con mas de una primarykey
    )

# campos de tipo lista seleccionable (Campos.tipo = 2)
t_valoresSelec = sa.Table("ValoresSelec", meta.metadata,
    sa.Column("exploracion_id", sa.types.Integer, sa.ForeignKey('Exploraciones.id'), primary_key=True),
    sa.Column("formulario_id", sa.types.Integer, sa.ForeignKey('Formularios.id'), primary_key=True),
    sa.Column("campo_id", sa.types.Integer, sa.ForeignKey('Campos.id'), primary_key=True),
    sa.Column("elemento_id", sa.types.Integer, sa.ForeignKey('Elementos.id'), nullable=True),# primary_key=True
    ForeignKeyConstraint(['exploracion_id', 'formulario_id'], ['rel_Formularios_Exploraciones.exploracion_id', 'rel_Formularios_Exploraciones.formulario_id'])
    )

# campos de tipo multiseleccion (Campos.tipo = 3)
t_valoresMulti = sa.Table("ValoresMulti", meta.metadata,
    sa.Column("exploracion_id", sa.types.Integer, sa.ForeignKey('Exploraciones.id'), primary_key=True),
    sa.Column("formulario_id", sa.types.Integer, sa.ForeignKey('Formularios.id'), primary_key=True),
    sa.Column("campo_id", sa.types.Integer, sa.ForeignKey('Campos.id'), primary_key=True),
    sa.Column("elemento_id", sa.types.Integer, sa.ForeignKey('Elementos.id'), primary_key=True),
    sa.Column("orden", sa.types.Integer, nullable=True),
    sa.Column("cantidad", sa.types.Integer, nullable=True,default=1),
    ForeignKeyConstraint(['exploracion_id', 'formulario_id'], ['rel_Formularios_Exploraciones.exploracion_id', 'rel_Formularios_Exploraciones.formulario_id'])
    )

# campos de tipo booleano (Campos.tipo = 4)
t_valoresBool = sa.Table("ValoresBool", meta.metadata,
    sa.Column("exploracion_id", sa.types.Integer, sa.ForeignKey('Exploraciones.id'), primary_key=True),
    sa.Column("formulario_id", sa.types.Integer, sa.ForeignKey('Formularios.id'), primary_key=True),
    sa.Column("campo_id", sa.types.Integer, sa.ForeignKey('Campos.id'), primary_key=True),
    sa.Column("valor", sa.types.Boolean, nullable=True, default=False),
    ForeignKeyConstraint(['exploracion_id', 'formulario_id'], ['rel_Formularios_Exploraciones.exploracion_id', 'rel_Formularios_Exploraciones.formulario_id'])
    )

class ValorTexto(object):
    pass

class ValorSelec(object):
    pass

class ValorMulti(object):
    pass

class ValorBool(object):
    pass

orm.mapper(ValorTexto, t_valoresTexto, properties = {
    "rel_formularios_exploraciones": orm.relation(Rel_Formularios_Exploraciones,
                primaryjoin = and_(t_valoresTexto.c.exploracion_id == t_rel_Formularios_Exploraciones.c.exploracion_id,
                                    t_valoresTexto.c.formulario_id == t_rel_Formularios_Exploraciones.c.formulario_id),
                backref = backref('valoresTexto', order_by='exploracion_id')),
    "exploracion":	orm.relation(Exploracion, backref=backref('valoresTexto', viewonly=True, order_by='campo_id')), # de hecho, podria ser valorTexto, y poner uselist=False...
    "formulario":	orm.relation(Formulario, backref=backref('valoresTexto', viewonly=True, order_by='campo_id')),
    "campo":		orm.relation(Campo, backref=backref('valoresTexto', viewonly=True, order_by='exploracion_id'))
    })

orm.mapper(ValorSelec, t_valoresSelec, properties = {
    "rel_formularios_exploraciones": orm.relation(Rel_Formularios_Exploraciones,
                primaryjoin = and_(t_valoresSelec.c.exploracion_id == t_rel_Formularios_Exploraciones.c.exploracion_id,
                                    t_valoresSelec.c.formulario_id == t_rel_Formularios_Exploraciones.c.formulario_id),
                backref = backref('valoresSelec', order_by='exploracion_id')),
    "exploracion":	orm.relation(Exploracion, backref=backref('valoresSelec', viewonly=True, order_by='campo_id')), # de hecho, podria ser valorSelec, y poner uselist=False...
    "formulario":	orm.relation(Formulario, backref=backref('valoresSelec', viewonly=True, order_by='campo_id')),
    "campo":		orm.relation(Campo, backref=backref('valoresSelec', viewonly=True, order_by='exploracion_id')),
##    "elemento": orm.relation(Elemento, backref=backref('valoresSelec', order_by='id'))
    "elemento":		orm.relation(Elemento)
    })

orm.mapper(ValorMulti, t_valoresMulti, properties = {
    "rel_formularios_exploraciones": orm.relation(Rel_Formularios_Exploraciones,
                primaryjoin = and_(t_valoresMulti.c.exploracion_id == t_rel_Formularios_Exploraciones.c.exploracion_id,
                                    t_valoresMulti.c.formulario_id == t_rel_Formularios_Exploraciones.c.formulario_id),
##                backref = backref('valoresMulti', order_by='exploracion_id')),
                backref = backref('valoresMulti', order_by='orden')),
    "exploracion":	orm.relation(Exploracion, backref=backref('valoresMulti', viewonly=True, order_by='campo_id')),
    "formulario":	orm.relation(Formulario, backref=backref('valoresMulti', viewonly=True, order_by='campo_id')),
    "campo":		orm.relation(Campo, backref=backref('valoresMulti', viewonly=True, order_by='exploracion_id')),
    "elemento":		orm.relation(Elemento)
    })

orm.mapper(ValorBool, t_valoresBool, properties = {
    "rel_formularios_exploraciones": orm.relation(Rel_Formularios_Exploraciones,
                primaryjoin = and_(t_valoresBool.c.exploracion_id == t_rel_Formularios_Exploraciones.c.exploracion_id,
                                    t_valoresBool.c.formulario_id == t_rel_Formularios_Exploraciones.c.formulario_id),
                backref = backref('valoresBool', order_by='exploracion_id')),
    "exploracion":	orm.relation(Exploracion, backref=backref('valoresBool', viewonly=True, order_by='campo_id')), # de hecho, podria ser valorBool, y poner uselist=False...
    "formulario":	orm.relation(Formulario, backref=backref('valoresBool', viewonly=True, order_by='campo_id')),
    "campo":		orm.relation(Campo, backref=backref('valoresBool', viewonly=True, order_by='exploracion_id'))
    })

# anado una nuevo metodo a Rel_Formularios_Exploraciones, un iterador (generador) que devuelve todos los valores de todos los tipos de campos
def _rel_valores(self):
    for valor in self.valoresTexto:
        yield valor
    for valor in self.valoresSelec:
        yield valor
    for valor in self.valoresMulti:
        yield valor
    for valor in self.valoresBool:
        yield valor

Rel_Formularios_Exploraciones.valores = _rel_valores
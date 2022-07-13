import sqlalchemy as sa
from sqlalchemy import orm, ForeignKey
from sqlalchemy.orm import relation, backref

from endotools.model import meta, Paciente, Medico, TipoExploracion, \
                            Formulario, MotivoCancelacion, Centro, Servicio, Aseguradora

'''
Estado:
    0   Sin finalizar
    1   Finalizada

NOTA: Tomamos como convención que los campos de tipo Date son fechas y los de
      tipo DateTime son horas, aunque en BBDD se guarden ambos como DATETIME.
'''
t_exploraciones = sa.Table("Exploraciones", meta.metadata,
    sa.Column("id", sa.types.Integer, sa.schema.Sequence('secuencia_exploraciones'), primary_key=True),
    sa.Column("centro_id", sa.types.Integer, sa.ForeignKey('Centros.id'), nullable=True),   # Ya no se usa a partir de las 2.4.7. En posteriores versiones se eliminará!
    sa.Column("tipoExploracion_id", sa.types.Integer, sa.ForeignKey('TiposExploracion.id'), nullable=False),
    sa.Column("numero", sa.types.Integer, nullable=False),
    sa.Column("estado", sa.types.Integer, primary_key=False),   # estado = 0 -> NO FINALIZADA    estado = 1 -> FINALIZADA   estado = 2 -> CANCELADA
    sa.Column("medico_id", sa.types.Integer, sa.ForeignKey('Medicos.id'), nullable=False),
    sa.Column("paciente_id", sa.types.Integer, sa.ForeignKey('Pacientes.id'), nullable=False),
    sa.Column("fecha", sa.types.Date, nullable=False),
    sa.Column("hora", sa.types.DateTime, nullable=True),    # xxx ORACLE: si se usa "sa.types.Time" no va, tiene que ser DateTime, que es un DATE de Oracle (DATE tiene fecha y hora).
    sa.Column("StudyInstanceUID", sa.types.String(128), nullable=True),
    sa.Column("SeriesInstanceUID", sa.types.String(128), nullable=True),
    sa.Column("motivo_id", sa.types.Integer, sa.ForeignKey('MotivosCancelacion.id'), nullable=True),
    sa.Column("edad_paciente", sa.types.Integer, nullable=True),
    sa.Column("servicio_id", sa.types.Integer, sa.ForeignKey('Servicios.id'), nullable=True),   # A partir de la 2.4.7 se usa esto. indirectamente tambien indica el centro
    sa.Column("aseguradora_id", sa.types.Integer, sa.ForeignKey('Aseguradoras.id'), nullable= True),
    sa.Column("borrado", sa.types.Boolean, nullable=False, default=False),   # 2.4.10 - Borrado logico #30
    sa.Column("borrado_motivo", sa.types.String(200), nullable=True),        # 2.4.10 
    )

t_rel_Formularios_Exploraciones = sa.Table("rel_Formularios_Exploraciones", meta.metadata,
    sa.Column("exploracion_id", sa.types.Integer, sa.ForeignKey('Exploraciones.id'), primary_key=True),
    sa.Column("formulario_id", sa.types.Integer, sa.ForeignKey('Formularios.id'), primary_key=True),
    )

class Exploracion(object):
    pass

class Rel_Formularios_Exploraciones(object):
    pass

orm.mapper(Exploracion, t_exploraciones, properties = {
    "medico": orm.relation(Medico, backref=backref('exploraciones', viewonly=True, order_by='id')),
    "paciente": orm.relation(Paciente, backref=backref('exploraciones', viewonly=True, order_by='id')),
    "tipoExploracion": orm.relation(TipoExploracion, backref=backref('exploraciones', viewonly=True, order_by='id')),
    "centro": orm.relation(Centro, backref=backref('exploraciones', viewonly=True, order_by='id')),
    "servicio": orm.relation(Servicio, backref=backref('exploraciones', viewonly=True, order_by='id')),
    "motivo": orm.relation(MotivoCancelacion, backref=backref('exploraciones', viewonly=True, order_by='id')),
    "formularios": orm.relation(Rel_Formularios_Exploraciones, viewonly=True, backref = "exploracion"),
    "aseguradora": orm.relation(Aseguradora, backref=backref('exploraciones', viewonly=True, order_by='id')),
    })

orm.mapper(Rel_Formularios_Exploraciones, t_rel_Formularios_Exploraciones, properties={
    'formulario': orm.relation(Formulario, backref = backref("exploraciones", viewonly=True))
})


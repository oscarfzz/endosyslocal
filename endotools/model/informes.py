import sqlalchemy as sa
from sqlalchemy import orm, ForeignKey
from sqlalchemy.orm import relation, backref

from endotools.model import meta, Exploracion
from endotools.model.capturas import Captura
from endotools.model.medicos import Medico

# NOTA:	Tomamos como convención que los campos de tipo Date son fechas y los de
#       tipo DateTime son horas, aunque en BBDD se guarden ambos como DATETIME.

t_informes = sa.Table("Informes", meta.metadata,
    sa.Column("id", sa.types.Integer, sa.schema.Sequence('secuencia_informes'), primary_key=True),
    sa.Column("numero", sa.types.Integer, nullable=False),
    sa.Column("exploracion_id", sa.types.Integer, sa.ForeignKey('Exploraciones.id')),
    sa.Column("plantilla", sa.types.String(100), nullable=True),
    sa.Column("tipo", sa.types.Integer, default=0, nullable=True), #2.4.14
    sa.Column("fecha", sa.types.Date, nullable=False),
    sa.Column("enviado", sa.types.Boolean, nullable=True), #Indica si se ha enviado el mensaje ORU. si es null se interpreta como True, es decir, que se ha enviado.
    sa.Column("borrado", sa.types.Boolean, nullable=True),   # 2.4.10 - Borrado logico #30
    sa.Column("borrado_motivo", sa.types.String(200), nullable=True),        # 2.4.10
    sa.Column("medico_id", sa.types.Integer, sa.ForeignKey('Medicos.id'), nullable=True), #2.4.11.1
    sa.Column('comentarios', sa.types.Text, nullable=True),
    )

t_rel_Capturas_Informes = sa.Table("rel_Capturas_Informes", meta.metadata,
    sa.Column("captura_id", sa.types.Integer, sa.ForeignKey('Capturas.id'), primary_key=True),
    sa.Column("informe_id", sa.types.Integer, sa.ForeignKey('Informes.id'), primary_key=True),
    sa.Column("orden", sa.types.Integer, nullable=False),
    )

class Informe(object):
    pass

class Rel_Capturas_Informes(object):
    pass

orm.mapper(Informe, t_informes, properties = {
	"medico": orm.relation(Medico, backref=backref('informes', viewonly=True, order_by='id')),
    "rel_capturas": orm.relation(Rel_Capturas_Informes, viewonly=True, order_by='orden'),
    "capturas": orm.relation(Captura, viewonly=True, secondary = t_rel_Capturas_Informes),
    "exploracion": orm.relation(Exploracion, backref=backref('informes', viewonly=True, order_by='id'))
    })

orm.mapper(Rel_Capturas_Informes, t_rel_Capturas_Informes, properties = {
    "captura": orm.relation(Captura),
    })

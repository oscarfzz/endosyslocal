import sqlalchemy as sa
from sqlalchemy import orm, ForeignKey
from sqlalchemy.orm import relation, backref
from sqlalchemy.sql import and_

from endotools.model import meta, Exploracion, Exploracion_dicom
from endotools.model.exploraciones_dicom import t_exploraciones_dicom
from endotools.model.exploraciones import t_exploraciones

t_capturas = sa.Table("Capturas", meta.metadata,
    sa.Column("id", sa.types.Integer, sa.schema.Sequence('secuencia_capturas'), primary_key=True),
    sa.Column("seleccionada", sa.types.Boolean, nullable=True),
    sa.Column("SOPInstanceUID", sa.types.String(128), nullable=True),
    sa.Column("exploracion_id", sa.types.Integer, sa.ForeignKey('Exploraciones.id')),
    sa.Column("comentario", sa.types.Text, nullable=True),
    sa.Column("orden", sa.types.Integer, nullable=True),
    sa.Column("posx", sa.types.Integer, nullable=True),
    sa.Column("posy", sa.types.Integer, nullable=True),
    sa.Column("tipo", sa.types.String(8), nullable=True), # "jpg", "mpg" (de momento es directamente la extensión de archivo) si está vacío se interpreta como JPG
    sa.Column("uuid", sa.types.String(32), nullable=True), # el identificador del chunk
    sa.Column("disponible", sa.types.Boolean, nullable=True), #indica si el archivo esta en el servidor o en proceso de subida(false)
    sa.Column("dicom_stored", sa.types.Boolean, nullable=True, default=False), # Indica si la captura se envio al pacs en el pacs
    sa.Column("dicom_stgcmt", sa.types.Boolean, nullable=True, default=False), # Indica si la captura tiene confirmacion de Storage Commitment
    sa.Column("borrado", sa.types.Boolean, nullable=False, default=False),   # 2.4.10 - Borrado logico #30
    sa.Column("borrado_motivo", sa.types.String(200), nullable=True),        # 2.4.10 
    sa.Column("updated_at", sa.types.DateTime, nullable=True),
    )

class Captura(object):
    pass

orm.mapper(Captura, t_capturas, properties = {
    "exploracion": orm.relation(Exploracion,backref=backref('capturas', viewonly=True, order_by='id'))
    })
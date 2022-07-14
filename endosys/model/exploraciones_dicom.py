import sqlalchemy as sa
from sqlalchemy import orm, ForeignKey
from sqlalchemy.orm import relation, backref

from endosys.model import meta, Exploracion

# Posibles valores del campo "stored":
#   0 ->    la exploración no se ha enviado al PACS... se ha de enviar
#   1 ->    la exploración ya se ha enviado al PACS... ya no se ha de enviar
#   null -> la exploración no se tiene que enviar al PACS en ningún momento

t_exploraciones_dicom = sa.Table("Exploraciones_dicom", meta.metadata,
    sa.Column("exploracion_id", sa.types.Integer, sa.ForeignKey('Exploraciones.id'), primary_key=True),
    sa.Column("stored", sa.types.Boolean, nullable=True),
    sa.Column("accessionNumber", sa.types.String(64), nullable=True),
    sa.Column("studyInstanceUID", sa.types.String(100), nullable=True),
    sa.Column("studyID", sa.types.String(64), nullable=True),
    sa.Column("studyDate", sa.types.String(8), nullable=True),
    sa.Column("studyTime", sa.types.String(6), nullable=True),
    sa.Column("institutionName", sa.types.String(64), nullable=True),
    sa.Column("stationName", sa.types.String(64), nullable=True),
    sa.Column("patientName", sa.types.String(128), nullable=True),
    sa.Column("patientBirthDate", sa.types.String(8), nullable=True),
    sa.Column("patientSex", sa.types.String(16), nullable=True),
    sa.Column("studyDescription", sa.types.String(64), nullable=True),
    #sa.Column("placerOrderNumber", sa.types.String(64), nullable=True) #XXX?
    )

class Exploracion_dicom(object):
    pass

orm.mapper(Exploracion_dicom, t_exploraciones_dicom, properties = {
    "exploracion": orm.relation(Exploracion, backref=backref('exploracion_dicom', viewonly=True, uselist=False))
    })

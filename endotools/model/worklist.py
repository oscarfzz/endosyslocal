import sqlalchemy as sa
from sqlalchemy import orm, ForeignKey
from sqlalchemy.orm import relation, backref

from endotools.model import meta, Cita, Exploracion

# NOTA:	Tomamos como convención que los campos de tipo Date son fechas y los de
#       tipo DateTime son horas, aunque en BBDD se guarden ambos como DATETIME.

t_worklist = sa.Table("Worklist", meta.metadata,
    sa.Column("id", sa.types.Integer, sa.schema.Sequence('secuencia_worklist'), primary_key=True),
    sa.Column("date_queried", sa.types.Date, nullable=True),
    sa.Column("cita_id", sa.types.Integer, sa.ForeignKey('Citas.id')), # opcional
    sa.Column("exploracion_id", sa.types.Integer, sa.ForeignKey('Exploraciones.id')), # opcional
    sa.Column("source", sa.types.String(128), nullable=True), # indica de que WL viene el mensaje
    
    sa.Column("accessionNumber", sa.types.String(64), nullable=True), #0008,0050
    sa.Column("studyInstanceUID", sa.types.String(64), nullable=True), #0020,000D 
    sa.Column("refPhysicianName", sa.types.String(128), nullable=True), #0008,0090
    sa.Column("placerOrderNumber", sa.types.String(64), nullable=True), #0040,1006
    sa.Column("admissionID", sa.types.String(64), nullable=True), #0038,0010
    sa.Column("admDiagnosisDesc", sa.types.String(64), nullable=True), #0008,1080
    
    sa.Column("patientID", sa.types.String(64), nullable=True), #0010,0020
    sa.Column("patientName", sa.types.String(128), nullable=True), #0010,0010
    sa.Column("patientBirthDate", sa.types.String(16), nullable=True), #0010,0030
    sa.Column("patientSex", sa.types.String(16), nullable=True), #0010,0040
    sa.Column("patientWeight", sa.types.String(16), nullable=True), #0010,1030
    sa.Column("patientLocation", sa.types.String(64), nullable=True), #0038,0300 Current Patient Location

    sa.Column("schProcStepStartDate", sa.types.String(16), nullable=True), #0040,0002
    sa.Column("schProcStepStartTime", sa.types.String(16), nullable=True), #0040,0003
    sa.Column("schStationAETitle", sa.types.String(64), nullable=True), #0040,0001 ScheduledStationAETitle
    sa.Column("schProcStepDescription", sa.types.String(128), nullable=True), #0040,0007
    sa.Column("schProcStepID", sa.types.String(64), nullable=True), #0040,0009
    sa.Column("schProcStepLoc", sa.types.String(64), nullable=True), #0040,0011 ScheduledProcedureStepLocation
    sa.Column("schStationName", sa.types.String(64), nullable=True), #0040,0010 ScheduledStationName
    sa.Column("schPerfPhysicianName", sa.types.String(64), nullable=True), #0040,0006 ScheduledPerformingPhysiciansName
    sa.Column("modality", sa.types.String(4), nullable=True), #0008,0060
    
    sa.Column("reqPhysician", sa.types.String(128), nullable=True), #0032,1032
    sa.Column("reqService", sa.types.String(128), nullable=True), #0032,1033
    sa.Column("reqProcedureDesc", sa.types.String(64), nullable=True), #0032,1060 RequestedProcedureDescription
    sa.Column("reqProcedureID", sa.types.String(64), nullable=True), #0040,1001 RequestedProcedureID
    sa.Column("reqProcedurePriority", sa.types.String(64), nullable=True) #0040,1003 RequestedProcedurePriority
    
    )

class Work(object):
    pass

orm.mapper(Work, t_worklist, properties = {
    "cita": orm.relation(Cita, backref=backref('work', viewonly=True, uselist=False)),
    "exploracion": orm.relation(Exploracion, backref=backref('work', viewonly=True, uselist=False))
})


def get_work(**kwargs):
    """ Obtiene un registro del worklist a partir del campo
        'cita_id' o 'accessionNumber'
    """
    q = meta.Session.query(Work)
    if 'cita_id' in kwargs:
        q = q.filter( Work.cita_id == kwargs['cita_id'] )
    elif 'accessionNumber' in kwargs:
        q = q.filter( Work.accessionNumber == kwargs['accessionNumber'] )
    else:
        raise Exception(u'la función "model.endotools.worklist.get_work()" debe tener 1 parámetro ("cita_id" o "accessionNumber")')
    if q.count():
        return q.one()
    else:
        return None

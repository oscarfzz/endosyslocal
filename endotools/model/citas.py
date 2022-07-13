import sqlalchemy as sa
from sqlalchemy import orm, ForeignKey
from sqlalchemy.orm import relation, backref

#   QUITAR_CITA.SERVICIO_ID
##from endotools.model import meta, Paciente, Medico, TipoExploracion, Exploracion, Sala, Servicio, MotivoCancelacion, Prioridad, Agenda
from endotools.model import meta, Paciente, Medico, TipoExploracion, Exploracion, Sala, MotivoCancelacion, Prioridad, Agenda, Aseguradora

# NOTA:	Tomamos como convención que los campos de tipo Date son fechas y los de
#	   tipo DateTime son horas, aunque en BBDD se guarden ambos como DATETIME.

#   ESTADO DE LA CITA:
#	   exploracion_id=NULL	 cancelada=FALSE|NULL	CITA AUN NO REALIZADA
#	   exploracion_id=N		cancelada=FALSE|NULL	CITA REALIZADA CORRECTAMENTE
#	   exploracion_id=NULL		cancelada=TRUE			CITA CANCELADA (NO SE LLEGA A REALIZAR)
#   Si se cancela la exploración, el estado de la cita no cambia (sigue teniendo
#	exploracion_id=N y cancelada=FALSE|NULL)
#   No se puede cancelar (asignar cancelada=TRUE) una cita ya empezada (con
#	exploracion_id=N), el controller lo chequea.


t_citas = sa.Table("Citas", meta.metadata,
	sa.Column("id", sa.types.Integer, sa.schema.Sequence('secuencia_citas'), primary_key=True),
#	sa.Column("_codigo", sa.types.String(50), nullable=True), # xxx ORACLE
	sa.Column("paciente_id", sa.types.Integer, sa.ForeignKey('Pacientes.id')),
	sa.Column("medico_id", sa.types.Integer, sa.ForeignKey('Medicos.id')),
	sa.Column("sala_id", sa.types.Integer, sa.ForeignKey('Salas.id')),
	sa.Column("tipoExploracion_id", sa.types.Integer, sa.ForeignKey('TiposExploracion.id')),
	sa.Column("exploracion_id", sa.types.Integer, sa.ForeignKey('Exploraciones.id')),
	#   QUITAR_CITA.SERVICIO_ID
##	sa.Column("servicio_id", sa.types.Integer, sa.ForeignKey('Servicios.id'), nullable=True),   # no necesario, ya está agenda_id
	sa.Column("motivo_id", sa.types.Integer, sa.ForeignKey('MotivosCancelacion.id'), nullable=True),
	sa.Column("fecha", sa.types.Date, nullable=False),
	sa.Column("hora", sa.types.DateTime, nullable=True),	# ATENCION: es muy importante que la hora de la cita siempre incluya también la fecha correcta!
	sa.Column("observaciones", sa.types.Text, nullable=True),
	sa.Column("prioridad_id", sa.types.Integer, sa.ForeignKey('Prioridades.id'), nullable=True), # ANTERIORMENTE: 1 - Normal, 2 - Preferente, 3 - Urgente
	sa.Column("cancelada", sa.types.Boolean, nullable=True),

	sa.Column("agenda_id", sa.types.Integer, sa.ForeignKey('Agendas.id'), nullable=True),
	sa.Column("duracion", sa.types.Integer, nullable=True),  # en minutos. Sumados a la hora se obtiene la hora fin.
	sa.Column("aseguradora_id", sa.types.Integer, sa.ForeignKey('Aseguradoras.id'), nullable=True)
	)

class Cita(object):
	pass

orm.mapper(Cita, t_citas, properties = {
#	"paciente": orm.relation(Paciente, backref=backref('citas', order_by='id')),				# si no se pone ni "cascade" ni "viewonly" parece que funciona distinto en SQL Server y en MySQL.
#	"paciente": orm.relation(Paciente, backref=backref('citas', cascade="all", order_by='id')),	# el parametro "cascade" indica qué se hará con las citas si se elimina el paciente (eliminarlas también, poner el paciente_id a NULL...)
	"paciente": orm.relation(Paciente, backref=backref('citas', viewonly=True, order_by='id')),	# con viewonly=True no se intenta hacer nada sobre las Citas al eliminar pacientes, dejándolo en manos del motor de BBDD. Es como se espera que funcione (SQL Server sin viewonly ni cascade funciona asi, MySQL no)
	"sala": orm.relation(Sala, backref=backref('citas', viewonly=True, order_by='id')),
	"medico": orm.relation(Medico, backref=backref('citas', viewonly=True, order_by='id')),
	"tipoExploracion": orm.relation(TipoExploracion, backref=backref('citas', viewonly=True, order_by='id')),
	#   QUITAR_CITA.SERVICIO_ID
##	"servicio": orm.relation(Servicio, backref=backref('citas', viewonly=True, order_by='id')),
	"agenda": orm.relation(Agenda, backref=backref('citas', viewonly=True, order_by='id')),
	"motivo": orm.relation(MotivoCancelacion, backref=backref('citas', viewonly=True, order_by='id')),
	"prioridad": orm.relation(Prioridad, backref=backref('citas', viewonly=True, order_by='id')),
	"exploracion": orm.relation(Exploracion, backref=backref('cita', viewonly=True, uselist=False)),
	"aseguradora": orm.relation(Aseguradora, backref=backref('citas', viewonly=True, order_by='id'))
	})

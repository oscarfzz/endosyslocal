'''
Cada agenda pertenece a un solo servicio (e indirectamente a un solo centro)
'''

import sqlalchemy as sa
from sqlalchemy import orm
from sqlalchemy.orm import relation, backref


from endosys.model import meta, Servicio

t_agendas = sa.Table("Agendas", meta.metadata,
    sa.Column("id", sa.types.Integer,  sa.schema.Sequence('secuencia_agendas'), primary_key=True),
    sa.Column("codigo", sa.types.String(50), nullable=True),    # para integraciones
    sa.Column("nombre", sa.types.String(50), nullable=False),
	sa.Column("servicio_id", sa.types.Integer, sa.ForeignKey('Servicios.id'))
    )

t_horarios_agendas = sa.Table("HorariosAgendas", meta.metadata,
	sa.Column("agenda_id", sa.types.Integer, sa.ForeignKey('Agendas.id'), primary_key=True),
	sa.Column("hora_ini", sa.types.DateTime, primary_key=True),
	sa.Column("hora_fin", sa.types.DateTime, primary_key=True),
	sa.Column("dia_semana", sa.types.Integer, primary_key=True, autoincrement = False)  #   0 a 6 -> lunes a domingo
    )


class Agenda(object):
    pass

class HorarioAgenda(object):
    pass


orm.mapper(Agenda, t_agendas, properties = {
    "servicio": orm.relation(Servicio, backref=backref('agendas', viewonly=True, order_by='id')),
    'horarios': orm.relation(HorarioAgenda, backref = backref("medicos", viewonly=True),
							 order_by = [t_horarios_agendas.c.dia_semana, t_horarios_agendas.c.hora_ini])
})
backref = backref("medicos", viewonly=True)
orm.mapper(HorarioAgenda, t_horarios_agendas, properties={
##	"agenda": orm.relation(Agenda, backref=backref('horarios', order_by='dia_semana'))
})

def get_agenda(**kwargs):
	"""
	obiene un registro 'Agenda' a partir del codigo.
	el codigo se ha de pasar como keyword argument, ejem: codigo="AGENDA1".
	"""
	from endosys.model import meta
	q = meta.Session.query(Agenda)
	if 'codigo' in kwargs:
		if kwargs['codigo'] == None: return None
		q = q.filter( Agenda.codigo == kwargs['codigo'] )
	else:
		raise Exception(u'la función "get_agenda" debe tener 1 solo parámetro "codigo"')
	if q.count():
		return q.one()
	else:
		return None

def get_agenda_id(**kwargs):
	"""
	igual que el anterior, pero devuelve el id o None
	"""
	agenda = get_agenda(**kwargs)
	if agenda:
		return agenda.id
	else:
		return None
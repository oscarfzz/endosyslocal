'''
Cada médico puede pertenecer a varios servicios, de cualquier centro.

Cada médico puede pertenecer a varias agendas (que deben pertenecer estar
vinculadas a un servicio al que pertenezca el médico)
'''

import sqlalchemy as sa
from sqlalchemy import orm
from sqlalchemy.orm import relation, backref

from endosys.model import meta, Servicio, Agenda
##from endosys.model.servicios import Servicio

t_medicos = sa.Table("Medicos", meta.metadata,
    sa.Column("id", sa.types.Integer, sa.schema.Sequence('secuencia_medicos'), primary_key=True),
    sa.Column("username", sa.types.String(255), sa.ForeignKey('users.username'), unique=True),
    sa.Column("nombre", sa.types.String(50), nullable=False),
    sa.Column("apellido1", sa.types.String(50), nullable=True),
    sa.Column("apellido2", sa.types.String(50), nullable=True),
    sa.Column("colegiado", sa.types.String(20), nullable=True)
    )

t_rel_Medicos_Servicios = sa.Table("rel_Medicos_Servicios", meta.metadata,
    sa.Column("servicio_id", sa.types.Integer, sa.ForeignKey('Servicios.id'), primary_key=True),
    sa.Column("medico_id", sa.types.Integer, sa.ForeignKey('Medicos.id'), primary_key=True)
    )

t_rel_Medicos_Agendas = sa.Table("rel_Medicos_Agendas", meta.metadata,
    sa.Column("agenda_id", sa.types.Integer, sa.ForeignKey('Agendas.id'), primary_key=True),
    sa.Column("medico_id", sa.types.Integer, sa.ForeignKey('Medicos.id'), primary_key=True)
    )

class Medico(object):
    pass

class Rel_Medicos_Servicios(object):
    pass

class Rel_Medicos_Agendas(object):
    pass


orm.mapper(Medico, t_medicos, properties = {
    'servicios': orm.relation(Rel_Medicos_Servicios, backref = "medico"), # he quitado el viewonly=True porque si no no podia crear un nuevo medico con servicios asignados, pues no asignaba el medico_id
    'agendas': orm.relation(Rel_Medicos_Agendas, backref = "medico")
})

#orm.mapper(Rel_Medicos_Servicios, t_rel_Medicos_Servicios, properties={
#    'servicio': orm.relation(Servicio, viewonly=True, backref = "medicos")
#})
orm.mapper(Rel_Medicos_Servicios, t_rel_Medicos_Servicios, properties={
    'servicio': orm.relation(Servicio, backref = backref("medicos", viewonly=True)) # asi funciona ok, pero tal como esta arriba falla en rest/servicios update()
})

orm.mapper(Rel_Medicos_Agendas, t_rel_Medicos_Agendas, properties={
    'agenda': orm.relation(Agenda, backref = backref("medicos", viewonly=True)) # asi funciona ok, pero tal como esta arriba falla en rest/servicios update()
})


def get_medico(**kwargs):
	"""
	obtiene un registro 'Medico' a partir del username.
	el username se ha de pasar como keyword argument, ejem: username="admin".
	"""
	q = meta.Session.query(Medico)
	if 'username' in kwargs:
		q = q.filter( Medico.username == kwargs['username'] )
	else:
		raise Exception(u'la función "get_medico" debe tener 1 solo parámetro "username"')
	if q.count():
		return q.one()
	else:
		return None

def medico_tiene_servicio(medico, servicio_id):
	"""
	comprueba si el médico tiene el servicio indicado
		medico  		registro sql alchemy
		servicio_id 	id del servicio a comprobar
		devuelve        bool
	"""
	return len( filter(lambda rel: rel.servicio_id == servicio_id, medico.servicios) ) > 0
'''
id
codigo
nombre
'''

import sqlalchemy as sa
from sqlalchemy import orm
from sqlalchemy.orm import relation, backref

from endotools.model import meta, Centro

t_servicios = sa.Table("Servicios", meta.metadata,
	sa.Column("id", sa.types.Integer, sa.schema.Sequence('secuencia_servicios'), primary_key=True),
	sa.Column("codigo", sa.types.String(50), nullable=True),   # de uso para integraciones
	sa.Column("nombre", sa.types.String(50), nullable=False),
	sa.Column("centro_id", sa.types.Integer, sa.ForeignKey('Centros.id')),
	useexisting=True # parece que sirve para que se modifique la tabla aunque ya exista... aunque no parece que funcione
	)

class Servicio(object):
	pass

orm.mapper(Servicio, t_servicios, properties = {
	"centro": orm.relation(Centro, backref=backref('servicios', viewonly=True, order_by='id'))
	})

def get_servicio(**kwargs):
	"""
	obtiene un registro 'Servicio' a partir del codigo.
	el codigo se ha de pasar como keyword argument, ejem: codigo="DIGC".
	"""

	q = meta.Session.query(Servicio)
	if 'codigo' in kwargs:
		q = q.filter( Servicio.codigo == kwargs['codigo'] )
	else:
		raise Exception(u'la función "get_servicio" debe tener 1 solo parámetro "codigo"')
	if q.count():
		return q.one()
	else:
		return None

def get_servicio_id(**kwargs):
	"""
	igual que el anterior, pero devuelve el id o None
	"""
	servicio = get_servicio(**kwargs)
	if servicio:
		return servicio.id
	else:
		return None

def get_servicio_y_agenda_id(**kwargs):
	"""
	devuelve el id del servicio y el id de la primera agenda asociada al servicio,
	identificado a partir de código.
	De momento, a las citas creadas por mensajes HL7 ORM o SIU siempre se les
	asigna una sola agenda relacionada con el servicio correspondiente, como si
	la relación servicio:agenda fuera 1:1.
	Por lo tanto, en integraciones se requiere que cada servicio tenga una
	agenda.
	"""
	servicio = get_servicio(**kwargs)
	ret = [None, None]
	if servicio:
		ret[0] = servicio.id
		if len(servicio.agendas) == 0:
			#raise Exception('El servicio no tiene ninguna agenda')
			pass # XXX de momento, para evitar problemas, si o tiene agenda devuelve None en vez de lanzar una excepción
		else:
			ret[1] = servicio.agendas[0].id
	return ret
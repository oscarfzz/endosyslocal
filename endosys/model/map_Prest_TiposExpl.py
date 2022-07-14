"""
Esta tabla se utiliza para vincular códigos de prestación (o prueba), códigos
de servicios y tipos de exploración.

"hl7_process" la utiliza para averiguar el tipo de exploración según el código
de prestación y código de servicio obtenidos (función
"get_tipoExploracion_id_from_prestacion()"). (NO IMPLEMENTADO)

"worklist" la utiliza para averiguar el código de servicio a partir del código
de prestación (función "get_servicio_from_prestacion()").
Opcionalmente también puede averiguar el tipo de exploración. (AUN NO IMPLEMENTADO)


"""

import sqlalchemy as sa
from sqlalchemy import orm

from endosys.model import meta, TipoExploracion

t_map_Prest_TiposExpl = sa.Table('map_Prest_TiposExpl', meta.metadata,
    sa.Column("prestacion_cod", sa.types.String(50), nullable=False, primary_key=True),
    sa.Column("servicio_cod", sa.types.String(50), nullable=False, primary_key=True),
    sa.Column('tipoExploracion_id', sa.types.Integer, sa.ForeignKey('TiposExploracion.id'), nullable=True)
    )

class Map_Prest_TiposExpl(object):
    pass


orm.mapper(Map_Prest_TiposExpl, t_map_Prest_TiposExpl, properties={
    'tipoExploracion': orm.relation(TipoExploracion, backref = "maps_prest_tiposexpl")
})

def get_tipoExploracion_id_from_prestacion(**kwargs):
	"""
	obtiene un TipoExploracion a partir de un código de prestación y
	un código de servicio.
	los códigos se han de pasar como keyword arguments:
		prestacion="C001", servicio="DIGC"
	se devuelve el id del tipo de exploración.
	"""
	q = meta.Session.query(Map_Prest_TiposExpl)
	if not('prestacion' in kwargs) or not('servicio' in kwargs):
		raise Exception(u'la función "get_tipoExploracion_id_from_prestacion" debe tener los parámetros "prestacion" y "servicio"')

	q = q.filter( Map_Prest_TiposExpl.prestacion_cod == kwargs['prestacion'] )
	q = q.filter( Map_Prest_TiposExpl.servicio_cod == kwargs['servicio'] )

	if q.count():
		return q.one().tipoExploracion_id
	else:
		return None



##def get_servicio_from_prestacion(**kwargs):
##	"""
##	obtiene un código de servicio a partir de un código de prestación.
##	el código se ha de pasar como keyword arguments:
##		prestacion="GASTRO"
##	se devuelve el codigo de servicio.
##	"""
##	from endosys.model.meta import Session
##	q = Session.query(Map_Prest_TiposExpl)
##	if not('prestacion' in kwargs):
##		raise Exception(u'la función "get_servicio_from_prestacion" debe tener el parámetro "prestacion"')
##
##	q = q.filter( Map_Prest_TiposExpl.prestacion_cod == kwargs['prestacion'] )
##
##	if q.count():
##		return q.one().servicio_cod
##	else:
##		return None


def get_servicios_from_prestacion(**kwargs):
	"""
	obtiene los códigos de servicio a partir de un código de prestación.
	el código se ha de pasar como keyword arguments:
		prestacion="GASTRO"
	se devuelve un list con los codigos de servicio. Si no hay ninguno el list está vacio [].
	De momento solo lo usa plugins/base/citasWorklist.py
	"""
	q = meta.Session.query(Map_Prest_TiposExpl)
	if not('prestacion' in kwargs):
		raise Exception(u'la función "get_servicio_from_prestacion" debe tener el parámetro "prestacion"')

	q = q.filter( Map_Prest_TiposExpl.prestacion_cod == kwargs['prestacion'] )

	return map(lambda m: m.servicio_cod, q.all())

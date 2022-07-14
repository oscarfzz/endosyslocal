import sqlalchemy as sa
from sqlalchemy import orm, ForeignKey
from sqlalchemy.orm import relation, backref

from endotools.model import meta, Cita

'''
Información interesante a almacenar:
	identificadores externos
	NHC
	número de cita		(puede ser también un ext_id)
	número de episodio  (puede ser también un ext_id)
	número de petición  (puede ser también un ext_id)
	código prestación
	descripción prestación
	servicio
	procedencia
	servicio solicitante
	médico solicitante
	agenda
	sala
	procedimientos
	episodio anterior
	resultado enviado
	...

-Sería interesante guardar los valores con códigos (agenda, prestación, etc..)
 en tablas

INFORMACIÓN INTERESANTE:
	En SQL Server, si un campo de tipo varchar tiene valor NULL, no ocupará
	espacio. Por lo tanto no es problema tener una tabla con muchos campos
	de tipo varchar con valor NULL. En el caso de tener valor, el tamaño
	es la longitud del valor + 2 bytes.
	Por cada registro hay un bitfield que guarda qué campos tienen asignado
	valor NULL (cada 8 campos que permiten null, ocupa 1 byte).
'''
t_citas_ex = sa.Table("Citas_ex", meta.metadata,
    sa.Column("cita_id", sa.types.Integer, sa.ForeignKey('Citas.id'), primary_key=True),

    sa.Column("id_ext_1", sa.types.String(50), nullable=True, index=True),
    sa.Column("id_ext_2", sa.types.String(50), nullable=True, index=True),
    sa.Column("id_ext_3", sa.types.String(50), nullable=True, index=True),
    sa.Column("id_ext_4", sa.types.String(50), nullable=True, index=True),
##    sa.Column("id_ext_1", sa.types.String(50), nullable=True, index=True, unique=True),  # XXX deberia ser asi? indexado y único...
##    sa.Column("id_ext_2", sa.types.String(50), nullable=True, index=True, unique=True),  # NO SE PUEDE, si permite nulls...
##    sa.Column("id_ext_3", sa.types.String(50), nullable=True, index=True, unique=True),
##    sa.Column("id_ext_4", sa.types.String(50), nullable=True, index=True, unique=True),

    #sa.Column("nhc", sa.types.String(50), nullable=True),            	#   no debería hacer falta, aunque es interesante tenerlo
    sa.Column("idunico", sa.String(50),	nullable=True),
    sa.Column("cip", sa.types.String(50), nullable=True),            	#   lo mismo que arriba
    sa.Column("numero_cita", sa.types.String(50), nullable=True),
    sa.Column("numero_episodio", sa.types.String(50), nullable=True),   #   numicu
    sa.Column("numero_peticion", sa.types.String(50), nullable=True),	#	order number
    sa.Column("prestacion_cod", sa.types.String(50), nullable=True),
    sa.Column("prestacion_descr", sa.types.String(120), nullable=True),
    sa.Column("servicio_cod", sa.types.String(50), nullable=True),      #   no confundir con los "servicios" gestionados por Endosys App
    sa.Column("servicio_descr", sa.types.String(50), nullable=True),
    sa.Column("agenda_cod", sa.types.String(50), nullable=True),
    sa.Column("agenda_descr", sa.types.String(50), nullable=True),
    sa.Column("procedencia_cod", sa.types.String(50), nullable=True),
    sa.Column("procedencia_descr", sa.types.String(120), nullable=True),
    sa.Column("servicio_peticionario_cod", sa.types.String(50), nullable=True),
    sa.Column("servicio_peticionario_descr", sa.types.String(50), nullable=True),
    sa.Column("medico_peticionario_cod", sa.types.String(50), nullable=True),
    sa.Column("medico_peticionario_descr", sa.types.String(100), nullable=True),
    sa.Column("estado", sa.types.Integer, nullable=True),                #   permite a la parte de integración almacenar el estado de esta cita (ejem. si se ha enviado el informe al HIS)
    sa.Column("pv1", sa.types.Text, nullable=True),
    sa.Column("obr", sa.types.Text, nullable=True),
    sa.Column("orc", sa.types.Text, nullable=True),
    sa.Column("filler_status_code", sa.types.String(15), nullable=True) # SCH.25.1, en mensajes SIU: "This field contains a code describing the status of the appointment with respect to the filler application"

##   	sa.Column("alternate_visit_id", sa.types.String(50), nullable=True), # id proceso del HIS
##	sa.Column("placer_field_1", sa.types.String(100), nullable=True), # Candelaria (Tipo departamento destino)
##	sa.Column("placer_field_2", sa.types.String(100), nullable=True), # Candelaria (Codigo departamento destino)
##	sa.Column("diagnostic_serv_sect_id", sa.types.String(100), nullable=True) # Candelaria (Proveedor)
    )

class Cita_ex(object):
    pass

orm.mapper(Cita_ex, t_citas_ex, properties = {
    "cita": orm.relation(Cita, backref=backref('ex', viewonly=True, uselist=False))
    })

def get_cita_ex(**kwargs):
    """
    obtiene un registro 'Cita_ex' a partir de alguno de estos identificadores:
    	cita_id
		id_ext_1
        id_ext_2
        id_ext_3
        id_ext_4
		numero_cita
    	numero_episodio
    	numero_peticion

	el id se ha de pasar como keyword argument, ejem: id_ext_1=1234. Solo se
	ha de pasar uno de estos identificadores.
    """
    q = meta.Session.query(Cita_ex)
    if 'cita_id' in kwargs:
        q = q.filter( Cita_ex.cita_id == kwargs['cita_id'] )
    elif 'id_ext_1' in kwargs:
        q = q.filter( Cita_ex.id_ext_1 == kwargs['id_ext_1'] )
    elif 'id_ext_2' in kwargs:
        q = q.filter( Cita_ex.id_ext_2 == kwargs['id_ext_2'] )
    elif 'id_ext_3' in kwargs:
        q = q.filter( Cita_ex.id_ext_3 == kwargs['id_ext_3'] )
    elif 'id_ext_4' in kwargs:
        q = q.filter( Cita_ex.id_ext_4 == kwargs['id_ext_4'] )
    elif 'numero_cita' in kwargs:
        q = q.filter( Cita_ex.numero_cita == kwargs['numero_cita'] )
    elif 'numero_episodio' in kwargs:
        q = q.filter( Cita_ex.numero_episodio == kwargs['numero_episodio'] )
    elif 'numero_peticion' in kwargs:
        q = q.filter( Cita_ex.numero_peticion == kwargs['numero_peticion'] )
    else:
        raise Exception(u'la función "get_cita_ex" debe tener 1 solo parámetro')
    if q.count():
        return q.one()
    else:
        return None

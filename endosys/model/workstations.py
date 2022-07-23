'''
Estaciones de Trabajo (puestos) de EndoSys.

Para poder guardar una configuración de un equipo cliente debería estar
configurado con una IP estática.

ip              la IP es también la clave primaria
host            opcionalmente se puede guardar el nombre de host

agenda_id       agenda, servicio y centro por defecto del cliente. Se utilizan
servicio_id     en ese orden de preferencia, según si tienen valor asignado y
centro_id       si el usuario dispone de la agenda o servicio. Se usa por ejemplo
				en Citas Pendientes.
'''

import sqlalchemy as sa
from sqlalchemy import orm
from sqlalchemy.orm import relation, backref

from endosys.model import meta, Servicio

"""
	nombre:		Nombre descriptivo de la estación, para mostrar a los usuarios.
	ip:			La IP del equipo, de momento es lo que se utiliza para identificarlos.
				v2.4.8.5:	Se permite a un sólo Workstation tener la IP a NULL, siendo en ese
							caso el utilizado por defecto. Se usa para permitir acceso de
							consulta ilimitado.
	tipo:		El tipo de estación:
					NULL, 0     Sin definir
					1     		Puesto de captura
					2     		Puesto de consulta
"""

t_workstations = sa.Table("Workstations", meta.metadata,
    sa.Column("id",			sa.types.Integer, sa.schema.Sequence('secuencia_workstations'), primary_key=True),
    sa.Column("nombre",		sa.types.String(50), nullable=True),
    sa.Column("ip",			sa.types.String(15), nullable=True), # v2.4.8.5: ahora puede ser NULL, que será el workstation "por defecto".
    sa.Column("nombre_equipo", sa.types.String(200), nullable=True),
	sa.Column("tipo",		sa.types.Integer,	 nullable=True),
	sa.Column("borrado", 	sa.types.Boolean, nullable=False, default=False),  
    sa.Column("borrado_motivo", sa.types.String(200), nullable=True),   
)

t_rel_Servicios_Workstations = sa.Table("rel_Servicios_Workstations", meta.metadata,
    sa.Column("workstation_id", sa.types.Integer, sa.ForeignKey('Workstations.id'), primary_key=True),
    sa.Column("servicio_id", sa.types.Integer, sa.ForeignKey('Servicios.id'), primary_key=True)
    )


class Workstation(object):
    pass

class Rel_Servicios_Workstations(object):
    pass

orm.mapper(Workstation, t_workstations, properties = {
    'servicios': orm.relation(Rel_Servicios_Workstations, backref = "workstation") # sin viewonly=True, si no no se puede crear un nuevo workstation con servicios asignados, pues no se asigna el workstation_id
})

orm.mapper(Rel_Servicios_Workstations, t_rel_Servicios_Workstations, properties={
#    'servicio': orm.relation(Servicio, viewonly=True, backref = "workstations")
    'servicio': orm.relation(Servicio, backref = backref("workstations", viewonly=True)) # asi debería funcionar ok, si hubiera algún fallo probar tal como está encima
})

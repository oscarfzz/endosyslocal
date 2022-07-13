'''
 Nueva a partir de la 2.4.18
 Se usa para guardar parametros de configuracion o 
 informacion de la aplicacion como por ejemplo la version
'''
import sqlalchemy as sa
from sqlalchemy import orm
from sqlalchemy.orm import relation, backref
from endotools.model import meta
t_configuraciones = sa.Table("Configuraciones", meta.metadata,
    sa.Column("clave", sa.types.String(15), primary_key=True),
    sa.Column("valor", sa.types.Text, nullable=False)
    )

class Configuracion(object):
    pass

orm.mapper(Configuracion, t_configuraciones)

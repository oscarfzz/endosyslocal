'''
id
nombre
'''

import sqlalchemy as sa
from sqlalchemy import orm
from sqlalchemy.orm import relation, backref

from endotools.model import meta

# Tipos de campo (posibles valores de "tipo")
#   1: texto
#   2: selec
#   3: multi
#   4: bool
#   5: memo
#   6: separador/titulo

# Tipos de control (posibles valores de "tipo_control")
#   0, null: select comun, multiselect comun
#   1:       select actocomplete (solo afecta al tipo=2 (select))
#   2:       multiselect con cantidades ( solo afecta al tipo=3 (multiselect)). A partir de la 2.4.10 #680

# Ambito: Para campos de selección/multiselección, indica si el listado de
# elementos será común para todos los Servicios, o si cada servicio tendrá un
# listado exclusivo de elementos para dicho campo. Valores:
#   0, null: listado común (comportamiento normal, el habitual hasta v2.4.21)
#   1:       listado por servicio

t_campos = sa.Table("Campos", meta.metadata,
    sa.Column("id", sa.types.Integer, sa.schema.Sequence('secuencia_campos'), primary_key=True),
    sa.Column("nombre", sa.types.String(50), nullable=False, unique=True),
    sa.Column("titulo", sa.types.String(50), nullable=False),
    sa.Column("tipo", sa.types.Integer, nullable=False),
    sa.Column("columnas", sa.types.Integer, nullable=False),
    sa.Column("tipo_control", sa.types.Integer, nullable=True),
    sa.Column("valorPorDefecto", sa.types.String(1000), nullable=True),
    sa.Column("solo_lectura", sa.types.Boolean, nullable=True),  #   se refiere a que el usuario no puede introducir un valor, pero la interfaz REST si que lo acepta (se puede asignar un valor por programación en javascript)
    sa.Column("script", sa.types.Text, nullable=True),   # es un script (javascript) que se ejecuta para calcular el valor del campo (en cliente)
    sa.Column("obligatorio", sa.types.Boolean, nullable=True),
    sa.Column("ambito", sa.types.Integer, nullable=True),
    )

class Campo(object):
    pass

orm.mapper(Campo, t_campos)

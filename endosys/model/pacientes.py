# -*- coding: utf-8 -*-

import sqlalchemy as sa
from sqlalchemy import orm, ForeignKey
from sqlalchemy.orm import relation, backref

from endosys.model import meta, Aseguradora, Centro
##from endosys.model.aseguradoras import Aseguradora

# NOTA:	Tomamos como convención que los campos de tipo Date son fechas y los de
#       tipo DateTime son horas, aunque en BBDD se guarden ambos como DATETIME.

t_pacientes = sa.Table("Pacientes", meta.metadata,
    sa.Column("id", sa.types.Integer, sa.schema.Sequence('secuencia_pacientes'), primary_key=True),
    sa.Column("idunico", sa.types.String(50), nullable=True, index=True),
    sa.Column("CIP", sa.String(50), nullable=True, index=True),
    sa.Column("DNI", sa.String(50), nullable=True),
    sa.Column("nombre", sa.types.String(50), nullable=True),
    sa.Column("apellido1", sa.types.String(50), nullable=True),
    sa.Column("apellido2", sa.types.String(50), nullable=True),
    sa.Column("sexo", sa.types.Integer, nullable=True),         # 0 - mujer, 1 - hombre
    sa.Column("fechaNacimiento", sa.types.Date, nullable=True),
    sa.Column("direccion", sa.types.String(100), nullable=True),
    sa.Column("poblacion", sa.types.String(50), nullable=True),
    sa.Column("provincia", sa.types.String(50), nullable=True),
    sa.Column("codigoPostal", sa.types.String(5), nullable=True),
    sa.Column("aseguradora_id", sa.types.Integer, sa.ForeignKey('Aseguradoras.id')),
    sa.Column("numAfiliacion", sa.types.String(50), nullable=True),
    sa.Column("telefono1", sa.types.String(20), nullable=True),
    sa.Column("telefono2", sa.types.String(20), nullable=True),
    sa.Column("comentarios", sa.types.Text(1000), nullable=True),
    sa.Column("numero_expediente", sa.types.String(50), nullable=True),
	sa.Column("deshabilitado", sa.types.Boolean, nullable=True)
	)

t_rel_Pacientes_Centros = sa.Table("rel_Pacientes_Centros", meta.metadata,
    sa.Column("centro_id", sa.types.Integer, sa.ForeignKey('Centros.id'),primary_key=True),
    sa.Column("paciente_id", sa.types.Integer, sa.ForeignKey('Pacientes.id'),primary_key=True),
    sa.Column("nhc", sa.types.String(50), nullable=False, index=True)
    )

class Paciente(object):
    pass

class Rel_Pacientes_Centros(object):
    pass

orm.mapper(Paciente, t_pacientes, properties = {
    "aseguradora": orm.relation(Aseguradora, backref=backref('pacientes', viewonly=True, order_by='id')),
    "centros": orm.relation(Rel_Pacientes_Centros, viewonly=True, backref = backref('paciente'))
})

orm.mapper(Rel_Pacientes_Centros, t_rel_Pacientes_Centros, properties={
    'centro': orm.relation(Centro, backref = backref("pacientes", viewonly=True)) # asi funciona ok, pero tal como esta arriba falla en rest/servicios update()
})
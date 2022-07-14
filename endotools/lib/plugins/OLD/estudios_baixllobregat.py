""" plugin para trazabilidad de lavadoras

requiere el plugin de campos_baixllobregat

"""

import os
import logging
from endotools.model import meta
from endotools.lib.plugins.base import *
from endotools.lib.plugins.base.estudios import PluginEstudios, Estudio
from endotools.lib.misc import *
from sqlalchemy.types import Integer, Date
from sqlalchemy.sql import and_
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.exceptions import IntegrityError

import endotools.model.estudios, endotools.model.citas, endotools.model.prestaciones

from pylons import config

import time
from datetime import date, datetime

import logging
log = logging.getLogger(__name__)

class PluginEstudiosBaixLlobregat(PluginEstudios):

	_mapper_TicketsLavadoras = None

	class TicketsLavadoras(object):
		pass

	def _crear_tabla_TicketsLavadoras(self):
		log.debug("_crear_tabla_TicketsLavadoras")
		if not self._mapper_TicketsLavadoras:
			self._mapper_TicketsLavadoras = orm.mapper(self.TicketsLavadoras, t_TicketsLavadoras)
		t_TicketsLavadoras.create(bind=meta.engine, checkfirst=True)
		#meta.metadata.create_all(bind=meta.engine)
		meta.Session.commit()

	def _get_reg_TicketsLavadoras(self, estudio_id, must_exist = True):
		q = meta.Session.query(self.TicketsLavadoras)
		q = q.filter( self.TicketsLavadoras.estudio_id == estudio_id )
		# el registro deberia existir
		if q.count() == 0:
			if must_exist: raise E_ErrorServidor('No existe el registro de TicketsLavadoras para el estudio %s' % str(estudio_id))
			else: return None
		else:
			return q.one()


	def __init__(self, campo_endoscopio):
		""" 'campo_endoscopio' tiene que ser el nombre del campo de tipo selec que indica el endoscopio seleccionado """

		PluginEstudios.__init__(self)
		from endotools.lib.plugins.campos_baixllobregat import PluginCamposBaixLlobregat
		self._add_dependence(PluginCamposBaixLlobregat)

		# configuracion
		self.campo_endoscopio = campo_endoscopio.upper()
		self.modelos_endoscopios = {}

		self.like_filter = ()
		self.tabla = endotools.model.estudios.Estudio

		# crear la tabla TicketsLavadoras en la BBDD
		self._crear_tabla_TicketsLavadoras()

	def convertir_a_formato_ticket(self, endoscopio):
		""" convierte un identificador de endoscopio tal como se selecciona en
		EndoTools al formato tal como se imprime en el ticket. ahora mismo es asi:

		EndoTools			   Ticket
		modelo (num_serie)	  modelo_abreviado-num_serie------ (ancho de 16 chars)
		"""
		modelo = ''
		n_serie = ''
		if '(' in endoscopio:
			modelo = endoscopio[: endoscopio.index('(')].strip()
		else:
			modelo = endoscopio.strip()
		if ('(' in endoscopio) and (')' in endoscopio):
			n_serie = endoscopio[endoscopio.index('(')+1 : endoscopio.index(')')]

		if modelo in self.modelos_endoscopios:
			return ( '%s-%s' % (self.modelos_endoscopios[modelo], n_serie) ).ljust(16, '-')
		else:
			return ( '%s-%s' % (modelo, n_serie) ).ljust(16, '-')


	def inicia_estudio(self, id, medico, params):
		""" en principio no hacer nada """
		pass


	def finaliza_estudio(self, id, medico):

		def get_endoscopio():
			from endotools.lib.prestacion import TIPO_SELEC
			from endotools.lib.prestacion import PrestData
			for prestacion in estudio.prestaciones:
				prestdata = PrestData(prestacion)
				for campo in prestdata.campos:
					if campo.nombre.upper() == self.campo_endoscopio:
						if campo.tipo != TIPO_SELEC:
							raise E_ErrorServidor('El campo de endoscopio debe ser de tipo selección')
						return campo.valor.get()
			return None


		""" asignar el ticket correspondiente al endoscopio seleccionado """
		estudio = registro_by_id(self.tabla, id)

		# obtener el endoscopio seleccionado
		endoscopio = get_endoscopio()
		if not endoscopio: return
		endoscopio = endoscopio[1]

		# extraer/convertir el identificador del endoscopio tal como se muestra en el ticket
		log.debug('Endoscopio (formato campo): %s', endoscopio)
		endoscopio = self.convertir_a_formato_ticket(endoscopio)
		log.debug('Endoscopio (formato ticket): %s', endoscopio)

		# buscar el ticket para este endoscopio, que tenga estado=0
		q = meta.Session.query(self.TicketsLavadoras)
		q = q.filter( and_( self.TicketsLavadoras.endoscopio_NUM == endoscopio,
							self.TicketsLavadoras.estado == 0) )

		# el registro deberia existir
		if q.count() == 0: return
		ticketLavadora = q.one()

		# marcarlo como usado (estado=1) y asignarle el estudio_id a este estudio
		ticketLavadora.estado = 1
		ticketLavadora.estudio_id = id
		meta.Session.update(ticketLavadora)
		meta.Session.commit()


import sqlalchemy as sa
from sqlalchemy import orm, ForeignKey
from sqlalchemy.orm import relation, backref

t_TicketsLavadoras = sa.Table("TicketsLavadoras", meta.metadata,
	sa.Column("id", sa.types.Integer, primary_key=True),
	sa.Column("ticket", sa.types.String(5000), nullable=True),
	sa.Column("endoscopio_NUM", sa.types.String(50), nullable=True),
	sa.Column("estudio_id", sa.types.Integer, nullable=True),
	sa.Column("estado", sa.types.Integer, nullable=True),
	)

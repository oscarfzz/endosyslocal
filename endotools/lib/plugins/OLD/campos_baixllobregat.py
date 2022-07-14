"""
El plugin de campos sirve para añadir campos aparte de los normales de EndoTools.
Los valores de estos campos se obtienen y modifican de una forma externa al resto
de campos.

se definen estos campos:

id                      tipo
-------------------------------------------------------
_ticket                 memo


XXX reestructurar esto, abstrayendo la info de cada campo en clases

requiere el plugin de estudios_baixllobregat
"""

import logging
from endotools.model import meta
from endotools.lib.plugins.base import *
from endotools.lib.plugins.base.campos import PluginCampos, Campo, Elemento
from endotools.lib.misc import *
from sqlalchemy.types import Integer, Date
from sqlalchemy.sql import and_
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.exceptions import IntegrityError

from endotools.model.estudios import Estudio


class PluginCamposBaixLlobregat(PluginCampos):

    def __init__(self):
        PluginCampos.__init__(self)
        from endotools.lib.plugins.estudios_baixllobregat import PluginEstudiosBaixLlobregat
        self._add_dependence(PluginEstudiosBaixLlobregat)
        self.TicketsLavadoras = None

    def _get_TicketsLavadoras_class(self):
        # obtiene la clase para acceder a la tabla TicketsLavadoras.
        # primero comprueba si la tabla se ha de crear
        if self.TicketsLavadoras: return
        from endotools.config.plugins import pluginEstudios
        pluginEstudios._crear_tabla_TicketsLavadoras()
        self.TicketsLavadoras = pluginEstudios.TicketsLavadoras

    def _get_reg_TicketsLavadoras(self, estudio_id, must_exist = True):
        from endotools.config.plugins import pluginEstudios
        return pluginEstudios._get_reg_TicketsLavadoras(estudio_id, must_exist)


    def get_campos(self, prestacion):
        from endotools.lib.prestacion import TIPO_SELEC, TIPO_MEMO
##        estudio = Session.query(Estudio).filter( Estudio.id == prestacion.estudio_id ).one()
        return (Campo(  id = '_ticket', nombre = '_ticket', titulo = 'Ticket',
                        tipo = TIPO_MEMO, columnas = 2, orden = 1, solo_lectura = 1, grupoCampos_id = '_TRAZABILIDAD',
                        grupoCampos_nombre = 'Trazabilidad', grupoCampos_columnas = 2),
##                Campo(  id = '_motivo_fallo', nombre = '_motivo_fallo', titulo = 'Motivo fallo',
##                        tipo = TIPO_SELEC, columnas = 1, orden = 2, grupoCampos_id = '_CAPTURA_ACTIVIDAD',
##                        grupoCampos_nombre = 'Captura de actividad', grupoCampos_columnas = 2),
##                Campo(  id = '_estado_seguimiento', nombre = '_estado_seguimiento', titulo = 'Estado seguimiento',
##                        tipo = TIPO_SELEC, columnas = 1, orden = 3, grupoCampos_id = '_CAPTURA_ACTIVIDAD',
##                        grupoCampos_nombre = 'Captura de actividad', grupoCampos_columnas = 2),
                )


    def get_valor_campo(self, prestacion, campo_id):
        if campo_id == '_ticket':
            # buscar en la tabla TicketsLavadoras el ticket correspondiente al estudio
            self._get_TicketsLavadoras_class()
            ticketLavadora = self._get_reg_TicketsLavadoras(prestacion.estudio_id, must_exist = False)
            if ticketLavadora:
                return (ticketLavadora.ticket, )
            else:
                return ('(No hay ticket asociado)',)
        return None


    def set_valor_campo(self, prestacion, campo_id, valor):
        """ no se puede modificar el valor del ticket """
        pass


    def get_elementos_campo(self, campo_id):
        """ no hay campos de tipo selec """
        pass
##        if campo_id == '_estado_seguimiento':
##            return (Elemento(id = 0, nombre = u'0 Fin de seguimiento'),
##                	Elemento(id = 1, nombre = u'1 En seguimiento'),
##                	Elemento(id = 2, nombre = u'2 Paso a otra consulta'),
##                	Elemento(id = 5, nombre = u'5 Paso a otro centro funcional'),
##                	Elemento(id = 6, nombre = u'6 Paso a otro centro hospitalario'),
##                    )
##        else:
##            return ()

''' clase base para crear un plugin de gestion de agendas.

posibles errores: (usar los mismos codigos http, por conveniencia)

403 - No permitido: no se permite la operacion
401 - No autorizado: la operacion se permite pero no esta autorizado
400 - parametros incorrectos: los parametros suministrados son incorrectos
404 - no se ha encontrado: no existe ninguna agenda con el id o parametros de busqueda indicados
500 - error no especificado

estados correctos:
200 - ok
201 - la agenda se ha creado correctamente

'''

# XXX deberia gestionar tambien (o opcionalmente): salas (y tipos prestacion y medicos?) para vincular correctamente
# XXX Mejor usar excepciones?

from endosys.lib.misc import record
from endosys.lib.plugins.base import obj_from_params, Plugin

# usar los mismos nombres de campos que en la tabla de agendas, asi es mas sencillo
class Agenda(object):

    def __init__(self, **kwargs):
        self.id = None
        self.nombre = None
        self.horamin = None
        self.horamax = None
        self.activa = None
        self.codigo_servicio = None
        for k in kwargs: setattr(self, k, kwargs[k])

# de momento me baso en las mismas operaciones REST
class PluginAgendas(Plugin):

    def index(self, params):
        Plugin.__init__(self)
        """ devuelve un list de objetos Agenda.
        """
        # XXX falta definir el formato de params y los valores permitidos (un dict seria lo mejor. incluso usar el **kwargs)
        # o podria ser un mismo objeto Agenda, con los campos distintos de None siendo el filtro...
        pass

    def show(self, id):
        """ devuelve un objeto Agenda con el id indicado """
        pass

    def create(self, agenda):
        """ crea una nueva agenda a partir del objeto Agenda pasado como parametro.
        devuelve el id
        """
        pass

    def update(self, id, agenda):
        """ modifica una agenda con el id indicado a partir de los datos del objeto Agenda pasado como parametro.
        devuelve un codigo de estado
        """
        pass

    def delete(self, id):
        """ elimina una agenda con el id indicado.
        devuelve un codigo de estado
        """
        pass

    def agenda_from_params(self, params):
        """ devuelve un objeto Agenda a partir de unos params
        """
        agenda = Agenda()
        obj_from_params(agenda, params)
        return agenda

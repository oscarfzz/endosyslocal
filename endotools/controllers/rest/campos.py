import logging
from endotools.model.campos import Campo
from endotools.model import Formulario
from xml.etree.ElementTree import Element, SubElement, tostring

from endotools.lib.genericREST import *

from authkit.authorize.pylons_adaptors import authorize
from authkit.permissions import RemoteUser, ValidAuthKitUser, UserIn, HasAuthKitRole, And
from endotools.lib.usuarios.seguridad import roles

#from paste.util.multidict import MultiDict, UnicodeMultiDict

from endotools.lib.plugins.base import *
from endotools.config.plugins import pluginCampos

log = logging.getLogger(__name__)

class CamposController(GenericRESTController):

    def __init__(self, *args, **kwargs):
        GenericRESTController.__init__(self, *args, **kwargs)
        self.tabla = Campo
        self.nombre_recurso = 'campo'
        self.nombre_recursos = 'campos'
        self.campos_index = ('id', 'nombre', 'titulo', 'tipo', 'columnas', 'valorPorDefecto', 'tipo_control', 'ambito')

    @authorize(RemoteUser())
    def index(self, formulario_id=None, format='xml'):
        p = request.params
        self.formulario_id = formulario_id
        return self._doIndex(p, format)

    def _filtrar_index(self, query, format= None):
        #  filtrar por formulario
        if self.formulario_id != None:
            query = query.filter(Campo.formularios.any(Formulario.id == self.formulario_id))
        return query

    @authorize(RemoteUser())
    def show(self, id, format='xml'):
        return GenericRESTController.show(self, id, format)

    @authorize(HasAuthKitRole([roles.admin_tipos_exploracion]))
    def create(self, format='xml'):
        return GenericRESTController.create(self, format)


    @authorize(HasAuthKitRole([roles.admin_tipos_exploracion]))
    def update(self, id):
        '''
        poder ejecutar la funcion de "actualizar". Se utiliza en la integración
        de SIHGA, sirve para cargar los elementos de un campo de tipo selección
        de una fuente externa (otra tabla, un WS, etc...)
        para ejecutar esta funcion se pasa el parámetro "_actualizar=1"
        '''
        if '_actualizar' in request.params:
            if request.params['_actualizar'] == '1': self._actualizar_elementos(id)
            del request.params['_actualizar']
            return

        return GenericRESTController.update(self, id)

    @authorize(HasAuthKitRole([roles.admin_tipos_exploracion]))
    def delete(self, id):
        return GenericRESTController.delete(self, id)

    def _actualizar_elementos(self, id):
        #   de momento se usa para la integración con SIHGA, aunque está implementado
        #   como plugin, para que se pueda reutilizar
        if pluginCampos:
            pluginCampos._do_actualizar_elementos_campo(id)
##          try:
##              pluginCampos._do_actualizar_elementos_campo(id)
##          except PluginException, e:
##              abort_xml(e.http_status, str(e))
##          except Exception, e:
##              abort_xml(500, 'Ha ocurrido un error actualizando los elementos del campo (%s)' % e)
        # ############################################################

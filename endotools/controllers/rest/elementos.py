import logging
from pylons.i18n import _
from endotools.model import meta
from endotools.model.elementos import Elemento
from xml.etree.ElementTree import Element, SubElement, tostring

#from endotools.lib.base import *
from endotools.lib.genericREST import *

from authkit.authorize.pylons_adaptors import authorized, authorize, NotAuthorizedError
from authkit.permissions import RemoteUser, ValidAuthKitUser, UserIn, HasAuthKitRole, And

from endotools.lib.usuarios.seguridad import roles

from endotools.lib.plugins.base import *
from endotools.config.plugins import pluginCampos
import endotools.lib.plugins.base.campos as campos_base_plugin
from endotools.model.formularios import Rel_Campos_Formularios

from endotools.model.valores import ValorSelec, ValorMulti
from endotools.lib.misc import registro_by_id

log = logging.getLogger(__name__)


class ElementosController(GenericRESTController):

    def __init__(self, *args, **kwargs):
        GenericRESTController.__init__(self, *args, **kwargs)
        self.tabla = Elemento
        self.nombre_recurso = 'elemento'
        self.nombre_recursos = 'elementos'
        self.campos_index = ('id', 'campo_id', 'nombre', 'activo', 'orden', 'codigo')
        #self.like_filter = ('nombre')
        self.contains_filter = ('nombre')
        self.campo_orderby = Elemento.orden, Elemento.nombre


    @authorize(RemoteUser())
    def index(self, campo_id=None, format='xml'):
        #if p["campo_id"]=="310":
        #   raise Exception("Error")

        p = request.params
        if campo_id != None: p['campo_id'] = campo_id
        #   XXX si se pasa el parametro "query" se sustituye por "nombre"
        #   ya que "query" es que el usa el autocomplete de YUI2 por defecto...
        if 'query' in p:
            if p['query'] == ' ':
                 p['query'] = ''

            p['nombre'] = p['query']
            del(p['query'])

        # si está el campo "activo", intenta pasarlo a INT (esperando 0 o 1),
        # ya que si no, al ser tipo BIT en BBDD, no lo reconoce bien
        if 'activo' in p:
            try:
                p['activo'] = int(p['activo'])
            except Exception as e:
                log.error(e)

        return self._doIndex(p, format)

    def _doIndex(self, params, format='xml'):
        campo_id = params.get('campo_id')
        #   XXX
        #   ELEMENTOS DE CAMPOS FIJOS: campo_id es SEXO, TIPOEXPLORACION o MEDICO
        #   igual seria mas correcto que el medico y el tipo de exploracion se obtubieran
        #   de rest/medicos y rest/tiposexploracion directamente, o al menos si se permite
        #   de los dos, que compartan el mismo codigo.
        #   Tener en cuenta que de esta forma no puede haber un plugincampos que
        #   gestione estos campos.
        if (campo_id and str(campo_id).upper() in ('SEXO', 'MEDICO', 'TIPOEXPLORACION', 'SERVICIO', 'ASEGURADORA_ID')):
            if str(campo_id).upper() == 'SEXO':
                elementos = (
                        {'id': 'H', 'codigo': '',   'nombre': _('Sexo:Hombre'), 'activo': True},#IDIOMAOK
                        {'id': 'M', 'codigo': '',   'nombre': _('Sexo:Mujer'),  'activo': True}#IDIOMAOK
                    )
            elif str(campo_id).upper() == 'SERVICIO':
                # obtener los servicios del médico
                medico = medico_from_user(request.environ['REMOTE_USER'])
                # SERVICIOS DEL MEDICO
                elementos = []
                for rel in medico.servicios:
                    elementos.append({'id': formatea_valor(rel.servicio.id),    'codigo': '',   'nombre': formatea_valor(rel.servicio.nombre),  'activo': True})

            elif str(campo_id).upper() == 'MEDICO':
                # obtener los medicos
                from endotools.model.medicos import Medico
                medicos = meta.Session.query(Medico).all()
                elementos = []
                for medico in medicos:
                    elementos.append({'id': formatea_valor(medico.id),  'codigo': '',   'nombre': formatea_valor(medico.nombre),    'activo': True})
            elif str(campo_id).upper() == 'TIPOEXPLORACION':
                # obtener los tipos de exploracion
                from endotools.model.tiposExploracion import TipoExploracion
                tiposExploracion = meta.Session.query(TipoExploracion).all()
                elementos = []
                for tipoExploracion in tiposExploracion:
                    elementos.append({'id': formatea_valor(tipoExploracion.id), 'codigo': '',   'nombre': formatea_valor(tipoExploracion.nombre),   'activo': tipoExploracion.activo})
            elif str(campo_id).upper() == 'ASEGURADORA_ID':
                # obtener los tipos de exploracion
                from endotools.model.aseguradoras import Aseguradora
                listado_aseguradoras = meta.Session.query(Aseguradora).all()
                elementos = []
                for aseguradora in listado_aseguradoras:
                    elementos.append({'id': formatea_valor(aseguradora.id), 'codigo': '',   'nombre': formatea_valor(aseguradora.nombre),   'activo': True})
            else:
                elementos = ()

            if len(elementos) == 0: abort_xml(404, _('No se ha encontrado ningún elemento'))#IDIOMAOK
            return self.respuesta_doIndex(None, elementos, format)

        # #######################################################################

        # solo se accedera al plugin de campos si se hace por el campo_id, y éste NO es un int
        if not( pluginCampos and campo_id and not isint(campo_id) ):
            return GenericRESTController._doIndex(self, params, format)
        else:
            try:
                elementos = pluginCampos.get_elementos_campo(campo_id)
            except PluginException, e:
                log.error(e)
                abort_xml(e.http_status, str(e))
            except Exception, e:
                log.error(e)
                abort_xml(500, _('Ha ocurrido un error cargando los elementos (%s)') % e)#IDIOMAOK

            # si no se encuentra ningun elemento, devolver error 404
            if len(elementos) == 0: abort_xml(404, _('No se ha encontrado ningún elemento'))#IDIOMAOK

            if format == 'html':
                return ''

            elif format == 'xml':
                response.content_type = "text/xml"
                response.headers['cache-control'] = "no-cache, no-store, must-revalidate"

                root = Element(self.nombre_recursos)
                for elemento in elementos:
                    e = SubElement(root, self.nombre_recurso, {
                                'id': formatea_valor(elemento.id),
                                'href': h.url_for('rest_' + self.nombre_recurso, id=elemento.id, format=format) })
                    SubElement(e, 'campo_id').text = formatea_valor(campo_id)
                    SubElement(e, 'nombre').text = formatea_valor(elemento.nombre)
                    SubElement(e, 'activo').text = formatea_valor(elemento.activo)
                    SubElement(e, 'codigo').text = formatea_valor(elemento.codigo)



                return tostring(root)


    @authorize(RemoteUser())
    def show(self, id, format='xml'):
        return GenericRESTController.show(self, id, format)

##  @authorize(HasAuthKitRole([roles.crear_elementos]))
    @authorize(HasAuthKitRole([roles.baja_elementos]))
    def update(self, id):
        # solo se permite cambiar el campo "activo" y "orden", no se puede modificar
        # nada mas a no ser que seas sysadmin.
        # XXX se podria permitir modificar si aun no se ha usado.
        # XXX tambien se podria implementar la "baja" desde el delete.
        if 'campo_id' in request.params or 'nombre' in request.params:
            raise NotAuthorizedError

        if 'codigo' in request.params and (request.environ['REMOTE_USER'] != "sysadmin"):
            raise NotAuthorizedError

        return GenericRESTController.update(self, id)


    @authorize(RemoteUser())
    #@authorize(HasAuthKitRole([roles.crear_elementos]))
    def create(self, campo_id=None, format='xml'):
        #import pdb
        #pdb.set_trace()
        p = request.params
        if campo_id != None: p['campo_id'] = campo_id

        #2.4.10.3: si el elemento que se quiere agregar tiene una relacion con un campo de texto predefinido
        #          no se comprueban permisos.
        comprobar_permisos = True
        if p['campo_id'] is not None:
            cant_relacionados = meta.Session.query(Rel_Campos_Formularios).filter(Rel_Campos_Formularios.campo_rel_id == p["campo_id"])
            if cant_relacionados.count()>0:
                comprobar_permisos=False

        if comprobar_permisos:
            if not authorized(HasAuthKitRole(roles.crear_elementos)):   
                abort_json(403, _("No tiene permisos para agregar un elemento de este campo"))#IDOMAOK
                
        if 'nombre' in p:
            existe_elemento = meta.Session.query(Elemento).filter(Elemento.nombre == p["nombre"])
            existe_elemento = existe_elemento.filter(Elemento.campo_id == p["campo_id"])
            if 'servicio_id' in p:
                existe_elemento = existe_elemento.filter(Elemento.servicio_id == p["servicio_id"])
            if existe_elemento.count() > 0:
                abort_json(400, _("Ya existe un elemento con el mismo nombre para ese campo"))#IDIOMAOK

        return GenericRESTController._doCreate(self, p, format)


    @authorize(HasAuthKitRole([roles.baja_elementos]))
    def delete(self, id):
        #obtener el elmento
        elem = meta.Session.query(Elemento).filter(Elemento.id == id).one()
        nombre = unicode(elem.nombre,errors='ignore')

        # checkear si esta siendo utilizado en ValorMulti y ValorSelec
        q = meta.Session.query(ValorMulti).filter(ValorMulti.elemento_id == id)
        cant_multi = q.count()

        q = meta.Session.query(ValorSelec).filter(ValorSelec.elemento_id == id)
        cant_selec = q.count()

        #si tiene elementos no se puede eliminar
        if cant_selec or cant_multi:
            # Envia el error 500 con el nombre,
            json = { 'nombre': nombre }
            abort_json(500, json)
        else:
            return GenericRESTController.delete(self, id)

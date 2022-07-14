import os
import shutil
import json
try:
    import Image
except ImportError:
    from PIL import Image
import logging
from datetime import date
from base64 import b64decode

from pylons.i18n import _
from xml.etree.ElementTree import Element, SubElement, tostring
from sqlalchemy.sql import join
from authkit.authorize.pylons_adaptors import authorized, authorize, authorize_request, NotAuthorizedError
from authkit.permissions import RemoteUser, ValidAuthKitUser, UserIn, HasAuthKitRole, And
from sqlalchemy import or_
from sqlalchemy.orm import eagerload_all

from endosys.lib.genericREST import *
from endosys.model import meta
from endosys.model.capturas import Captura
from endosys.model.citas import Cita
from endosys.model.worklist import Work
from endosys.model.servicios import Servicio
from endosys.model.exploraciones_dicom import Exploracion_dicom
from endosys.model.exploraciones import Exploracion
from endosys.lib.usuarios.seguridad import roles
from endosys.lib.misc import *
from endosys.lib.pydcmtk.pydcmtk import *
import endosys.lib.registro as registro
from endosys.lib import capturas
from endosys.lib.exploraciones import is_exploracion_borrada

log = logging.getLogger(__name__)

class CapturasController(GenericRESTController):

    def __init__(self, *args, **kwargs):
        GenericRESTController.__init__(self, *args, **kwargs)
        self.tabla = Captura
        self.nombre_recurso = 'captura'
        self.nombre_recursos = 'capturas'
        self.campos_index = ('id', 'exploracion', 'seleccionada', 'comentario', \
                             'orden', 'tipo', 'posx', 'posy', 'disponible', \
                             'dicom_stored', 'dicom_stgcmt', 'SeriesInstanceUID')
        self.format = 'json'

    @conditional_authorize(RemoteUser())
    def index(self, exploracion_id=None, format='xml'):
        """ Parametros adicionales a enviar para filtrar:
            * tipos: Si se envia 'tipos' en parametros, entonces filtra por los tipos
                     indicados. El formato tendrá que ser tipos=jpg,avi,otro 
            * exploracion_estado
            * dicom_stored / dicom
        """
        self.format=format
        p = request.params
        if exploracion_id != None: p['exploracion_id'] = exploracion_id
        self.medico_id = None
        self.mostrar_de_exploraciones_borrada = False
        self.exploracion_estado = None
        self.tipos = None
        self.cargar_exploracion_dicom =  False

        # se puede filtar por el estado de la exploracion
        if 'exploracion_estado' in p:
            self.exploracion_estado = p['exploracion_estado'] 
            del p['exploracion_estado']

        if 'tipos' in p:
            self.tipos = p['tipos'].split(',')
            for t in self.tipos:
                if t not in capturas.VALID_IMAGE_FORMATS and \
                   t not in capturas.VALID_VIDEO_FORMATS:
                    self.tipos.remove(t)
            del p['tipos']

        if not 'dicom_stored' in p and not 'dicom' in p:
            # 2.4.10 inicializa el parametro exploracion_borrada. Este indica si se mostraran las capturas que
            #        pertenezcan a una exploracion que esta borrada.
            if authorized( HasAuthKitRole(roles.borrado_logico)):
                self.mostrar_de_exploraciones_borrada = True

            # en el caso de que no sea "consultar_exploraciones_todas", filtrar solo las del usuario actual
            if not authorized( HasAuthKitRole(roles.consultar_exploraciones_todas) ):
                medico = medico_from_user(request.environ['REMOTE_USER'])
                self.medico_id = medico.id
        else:
            # La peticion esta viniendo desde Mirth, usa el usuario sysadmin
            username="sysadmin"
            medico = medico_from_user(username)
            self.cargar_exploracion_dicom = True
            if 'dicom' in p:
                # en este if pueden venir, dicom y dicom_stored
                # si viene dicom, hay que eliminarla pq no es del modelo
                del p["dicom"]
        
        return self._doIndex(p, format)

    def _filtrar_index(self, query, format= None):
        query = query.join(Captura.exploracion)
        # filtrar por medico
        if self.medico_id != None:
            query = query.filter( Exploracion.medico_id == self.medico_id )
        #query = query.order_by(Cita.fecha)  # ordenar por orden de captura

        # Filtra las capturas por su estado de exploracion
        if self.exploracion_estado != None:
            if self.exploracion_estado == False:
                query = query.filter( or_(Exploracion.borrado == 0, Exploracion.borrado == None))
            else:
                query = query.filter( Exploracion.estado == self.exploracion_estado)

        if self.tipos != None:
            # Se pueden filtrar varios tipos de capturas a la vez
            condicion = or_(*list( Captura.tipo==tipo for tipo in self.tipos ))
            query = query.filter( condicion )

        # TODO: analizar si esto es redundante, aunq este if depende del rol "borrado_logico"
        if not self.mostrar_de_exploraciones_borrada:
            query = query.filter( or_(Exploracion.borrado == 0, Exploracion.borrado == None))

        return query

    def _return_doIndex(self, registros, data, format):
        """
        amplia la info del index de capturas
        """
        for dat in data:
            ubicacion = capturas._archivo(dat['id'], 'auto')
            dat['ubicacion'] = ubicacion
            if not dat['tipo']:
                dat['tipo'] = capturas.DEFAULT_FORMAT

            # 2.4.23: Para agregar la informacion de la exploracion_dicom 
            #         dentro del objeto captura tuve que hacer esto. Fue la 
            #         unica forma de lograrlo, ya que con sqlalchemy fue imposible
            #         quizas porque la version es muy vieja. Si se actualiza 
            #         sqlalchemy quizas se podria intentar sacar este codigo y hacerlo
            #         con un relationship
            if self.cargar_exploracion_dicom:
                expl_dicom = meta.Session.query(Exploracion_dicom) \
                                    .filter(Exploracion_dicom.exploracion_id==dat['exploracion']['id']) \
                                    .first()
                dat['exploracion']['exploracion_dicom'] = self._crear_data(expl_dicom, format, expl_dicom.c.keys(), 'exploracion_id')
            
                servicio = meta.Session.query(Servicio) \
                                    .filter(Servicio.id==dat['exploracion']['servicio_id']) \
                                    .first()
                dat['exploracion']['centro'] = self._crear_data(servicio.centro, format, servicio.centro.c.keys())
                
                cita = meta.Session.query(Cita).filter(Cita.exploracion_id==dat['exploracion']['id']).first()
                if cita:
                    worklist = meta.Session.query(Work).filter(Work.cita_id==cita.id) \
                                                  .first()
                    if worklist:
                        dat['exploracion']['worklist'] = self._crear_data(worklist, format, worklist.c.keys())

        return data

    def _content_type(self, param):
        """ devuelve el content_type del archivo.
        si param es un int, se supondra que es el id, si es un str
        se supondra que sera el nombre del archivo. """
        if isinstance(param, int):
            archivo = capturas._archivo(param)
        elif isinstance(param, str):
            archivo = param
        else: raise Exception(_('parametro incorrecto en _content_type'))#IDIOMAOK
        ext = os.path.splitext(archivo)[1].upper()
        if (ext in ('.JPG', '.THUMB')): return "image/jpeg"
        elif (ext == '.BMP'): return "image/x-ms-bmp"
        elif (ext == '.PNG'): return "image/x-png"
        elif (ext == '.AVI'): return "video/avi"
        elif (ext in ('.MPG', '.TS')): return "video/mpeg"
        elif (ext in ('.WMV')): return "video/x-ms-wmv"
        else: return 'image/%s' % ext[1:]

    def _binfileiter(self, filename):
        """ para no cargar todo un fichero en memoria (con MPGs se colgaría)
            crear un iterador y usarlo para la descarga
        """
        size = 1*1024*1024 # paquetes de 1 MB...
        f = file(filename, 'rb')
        try:
            while True:
                buffer = f.read(size)
                if buffer:
                    yield buffer
                else:
                    break
        finally:
            f.close()

    # Desactivado para integración HUCA
    @conditional_authorize(HasAuthKitRole([roles.consultar_exploraciones_todas]))
    def show(self, id, format='auto'):
        format = format.lower()
        self.format=format

        captura = self._registro_by_id(id)

        # Verifica si esta autorizado cuando la exploracion esta borrada
        if is_exploracion_borrada(captura.exploracion.id) and not authorized( HasAuthKitRole(roles.borrado_logico)):
            abort(400, _(u'No es posible visualizar la captura porque la exploración se encuentra borrada'))#IDIOMAOK

        if format == 'xml':
            response.content_type = "text/xml"
            data = self._crear_data(captura, format)
            root = obj_to_xml(data, self.nombre_recurso, self.nombre_recursos)
            return tostring(root)

        archivo = None
        if format in ('auto',) + capturas.VALID_FORMATS:
            archivo = capturas._archivo(captura.id, format)
            if not archivo:
                archivo = capturas.obtener_del_pacs(captura)

        elif format == 'thumb':
            archivo = capturas._archivo(captura.id, 'thumb', create = True)

        if not archivo: 
            # el archivo no esta ni en el almacenamiento local ni
            # en el pacs, por lo tanto es un error de aplicacion
            # nunca tendria que pasar esto.
            log.error(_('No se ha encontrado la captura id: %s' % (str(captura.id)) ))#IDIOMAOK
            abort(self.format, 404, _('No se ha encontrado la captura'))#IDIOMAOK

        # registra la consulta de la imagen (los .thumb no)
        if format in ('auto', 'bmp', 'jpg', 'mpg', 'avi', 'ts', 'wmv'):
            username = request.environ.get('REMOTE_USER', registro.DEFAULT_REMOTE_USER)
            ipaddress = obtener_request_ip(request)
            registro.nuevo_registro(username, ipaddress, captura.exploracion, registro.eventos.mostrar,
                                    registro.res.captura, 'ID', str(captura.id), None)

        response.content_type = self._content_type(archivo)
        response.headers['content-length'] = os.path.getsize(archivo)
        return self._binfileiter(archivo)

    @conditional_authorize(HasAuthKitRole([roles.consultar_exploraciones_todas]))
    def create(self):
        # crear el archivo de imagen
        ruta = config['pylons.paths']['capturas']

        # Comprueba que la exploracion no este eliminada logicamente.
        if 'webob._parsed_post_vars' in request.environ:
            exploracion_id = request.environ['webob._parsed_post_vars'][0]['exploracion_id']
        else:
            exploracion_id = request.params['exploracion_id']
        if is_exploracion_borrada(exploracion_id):
            abort(self.format, 400, _(u'La exploración se encuentra borrada'))#IDIOMAOK

        if 'uuid' in request.params:
            # Create mediante EWC

            # Metodo de Precreacion de la imagen sin estar disponible en el servidor
            # Esto es necesario para el EWC ya que primero se crean en el REST y 
            # luego se envian los chunks
            uuid = request.params['uuid']

            # Buscar si existe una imagen con ese uuid, si ya existe no lo creo.
            q = meta.Session.query(Captura).filter(Captura.uuid == uuid)

            if q.count()>0:
                abort_xml(400, _(u'Ya existe una captura con ese UUID ya existe'))#IDIOMAOK

            ext = request.params['archivo'].split('.')[1]
            id = capturas._create_reg(self.tabla,exploracion_id, ext, uuid)


            resp = {'id':id}
            response.status_code = 200
            response.content_type = 'application/json'
            return simplejson.dumps(resp)

        else:
            # Create mediante formulario
            if 'webob._parsed_post_vars' in request.environ:

                # metodo nuevo, usando multipart
                params = request.environ['webob._parsed_post_vars'][0]

                fieldstorage = params['archivo']
                ext = get_extension(fieldstorage.filename)
                if ext not in capturas.VALID_FORMATS:
                    abort(400, _(u'La extensión del archivo no es válida: "%s"') % ext)#IDIOMAOK

                id = capturas._create_reg(self.tabla,params['exploracion_id'], ext)

                ruta = capturas._construir_ruta(ruta, None, params['exploracion_id'])
                archivo = '.'.join( (str(id), ext) )
                f = open(os.path.join(ruta, archivo), 'wb')
                shutil.copyfileobj(fieldstorage.file, f)
                fieldstorage.file.close()
                f.close()
            else:
                # TODO: verificar si no se usa mas este metodo, quizas el plugin.
                # crea la imagen desde un Base 64, 

                # metodo antiguo, con la imagen como un parametro en base64
                id = capturas._create_reg(self.tabla,request.params['exploracion_id'])
                if 'jpg' in request.params:
                    param = 'jpg'
                elif 'bmp' in request.params:
                    param = 'bmp'
                else: abort(400, _('falta el parametro con los datos de la imagen'))#IDIOMAOK
                archivo = '.'.join( (str(id), param) )

                ruta = capturas._construir_ruta(ruta, None, request.params['exploracion_id'])

                f = file(os.path.join(ruta, archivo) , 'wb')
                f.write(b64decode(request.params[param]))
                f.close()

            # Crear un thumbnail
            capturas._create_thumbnail( capturas._archivo(id) )

            response.status_code = 201
            response.content_type = "text/xml"
            root = Element(self.nombre_recurso)
            root.attrib['id'] = formatea_valor(id)
            return tostring(root)

    def update(self, id):

        # Solo se pueden modificar algunos campos especificos
        captura = self._registro_by_id(id)

        # Comprueba que la exploracion no este eliminada logicamente.
        if is_exploracion_borrada(captura.exploracion.id):
            abort(self.format, 400, _(u'La exploración se encuentra borrada'))#IDIOMAOK

        if 'SOPInstanceUID' in request.params:
            # No es necesario Login, viene del mirth
            log.info('%s - Captura ID: %s' % (_(u'Se ingreso al update de capturas mediante Mirth'),str(captura.id)))
        else:
            # Accede mediante endotools
            if not authorized(RemoteUser()):
                abort(403, _(u'El usuario no tiene permisos'))#IDIOMAOK

        p = {}

        if 'SOPInstanceUID' in request.params:
            if 'dicom_stored' in request.params:
                p['dicom_stored'] = request.params['dicom_stored']
            if 'dicom_stgcmt' in request.params:
                p['dicom_stgcmt'] = request.params['dicom_stgcmt']
            if 'SOPInstanceUID' in request.params:
                p['SOPInstanceUID'] = request.params['SOPInstanceUID']
        else:
            if 'seleccionada' in request.params:
                p['seleccionada'] = request.params['seleccionada']
            if 'comentario' in request.params:
                p['comentario'] = request.params['comentario']
            if 'orden' in request.params:
                p['orden'] = request.params['orden']
            if 'posx' in request.params:
                p['posx'] = request.params['posx']
            if 'posy' in request.params:
                p['posy'] = request.params['posy']

        
        # Traspasar capturas de una expl. a otra:
        # Internamente lo que hace es cambiar el id de exploracion en lass capturas
        # Condicion: Solamente se puede hacer cuando la exploracion
        #            tiene estado=0 y es el mismo usuario que la creo
        # Uso: Esta edicion esta hecha para poder ir hacia atras y traspasar 
        #      las capturas a otra exploracion nueva que se esta creando
        if 'exploracion_id' in request.params:
            exploracion_id = request.params['exploracion_id']
            if exploracion_id=='': #se quiere sacar la relacion entre captura y exploracion
                exploracion = captura.exploracion
            else: #se quiere asociar una exploracion con la captura
                exploracion = registro_by_id(Exploracion,exploracion_id)

            # Comprobacion de que pueda hacer ese cambio.
            username = request.environ['REMOTE_USER']
            ipaddress = obtener_request_ip(request)
            medico_conect = medico_from_user(username)
            autorizado = ( exploracion.medico_id == medico_conect.id) \
            or (authorized( HasAuthKitRole(roles.modificar_exploraciones_todas) ))
            if not autorizado:
                abort(403, _(u'No se pueden mover las imagenes a otra exploracion'))#IDIOMAOK

            # Envia el parametro porque esta autorizado
            if exploracion.estado == 0:
                p['exploracion_id'] = request.params['exploracion_id']

        if p:
            self._update_registro_from_params(captura, p)
            meta.Session.commit()
        else:
            abort(403, _('Solo se permite modificar los campos "seleccionada" "comentario" "orden"'))#IDIOMAOK

    @conditional_authorize(RemoteUser())
    def delete(self, id):
        # No permitir eliminar capturas
        response.status_code = 405
        return _('ERROR: No se puede eliminar una captura')#IDIOMAOK

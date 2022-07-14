import os
import json
from PIL import Image
import shutil
import logging
from datetime import date, datetime, timedelta
from random import randint
import time
from pylons.i18n import _
from xml.etree.ElementTree import Element, SubElement, tostring
from sqlalchemy.sql import join
from authkit.authorize.pylons_adaptors import authorized, authorize, authorize_request, NotAuthorizedError
from authkit.permissions import RemoteUser, ValidAuthKitUser, UserIn, HasAuthKitRole, And
from base64 import b64decode
import pydicom
from pydicom.dataset import Dataset, FileDataset

from endotools.model import meta
from endotools.model.capturas import Captura
from endotools.model.citas import Cita
from endotools.model.worklist import Work
from endotools.model.exploraciones import Exploracion
from endotools.model.configuraciones import Configuracion
from endotools.lib.misc import *
from endotools.lib.genericREST import *
from endotools.lib.pydcmtk.pydcmtk import *
import endotools.lib.registro as registro
from endotools.lib.pydicom_wrapper.dcmfile import DCMFile
from endotools.lib.pydicom_wrapper.qr import QRRequest
from endotools.lib.pydcmtk_wrapper.convert import DCMTKConvert

log = logging.getLogger(__name__)

VALID_IMAGE_FORMATS = ('jpg', 'jpeg', 'bmp', 'png')
VALID_VIDEO_FORMATS = ('avi', 'mpg', 'ts', 'wmv')
VALID_FORMATS = VALID_IMAGE_FORMATS + VALID_VIDEO_FORMATS
DEFAULT_FORMAT = 'jpg'
DEFAULT_THUMB_IMG = 'unknown.png'
DEFAULT_THUMB_VID = 'video_thumb.png'

def get_by_id(id):
    q = meta.Session.query(Captura).filter(Captura.id == id)
    if q.count():
        return q.one()
    else:
        return None

def _create_thumbnail(nombre_imagen):
    """
    Genera el thumbnail si es una imagen jpg o bmp... si es otra cosa (avi, mpg...)
    no hace nada
    """
    extension = get_extension(nombre_imagen)
    if (extension in VALID_IMAGE_FORMATS):
        img = Image.open(nombre_imagen)
        img.thumbnail((96, 72))
        if img.mode in ('RGBA', 'LA'):
            img.convert('RGB')
        img.save( os.path.splitext(nombre_imagen)[0] + '.thumb', 'JPEG')

def _archivo(id, ext = None, create = False):
    """ Devuelve el nombre del archivo (con la ruta), o None si no existe.
        * si se indica 'ext' solo se devolvera el archivo con esa extension.
        * si se indica 'ext="auto"' entonces buscará automaricamente JPG/JPEG, 
          BMP y MPG, en ese orden
        * si se indica 'ext="thumb"' entonces buscar el thumbnail.
        * si se indica 'create=True' entonces si no encuentra el thumb lo 
          creará.
        * si no existe se puede obtener del PACS. (no implementado)
    """
    ruta = config['pylons.paths']['capturas']
    ruta_subcategoria = _construir_ruta(ruta, id)
    # comprobar si existe el jpg
    if not ext or ext.upper() in ('AUTO', 'JPG', 'JPEG'):
        archivo = '.'.join( (str(id), 'jpg') )
        if os.path.exists( os.path.join(ruta_subcategoria, archivo) ):
            return os.path.join(ruta_subcategoria, archivo)
        elif os.path.exists( os.path.join(ruta, archivo) ):
            return os.path.join(ruta, archivo)
        archivo = '.'.join( (str(id), 'jpeg') )
        if os.path.exists( os.path.join(ruta_subcategoria, archivo) ):
            return os.path.join(ruta_subcategoria, archivo)
        elif os.path.exists( os.path.join(ruta, archivo) ):
            return os.path.join(ruta, archivo)

    # comprobar si existe el bmp
    if not ext or ext.upper() in ('AUTO', 'BMP'):
        archivo = '.'.join( (str(id), 'bmp') )
        if os.path.exists( os.path.join(ruta_subcategoria, archivo) ):
            return os.path.join(ruta_subcategoria, archivo)
        elif os.path.exists( os.path.join(ruta, archivo) ):
            return os.path.join(ruta, archivo)

    # comprobar si existe el png
    if not ext or ext.upper() in ('AUTO', 'PNG'):
        archivo = '.'.join( (str(id), 'png') )
        if os.path.exists( os.path.join(ruta_subcategoria, archivo) ):
            return os.path.join(ruta_subcategoria, archivo)
        elif os.path.exists( os.path.join(ruta, archivo) ):
            return os.path.join(ruta, archivo)

    # comprobar si existe el mpg
    if not ext or ext.upper() in ('AUTO', 'MPG'):
        archivo = '.'.join( (str(id), 'mpg') )
        if os.path.exists( os.path.join(ruta_subcategoria, archivo) ):
            return os.path.join(ruta_subcategoria, archivo)
        elif os.path.exists( os.path.join(ruta, archivo) ):
            return os.path.join(ruta, archivo)

    # comprobar si existe el ts
    if not ext or ext.upper() in ('AUTO', 'TS'):
        archivo = '.'.join( (str(id), 'ts') )
        if os.path.exists( os.path.join(ruta_subcategoria, archivo) ):
            return os.path.join(ruta_subcategoria, archivo)
        elif os.path.exists( os.path.join(ruta, archivo) ):
            return os.path.join(ruta, archivo)

    # comprobar si existe el avi
    if not ext or ext.upper() in ('AUTO', 'AVI'):
        archivo = '.'.join( (str(id), 'avi') )
        if os.path.exists( os.path.join(ruta_subcategoria, archivo) ):
            return os.path.join(ruta_subcategoria, archivo)
        elif os.path.exists( os.path.join(ruta, archivo) ):
            return os.path.join(ruta, archivo)

    # comprobar si existe el wmv
    if not ext or ext.upper() in ('AUTO', 'WMV'):
        archivo = '.'.join( (str(id), 'wmv') )
        if os.path.exists( os.path.join(ruta_subcategoria, archivo) ):
            return os.path.join(ruta_subcategoria, archivo)
        elif os.path.exists( os.path.join(ruta, archivo) ):
            return os.path.join(ruta, archivo)

    # comprobar si existe el thumbnail
    if ext and ext.upper() in ('THUMB',):
        archivo = '.'.join( (str(id), 'thumb') )

        if os.path.exists( os.path.join(ruta_subcategoria, archivo) ):
            return os.path.join(ruta_subcategoria, archivo)
        elif os.path.exists( os.path.join(ruta, archivo) ):
            return os.path.join(ruta, archivo)
        elif create:    
            # Si no existe Y se ha indicado 'create' => generar el thumbnail
            a = _archivo(id)
            
            # XXX puede ser que la imagen este en el PACS, pero no la voy a
            # descargar solo para generar el thumbnail, asi que deberia devolver
            # un thumbnail generico. El thumb correcto ya se generará si se
            # descarga la imagen del PACS.

            # Si no esta el archivo devuelve las imagenes thumb por defecto
            if not a:
                return os.path.join(config['pylons.paths']['root'], 'res', \
                                    DEFAULT_THUMB_IMG)
            elif (get_extension(a) in VALID_VIDEO_FORMATS):
                return os.path.join(config['pylons.paths']['root'], 'res', \
                                    DEFAULT_THUMB_VID)

            # Si tiene el archivo crea el thumbnail
            _create_thumbnail(a)
            return _archivo(id, ext, False)

    # si no existe ninguno, devolver None
    return None

def _construir_ruta(ruta, captura_id = None, exploracion_id = None):
    """ Esta función ha de delvolver la ruta segun el algoritmo defenido de
        almacenamiento AÑO/MES. Si la carpeta con esa fecha no existe, la crea.
        Recibe la base de la ruta y le agrega el anio y la fecha.
        Funcionamiento:
            * Si viene captura_id o exploracion_id agarra la fecha de la 
              exploracion
            * Sino agarra el dia actual
    """

    if captura_id:
        #coger la fecha de la exploracion
        captura = registro_by_id(Captura, captura_id)
        d = captura.exploracion.fecha
    elif exploracion_id:
        exploracion = registro_by_id(Exploracion, exploracion_id)
        d = exploracion.fecha
    else:
        d = date.today()

    if os.path.exists(ruta):
        # add year
        ruta = os.path.join( ruta, str(d.year) )
        # add month
        ruta = os.path.join( ruta, str('%02d' % d.month) )

        # verificar si existe la ruta base + año + mes
        if not os.path.exists(ruta):
            # crear la ruta
            error = None
            try:
                os.makedirs(ruta)
            except WindowsError, e:
                log.error(e)
                error = e
                # Si llega hasta aqui es porque ocurrio un error de Windows.
                # Se analiza si la ruta esta creada. Si bien se controla con el 
                # "if os.path.exists" puede pasar que si hay dos peticiones de
                # CREATE de capturas en simultaneo las dos entren al if pero 
                # una pueda crear el directorio y la otra de un error ya 
                # que fue creada por la primera que entro 
            if error:
                # si hay un error y no existe la ruta entonces hay que mostrarlo
                # ya que no es un error de simultaneidad de peticiones
                if not os.path.exists(ruta):
                    raise Exception(str(e))

    return ruta

def _create_reg(tabla, exploracion_id, tipo=None, uuid=None):
    nuevoRegistro = tabla()
    nuevoRegistro.exploracion_id = exploracion_id
    nuevoRegistro.seleccionada = False
    nuevoRegistro.tipo = tipo
    nuevoRegistro.uuid = uuid
    nuevoRegistro.updated_at = datetime.datetime.now()
    if uuid is not None:
        nuevoRegistro.disponible = 0
    else:
        nuevoRegistro.disponible = 1
    meta.Session.save(nuevoRegistro)
    meta.Session.commit()
    return nuevoRegistro.id

def _set_disponible(tabla, uuid):
    q = meta.Session.query(tabla).filter(tabla.uuid == uuid)
    if q.count():
        captura = q.one()
        captura.disponible=True
        meta.Session.update(captura)
        meta.Session.commit()
    else:
        return None


def _get_captura_by_uuid(tabla, uuid):
    q = meta.Session.query(tabla).filter(tabla.uuid == uuid)
    if q.count():
        return q.one().id
    else:
        return None

def _mover_capturas_ruta_correcta():
    """ Busca los archivos que estan en la carpeta base de capturas
        que sean de un formato valido y intenta moverlos a la carpeta correcta
        creada por la funcion _construir_ruta. Si el archivo no corresponde
        con ningun objeto captura de base de datos entonces los coloca en una
        carpeta con nombre especial "desconocidas"
    """
    
    count_moved = 0
    # obtengo los archivo en el directorio base
    base_dir = config['pylons.paths']['capturas']
    archivos_basedir = []
    if os.path.exists(base_dir):
        archivos_basedir = os.listdir(base_dir)

    desconocidos = []
    for archivo in archivos_basedir:
        archivo_origen = os.path.join(base_dir, archivo)
        if os.path.isfile(archivo_origen):
            
            if get_extension(archivo_origen) in VALID_FORMATS:

                try:
                    captura_id = int(archivo.split(".")[0])
                except Exception,e:
                    captura_id = None
                    log.error(e)

                if captura_id!=None:
                    try:
                        archivo_destino = os.path.join(_construir_ruta(base_dir, captura_id), archivo)
                    except Exception,e:
                        log.error(e)
                        archivo_destino = None

                    if archivo_destino: 
                        shutil.move(archivo_origen, archivo_destino)
                        log.info("[Tarea de organizacion de capturas] " + archivo_origen + " >> " + archivo_destino )
                        count_moved += 1 

                        thumb_filename = str(captura_id) + ".thumb"
                        thumb_origen = os.path.join(base_dir, thumb_filename)
                        if os.path.exists(thumb_origen):
                            thumb_destino = os.path.join(_construir_ruta(base_dir, captura_id), thumb_filename)
                            shutil.move(thumb_origen, thumb_destino)
                            log.info("[Tarea de organizacion de capturas] " + thumb_origen + " >> " + thumb_destino)
                    else:
                        # no es un id que se encuentre en la base de datos.
                        desconocidos.append(archivo_origen) 
                else:
                    # no es un archivo valido de captura
                    desconocidos.append(archivo_origen) 
            else:
                # no es un formato valido
                desconocidos.append(archivo_origen) 

    log.info("[Tarea de organizacion de capturas] Se movieron: " + str(count_moved) + " archivos " )

    for d in desconocidos:
        log.info("[Tarea de organizacion de capturas] No se movio (desconocido): " + d)
    log.info("[Tarea de organizacion de capturas] Desconocidos: " + str(len(desconocidos)) + " archivos " )

    return count_moved 


def _purgar_capturas_pacs():
    #import pdb
    #pdb.set_trace()
    try:
        days = int(config.get('PURGADO.MAXIMO'))
    except Exception,e:
        log.error(e)

    q = meta.Session.query(Captura)
    q = q.filter(Captura.dicom_stored == 1)
    q = q.filter(Captura.dicom_stgcmt ==1)
    q = q.filter(Captura.disponible == 1)
    q = q.filter(Captura.updated_at  < date.today() - timedelta(days=days))
    
    
    ruta = config['pylons.paths']['capturas']

    deleted_count=0
    for captura in q :
        try:
            ruta_subcategoria = _construir_ruta(ruta, captura.id)
            archivo = '.'.join( (str(captura.id), captura.tipo))
            filepath = os.path.join(ruta_subcategoria, archivo)
        except Exception,e:
            log.error(e)

        deleted_ids=[]
        if(os.path.exists(filepath)):
            try:
                os.remove(filepath)
                captura.disponible=0
                log.info("[Purgado de ficheros en pacs] Se elimina el fichero:" + archivo)
                deleted_count += 1
            except Exception,e:
                log.error( e)

    try:
        if deleted_count>0:
            meta.Session.commit()
    except Exception,e:
        log.error(e)

        


def generate_instance_uid():
    """ Genera un uid unico para SeriesInstanceUID y 
        SOPInstanceUID
    """
    start = 100000000000000000000000000000000000000
    end = 999999999999999999999999999999999999999
    prefix = "2.25."
    nro = randint(start,end)
    return prefix + str(nro)

def obtener_del_pacs(captura):
    # si el archivo no existe en local, intenta
    archivo = _obtener_del_pacs(captura)
    if archivo:
        # encontro el archivo en el pacs, 
        #por lo que o pongo como disponible
        captura.disponible=1
        captura.updated_at = datetime.datetime.now()
        meta.Session.update(captura)
        meta.Session.commit()
    return archivo

def _obtener_del_pacs(captura):
    import time
    if captura.dicom_stored and captura.SOPInstanceUID:
        # Si tiene dicom stored y un UID identificatorio, 
        # entonces si esta almacenado en el pacs, y se podria

        # datos del worklist para hacer la llamada
        worklist = meta.Session.query(Work).filter(Work.cita_id==captura.exploracion.cita.id)
        worklist = worklist.one()

        # configuraciones de rutas de archivos temporales y finales
        ruta = config['pylons.paths']['capturas']
        ruta = _construir_ruta(ruta, captura.id)
        archivo_destino = '.'.join( (str(captura.id), captura.tipo) )
        archivo_destino_temp = '.'.join( (archivo_destino, 'dicomized.'+ captura.tipo) )
        archivo_destino_temp_dcm = '.'.join( (captura.SOPInstanceUID, 'dcm') )
        ruta_destino = os.path.join(ruta, archivo_destino)
        ruta_destino_temp = os.path.join(ruta, archivo_destino_temp)
        ruta_destino_temp_dcm = os.path.join(ruta, archivo_destino_temp_dcm)

        # Leer configuraciones de worklist de la tabla configuraciones.
        confs_qr = meta.Session.query(Configuracion).filter(Configuracion.clave=='queryretrieve').one()
        if not confs_qr:
            abort(self.format,400, _(u'No hay configuraciones para el QR'))#IDIOMAOK
                        
        # Niveles: 1: centro, 2: servicio, 3:agenda
        # busca la cita de esa captura, para luego analizar que configuracion de queryretrieve usar
        expl_id = captura.exploracion.id
        cita = None
        try:
            cita = meta.Session.query(Cita).filter(Cita.exploracion_id==expl_id).first()
        except Exception, e:
            log.error("[_obtener_del_pacs] No hay cita para la exploracion de la que se quiere obtener la captura %s" % (str(expl_id)))
            log.error("[_obtener_del_pacs] %s " % (str(e)))
            return None
            
        if not cita.agenda:
            log.error("[_obtener_del_pacs] No hay agenda (expl_id: %s, cita_id: %s" % (str(expl_id), str(cita.id)))
        
        obj_nivel = {}
        obj_nivel['3'] = cita.agenda
        obj_nivel['2'] = cita.agenda.servicio
        obj_nivel['1'] = cita.agenda.servicio.centro
        current_conf = {'level': 0}
            
        try:
            # carga el valor del queryretrieve
            confs_dict = byteify(json.loads(confs_qr.valor))
        except Exception,e:
            log.error("[_obtener_del_pacs] Error al leer json de configuracion")
            return None
        
        for conf in confs_dict["queryretrieve"]:
            # leer las configuraciones. Tomará la que más prioridad tenga Agenda>Servicio>Centro
                               
            # - Si ya tiene un nivel mayor en current -> no hace nada.
            # - Si aparece un nivel > en conf_dict -> asigna a ese como
            #   current
            # - AND -> tienen que coincidir los ID del nivel. Si el usuario
            #   esta pidiendo citas del servicio 1 (ej: dig) entonces 
            #   el 'nivel_id' de la configuracion tiene que ser 1, sino no
            #   lo asigna 
            if current_conf['level'] < conf['level'] and \
               obj_nivel[str(conf['level'])].id == conf['level_id'] :
                current_conf = conf

        if current_conf['level'] == 0:
            log.error("[_obtener_del_pacs] El queryretrive no esta configurado correctamente")
            return None
            
        # hacer el query retrieve
        qr = QRRequest(current_conf, 'c-move')
        qr.get_image(worklist.patientID,\
                     worklist.studyInstanceUID, \
                     captura.exploracion.SeriesInstanceUID, \
                     captura.SOPInstanceUID, \
                     ruta)
                     
        # si no termino
        if not qr.is_finished():
            log.error("[_obtener_del_pacs]qr not finished: captura id "+str(captura.id))
            return None
            
        # si no se almaceno
        if not qr.is_stored():
            log.error("[_obtener_del_pacs]qr not stored: captura id "+str(captura.id))
            return None
            
        # convertir dcm to jpg imagen
        converted = False
        try:
            # intenta con pydicom
            dcmfile = DCMFile(dcmpath=ruta_destino_temp_dcm)
            dicomized_file = dcmfile.convert(ruta_destino_temp, captura.tipo)
            converted = True
        except Exception,e:
            log.info(str(e))

        if not converted:
            #intenta con dcmtk
            try:
                dcmtk_bin_path = os.path.join(config['pylons.paths']['root'], 'lib','pydcmtk_wrapper','bin')
                dcmtk = DCMTKConvert(dcmtk_bin_path)
                dicomized_file = dcmtk.convert_dcm2bmp2jpg(ruta_destino_temp_dcm, ruta_destino)
                converted=True
            except Exception,e:
                log.error(str(e))

        if converted:
            # mover temporal dicomizado a la ruta de capturas    
            shutil.move(dicomized_file, ruta_destino)
            os.remove(ruta_destino_temp_dcm)

            # llamar a _archivo
            return _archivo(captura.id, captura.tipo)
        else:
            return None
    else:
        return None
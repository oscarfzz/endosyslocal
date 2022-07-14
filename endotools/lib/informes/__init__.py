"""
Se ha reestructurado el código de generación de informes. Anteriormente estaba
en lib/informes.py. Ahora está en la carpeta lib/informes/, para poder organizar
mejor en mas de un archivo.

En lib/informes/legacy/informes.py está el mismo fichero utilizado anteriormente

de momento tiene el mismo comportamiento que antes, se exportan las funciones de
legacy, tal cual.

Hasta ahora se usaban estas dos funciones:

  get_plantillas()      Devuelve un array con todas las plantillas de informe.
  generar_informe()  Devuelve el informe en formato string (html).

Uso:
  generar_informe()  controllers/check.py
                        controllers/rest/informes.py:InformesController.create()

generar_informe() requeria que la plantilla sea un archivo HTML y devolvia un
string que es ese mismo HTML con las variables correspondientes a la exploracion
indicada.

En el caso de MS Word, la idea es que solo se permita el formato final PDF, por
lo que generar_informe() no devolverá ni HTML ni DOC, sino PDF directamente.

TODO:
    -Distinguir plantillas Word y HTML (.doc, .docx y .htm) ¿?

"""

from pylons.i18n import _
import os
import shutil
from pylons import config
import msword
import openoffice
import legacy
import legacy.informes
import logging
import endotools.model as model
from endotools.lib.misc import *
import tempfile
import uuid
from valores import get_valores
from endotools.model.informes import Informe
from endotools.model import meta

log = logging.getLogger(__name__)

def get_plantillas(exploracion_id = None):
    """
    De momento es básicamente la misma función anterior.

    Devuelve un array con todas las plantillas de informe.
    Se devuelven los nombres de archivo con la extensión, pero sin la ruta.
    Se devuelven TODOS los archivos, de cualquier extensión, excepto los que
    empiezan por "_".

    NUEVO:
    Se devuelven los nombres de archivo con la extensión Y con la ruta.
    Ahora pueden haber subcarpetas para organizar las plantillas.
      raiz: Las plantillas de la raiz SIEMPRE se mostrarán.
      carpetas:
        Tipo expl:  Si una carpeta tiene exactamente el mismo nombre que un tipo
                    de exploración, las plantillas sólo se mostrarán para el mismo.
                    TODO: lo ideal sería que cada tipo de expl tuviera un CODIGO,
                    para usarlo de nombre de carpeta.
        servicio:   Si una carpeta tiene como nombre el codigo de un servicio,
                    solo se mostrarán las plantillas si el tipo de expl. pertenece
                    al servicio indicado. AUN NO IMPLEMENTADO
        centro:     Si una carpeta tiene como nombre el codigo de un centro,
                    solo se mostrarán las plantillas si la expl. se ha realizado
                    en el centro indicado.
    nombres archivo:
        Opción para que si una plantilla tiene exactamente el mismo nombre que
        un tipo de exploración, solo aparezca para dicho tipo de expl. El archivo
        puede estar en una subcarpeta (p.e. de un servicio o centro).

        Además todos los que empiezan por "_" o "~" no se muestran.
        Si empieza por ".~", ya que puede ser un temporal de OpenOffice.


    """

    lista = []

    tipos_exploracion = []
    for r in meta.Session.query(model.TipoExploracion).all():
        tipos_exploracion.append(r.nombre.upper())

    exploracion = None
    if exploracion_id:
        exploracion = registro_by_id(model.Exploracion, exploracion_id)

    def anadir_plantillas(dirpath, files):
        """
        añade las plantillas, excepto:
            -las que empiezan por "_" o "~"
        """
        p = dirpath.replace(ruta, '').lstrip('\\/') # se ha de quitar también la barra del principio
        for f in files:
            if f.startswith('_') or f.startswith('~') or f.startswith('.~'): continue
            if exploracion and exploracion.tipoExploracion:
                filename = os.path.splitext(f)[0].upper()
                if filename in tipos_exploracion:
                    if filename != exploracion.tipoExploracion.nombre.upper(): continue
            #lista.append(f)
            lista.append(os.path.join(p, f))

    ruta = config['pylons.paths']['custom_informes_templ']
    for dirpath, dirs, files in os.walk(ruta):
        # raiz
        if dirpath == ruta:
            anadir_plantillas(dirpath, files)

        # raiz/CENTRO
        if exploracion and exploracion.servicio.centro:
            if dirpath == os.path.join(ruta, exploracion.servicio.centro.codigo):
                anadir_plantillas(dirpath, files)

        # raiz/TIPOEXPL
        if exploracion and exploracion.tipoExploracion:
            if dirpath.upper() == os.path.join(ruta, exploracion.tipoExploracion.nombre).upper():
                anadir_plantillas(dirpath, files)

        # raiz/CENTRO/TIPOEXPL
        if exploracion and exploracion.servicio.centro and exploracion.tipoExploracion:
            if dirpath.upper() == os.path.join(ruta, exploracion.servicio.centro.codigo, exploracion.tipoExploracion.nombre).upper():
                anadir_plantillas(dirpath, files)

    return lista


def previsualizar_para_firmar(exploracion, plantilla, imagenes = None):
    """
    Genera un informe pero no lo guarda en la carpeta de informes, sino en una
    carpeta temporal, con un nombre generado automaticamente. se usa como previsualización.
    Asi el cliente puede firmarlo y devolverlo al servidor.

    NOTA: de momento solo se permite para generados por MS Word y OpenOffice, en PDF.

        exploracion         registro de sqlalchemy de la Exploracion

        plantilla           ruta completa al fichero de la plantilla a usar

        imagenes            lista de ids de Capturas que se usaran en el informe

    devueve un dict con esta info:
        content     el contenido del pdf
        size        el tamaño del pdf
    """
    ext = os.path.splitext(plantilla)[1].upper()
    if not ext in ('.DOC', '.DOCX', '.ODT'):
        raise Exception('previsualizar_para_firmar(): Solo admite plantillas .DOC, .DOCX o .ODT')

    uuid_str = uuid.uuid4().hex
    # generar un nombre de archivo aleatorio, en la carpeta temporal del sistema por defecto
    # luego se elimina automaticamente. El archivo con marca de agua no se elimina
    nombre_archivo = os.path.join( tempfile.gettempdir(), uuid_str + '.pdf')

    try:
        if ext in ['.DOC', '.DOCX']:
            msword.generar_informe_msword(nombre_archivo, exploracion, plantilla, imagenes)
        elif ext in ['.ODT']:
            openoffice.generar_informe_openoffice(nombre_archivo, exploracion, plantilla, imagenes, True, None)

        # XXX aqui el PDF debe existir... asegurarse de que MS Word o OpenOffice lo hayan cerrado.
        pdfinfo = {}
        f = file(nombre_archivo, 'rb')
        pdfinfo['content'] = f.read()
        f.close()
        pdfinfo['size'] = os.path.getsize(nombre_archivo)
    finally:
        # el archivo con marca de agua no se elimina, se elimina desde otro lado
        if os.path.exists(nombre_archivo): os.remove(nombre_archivo)

    # Solo si es odf devuelve el uuid, para los otros formatos no esta soportado
    if ext in ['.ODT']:
        return pdfinfo, uuid_str
    else:
        return pdfinfo


def generar_informe(informe):
    """
    Genera un informe, utilizando el antiguo método por HTML, el nuevo por MS Word,
    o el nuevo por OpenOffice, según la extensión de la plantilla.

    informe:    es el registro sql alchemy de la tabla Informes. Normalmente este
                registro se acaba de crear, y se llama a generar_informe() para
                crear el fichero correspondiente.
    """
    ext = os.path.splitext(informe.plantilla)[1].upper()
##  print 'EXTENSION DE LA PLANTILLA', ext

    # nombre del archivo de informe, sin la extension (se añade luego segun el tipo)
    nombre_archivo = nombre_archivo_informe(informe, None, True)

    if ext in ['.HTM', '.HTML']:
        _generar_informe_from_html(informe)
    elif ext in ['.DOC', '.DOCX']:
        nombre_archivo = '.'.join((nombre_archivo, 'pdf'))
        msword.generar_informe_msword(nombre_archivo, informe.exploracion, informe.plantilla, informe.rel_capturas)
    elif ext in ['.ODT']:  # .sxw?
        nombre_archivo = '.'.join((nombre_archivo, 'pdf'))
        return openoffice.generar_informe_openoffice(nombre_archivo, informe.exploracion, informe.plantilla, informe.rel_capturas, False, informe)


def _generar_informe_from_html(informe):
    """
    Es la forma antigua de hacerlo. La plantilla es un HTML y se genera el
    informe también en formato HTML. Además se genera otro informe HTML con
    las referencias (imágenes, recursos, etc...) correctas para abrirlo de
    forma local, que se utiliza para convertir a PDF mediante la lib PISA.

##  Por último se genera una versión "alternativa" del informe usada si
##  hay un plugin de informes, para integraciones. Solo se usa en HUCA.
##  La función devuelve este informe alternativo.

    NUEVO:  además ya se genera el PDF y se guarda junto al HTML. Asi no se
            tiene que estar creando cada vez que se consulta. Esto lo hace
            la funcion legacy.html_to_pdf()

    informe:    registro sql alchemy de la tabla Informes
    """
    # genera el informe
    # y guardarlo a un archivo .html
    nombre_archivo = nombre_archivo_informe(informe, 'html')
    contenido_informe_html = legacy.informes.generar_informe_html(informe.exploracion, informe.plantilla, informe.rel_capturas, local = False)
    f = file(nombre_archivo, 'wb')
    # XXX el prefijo de UTF-8 para archivos de texto, no estoy seguro de que sea correcto hacerlo asi, a mano
    f.write("\xef\xbb\xbf")
    f.write(contenido_informe_html)
    f.close()


    # generar el informe con las rutas de imagenes locales (para luego generar el pdf)
    # y guardarlo a un archivo .local.html
    nombre_archivo = nombre_archivo_informe(informe, 'local.html')
    contenido_informe_html_local = legacy.informes.generar_informe_html(informe.exploracion, informe.plantilla, informe.rel_capturas, local = True)
    f = file(nombre_archivo, 'wb')
    # XXX el prefijo de UTF-8 para archivos de texto, no estoy seguro de que sea correcto hacerlo asi, a mano
    f.write("\xef\xbb\xbf")
    f.write(contenido_informe_html_local)
    f.close()

    # NUEVO: generar y guardar ya el archivo PDF a partir del .local.html
    pdfinfo = legacy.html_to_pdf(informe)


def guardar_pdf_en_carpeta(informe):
    """
    guardar una copia adicional del PDF en una carpeta, si esta configurado asi en el ini.
    Esto se utiliza para integraciones, de forma que el sistema del hospital recoja esta
    copia del informe y lo adjunte a sus archivos de historia clinica.
    El archivo .pdf tiene que existir.

    informe:    registro sql alchemy de la tabla Informes
    """
    guardar_pdf = config.get('INFORME_PDF.GUARDAR', '0') == '1'
    if not guardar_pdf: return
    

    centros_pdf = config.get('INFORME_PDF.CENTROS', '') 

    if centros_pdf != "":
        centros = centros_pdf.split(",")
        if informe.exploracion.servicio.centro.codigo not in centros:
            return
            
            
            
    try:
        carpeta_pdf = config.get('INFORME_PDF.CARPETA', '')
        nombre_pdf = config.get('INFORME_PDF.NOMBRE_ARCHIVO', '').replace('$', '%')
        ruta = os.path.join(carpeta_pdf, '')
        log.debug('ruta pdf: %s', ruta)

        # GENERAR EL NOMBRE SEGUN EL INI
        accessionNumber = '(SIN_CITA)'
        if informe.exploracion.cita and informe.exploracion.cita.work:
            accessionNumber = str(informe.exploracion.cita.work.accessionNumber)

        admissionID = '(SIN_CITA)'
        if informe.exploracion.cita and informe.exploracion.cita.work:
            admissionID = str(informe.exploracion.cita.work.admissionID)

        numero_cita = '(SIN_CITA)'
        if informe.exploracion.cita and informe.exploracion.cita.ex:
            numero_cita = str(informe.exploracion.cita.ex.numero_cita)
            
        numero_episodio = '(SIN_CITA)'
        if informe.exploracion.cita and informe.exploracion.cita.ex:
            numero_episodio = str(informe.exploracion.cita.ex.numero_episodio)
            
        numero_peticion = '(SIN_CITA)'
        if informe.exploracion.cita and informe.exploracion.cita.ex:
            numero_peticion = str(informe.exploracion.cita.ex.numero_peticion)
            
        nombre_params = {
            'id':               formatea_valor(informe.id).replace('/', '-'),
            'numero_informe':   formatea_valor(informe.numero).replace('/', '-'),
            'apellido1':        formatea_valor(informe.exploracion.paciente.apellido1).replace('/', '-'),
            'apellido2':        formatea_valor(informe.exploracion.paciente.apellido2).replace('/', '-'),
            'nombre':           formatea_valor(informe.exploracion.paciente.nombre).replace('/', '-'),
            'historia':         formatea_valor(informe.exploracion.paciente.idunico).replace('/', '-'),
            'tipoExploracion':  formatea_valor(informe.exploracion.tipoExploracion.nombre).replace('/', '-'),
            'codTipoExploracion':formatea_valor(informe.exploracion.tipoExploracion.codigo).replace('/', '-'),
            'numero':           formatea_valor(informe.exploracion.numero).replace('/', '-'),
            'fecha':            formatea_valor(informe.exploracion.fecha).replace('/', '-'),
            'servicio_codigo':  formatea_valor(informe.exploracion.servicio.codigo).replace('/', '-'),
            'centro_codigo':    formatea_valor(informe.exploracion.servicio.centro.codigo).replace('/', '-'),
            'medicoUsername':   formatea_valor(informe.exploracion.medico.username).replace('/', '-'),
            'accessionNumber':  accessionNumber,
			'admissionID':  	admissionID,
            'numero_cita':      numero_cita,
            'numero_episodio':  numero_episodio,
            'numero_peticion':  numero_peticion
        }


        # ---
        # obtiene los valores de los formularios, y crea un nuevo valores con el prefijo
        # FORMVAL__ y lo copia adentro de las variables para generar el informe
        valores = get_valores(informe.exploracion, mays = True, formato = 'TEXT', informe = informe)
        new_valores = {}

        for key, value in valores.iteritems():
            new_valores["FORMVAL__"+key] = value

        nombre_params.update(new_valores)
        # ---

        nombre_informe = nombre_pdf % nombre_params
        # ###################################################

#       archivo = '.'.join( (str(nombre_informe), 'pdf') ) # XXX al usar str() daba error con las Ñ , etc...
        archivo = '.'.join( (nombre_informe, 'pdf') )
        dest = os.path.join(ruta, archivo)
        src = nombre_archivo_informe(informe, 'pdf')
        shutil.copyfile(src, dest)
        
##          except Exception as e:
    except Exception, e:
        log.error('Ha ocurrido un error guardando el informe PDF:')
        log.error(e)
    
    


def get_pdf(informe):
    """
    Si existe el archivo PDF (ya generado al crear el informe por MS Word o OpenOffice) lo
    devuelve directamente. Si no, lo intenta generar a partir del local.html.

    NUEVO:  Como al generar desde HTML ya siempre genera también el PDF, siempre
            existirá...

    devueve un dict con esta info:
        content     el contenido del pdf
        size        el tamaño del pdf
    """
    nombre_archivo = nombre_archivo_informe(informe, 'pdf')

    pdfinfo = {}
    if os.path.exists(nombre_archivo):
        # existe el archivo PDF, devolverlo
        f = file(nombre_archivo, 'rb')
        pdfinfo['content'] = f.read()
        f.close()
        pdfinfo['size'] = os.path.getsize(nombre_archivo)
##      response.headers['content-length'] = os.path.getsize(nombre_archivo)
    else:
        # no existe, generarlo a partir del local.html
        # (esto solo debería ocurrir en actualizaciones, donde tienen informes
        # anteriores solo como .local.html. de está forma la primera vez que se
        # acceda ya se guardará el PDF)
        pdfinfo = legacy.html_to_pdf(informe)

    return pdfinfo

def nombre_archivo_informe(informe, extension = None, new = False):
    """
    Devuelve el nombre del archivo del informe.
    Si no se indica extension, se devuelve sin ella.

    ATENCION: En el caso de instalaciones antiguas, que usaban plantillas HTML
    y se generaba el informe en html (.local.html), estos ficheros deberán
    mantenerse en la raiz (/data/informes/) porque si están en la subcarpeta
    año/mes/ no se generará correctamente el PDF a partir del HTML.

    """
    archivo = str(informe.id)
    if extension != None:
        archivo = '.'.join( (archivo, extension) )

    #return os.path.join(config['pylons.paths']['informes'], archivo)

    d = informe.exploracion.fecha
    ruta = config['pylons.paths']['informes']
    if new:
        #se ha creado un informe y aqui vamos a ver donde se guarda
        #siguiendo el algoritmo año/mes primero miramos si existe
        #y si no creamos la ruta

        #verificar si existe la ruta base
        if os.path.exists(ruta):
            #añadimos el año a la ruta
            ruta = os.path.join( ruta, str(d.year) )
            #añadimos el mes a la ruta
            ruta = os.path.join( ruta, str('%02d' % d.month) )

            #verficiar si existe la ruta base + año + mes
            if not os.path.exists(ruta):
                #si no existe la creamos
                os.makedirs(ruta)
    else:
        #cuando el informe ya existe y se ha de consultar
        #miramos si el informe existe en las rutas año/mes
        #si no existe lo va a buscar en la ruta raiz data/informes

        ruta_subcategoria = os.path.join( ruta, str(d.year) )
        ruta_subcategoria = os.path.join( ruta_subcategoria, str('%02d' % d.month) )

        if os.path.exists( os.path.join(ruta_subcategoria, archivo) ):
            ruta = ruta_subcategoria


    return os.path.join(ruta, archivo)

def _mover_informes_ruta_correcta():
    
    """ Busca los archivos que estan en la carpeta base de informes
        que sean de un formato valido y intenta moverlos a la carpeta correcta
    """
    
    count_moved = 0
    # obtengo los archivo en el directorio base
    base_dir = config['pylons.paths']['informes']
    archivos_basedir = []
    if os.path.exists(base_dir):
        archivos_basedir = os.listdir(base_dir)

    desconocidos = []
    for archivo in archivos_basedir:
        archivo_origen = os.path.join(base_dir, archivo)
        
        if os.path.isfile(archivo_origen):

            if get_extension(archivo_origen) in ['pdf','html']:

                try:
                    informe_id = int(archivo.split(".")[0])
                except Exception, e:
                    log.error(e)
                    # aqui entraran los .local.html, estos son tratados mas abajo
                    informe_id = None

                if informe_id!=None:
                    # obtener el informe de la base de datos
                    try:
                        informe = meta.Session.query(Informe).filter(Informe.id == informe_id).one()
                    except Exception,e:
                        log.error(e)
                        informe = None

                    if informe:
                        #existe el informe, lo muevo.
                        archivo_destino = nombre_archivo_informe(informe,'pdf', True)
                        shutil.move(archivo_origen, archivo_destino)
                        log.info("[Tarea de organizacion de informes] " + archivo_origen + " >> " + archivo_destino )
                        count_moved += 1
                        
                        # si el archivo es un html, entonces busca el .local.html y mueve ese tambien
                        local_html_origen = os.path.join(base_dir, str(informe_id) + ".local.html")
                        if os.path.exists(local_html_origen):
                            local_html_destino = nombre_archivo_informe(informe, 'local.html', True)
                            shutil.move(local_html_origen, local_html_destino)
                            log.info("[Tarea de organizacion de informes] " + local_html_origen + " >> " + local_html_destino)
                            count_moved += 1
                        
                    else:
                        # no existe en bd
                        desconocidos.append(archivo_origen)
                else:
                    # no tiene el formato de un informe_id
                    desconocidos.append(archivo_origen)
            else:
                # no es un pdf
                desconocidos.append(archivo_origen) 

    log.info("[Tarea de organizacion de informes] Se movieron: " + str(count_moved) + " archivos " )

    for d in desconocidos:
        log.info("[Tarea de organizacion de informes] No se movio (desconocido): " + d)
    log.info("[Tarea de organizacion de informes] Desconocidos: " + str(len(desconocidos)) + " archivos " )

    return count_moved 
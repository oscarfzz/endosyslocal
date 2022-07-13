import os
try:
    import Image
except ImportError:
    from PIL import Image
import datetime
import logging
import tempfile
from base64 import b64decode, b64encode

from pylons import config
import simplejson
from pylons.i18n import _
from xml.etree.ElementTree import Element, SubElement, tostring
from authkit.authorize.pylons_adaptors import authorize, authorized, NotAuthorizedError
from authkit.permissions import RemoteUser, ValidAuthKitUser, UserIn, HasAuthKitRole, And
import sqlalchemy
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.sql import or_

from endotools.lib.usuarios.seguridad import roles
from endotools.lib.misc import *
from endotools.model import meta
from endotools.model.informes import Informe, Rel_Capturas_Informes
from endotools.model.capturas import Captura
from endotools.model.exploraciones import Exploracion
from endotools.model.tiposExploracion import TipoExploracion
from endotools.model.pacientes import Paciente
from endotools.model.pacientes import Rel_Pacientes_Centros
from endotools.model.centros import Centro
from endotools.model.citas import Cita
from endotools.model.servicios import get_servicio_id
from endotools.model.servicios import Servicio
from endotools.lib.base import render
from endotools.lib.genericREST import *
from endotools.lib.formularios import FormExplData
from endotools.lib.informes import generar_informe, previsualizar_para_firmar, get_pdf, guardar_pdf_en_carpeta, nombre_archivo_informe
from endotools.lib.plugins.base import *
from endotools.config.plugins import pluginInformes
import endotools.lib.registro as registro
from endotools.lib.exploraciones import is_exploracion_borrada
from endotools.lib.capturas import obtener_del_pacs, _archivo

log = logging.getLogger(__name__)

class InformesController(GenericRESTController):

    def __init__(self, *args, **kwargs):
        GenericRESTController.__init__(self, *args, **kwargs)
        self.tabla = Informe
        self.nombre_recurso = 'informe'
        self.nombre_recursos = 'informes'
        self.campos_index = ('id', 'tipo', 'exploracion', 'plantilla', 'fecha', 'numero', 'enviado','borrado', 'comentarios')
        self.campo_orderby = Informe.numero
        self.index_vacio = True

    def _return_doIndex(self, registros, data, format):
        for informe in registros:
            a = filter(lambda i: str(i['id']) == str(informe.id), data)
            if len(a) > 0:
                informe_el = a[0]
                # añadir el TipoExploracion
                informe_el['exploracion']['tipoExploracion'] = {
                    'id':       formatea_valor(informe.exploracion.tipoExploracion_id),
                    'nombre':   formatea_valor(informe.exploracion.tipoExploracion.nombre)
                }

                # añadir info de la cita (cita_ex), si tiene (lo necesitan p.ej. en Candelaria)
                if informe.exploracion.cita and informe.exploracion.cita.ex:
                    informe_el['cita'] = {
                        'id': formatea_valor(informe.exploracion.cita.id),
                        'ex': {
                            'prestacion_cod': formatea_valor(informe.exploracion.cita.ex.prestacion_cod),
                            'prestacion_descr': formatea_valor(informe.exploracion.cita.ex.prestacion_descr)
                        }
                    }

        return data


    def _return_index_html(self, informes, format='html'):

        html = cargar_layout_main()
        html = html.replace("|ENDOTOOLS:TITULO|", _(u'Listado de informes').encode())
        html = html.replace("|ENDOTOOLS:TITULO_CONTENIDO|", _(u'Listado de informes').encode())

        centro = None
        try:
            if self.centro_codigo is not None:
                centro = meta.Session.query(Centro).filter(Centro.codigo == self.centro_codigo).one()
            elif self.centro_id is not None:
                centro = meta.Session.query(Centro).filter(Centro.id == self.centro_id).one()
            elif hasattr(self, 'COD_SERVICIO') and (self.COD_SERVICIO is not None):
                centro = meta.Session.query(Servicio).filter(Servicio.codigo == self.COD_SERVICIO).one().centro
        except sqlalchemy.exceptions.InvalidRequestError as e:
            log.error(e)
            abort(400, _(u"No se ha podido encontrar el centro.") )

        paciente = None
        try:
            if self.paciente_id != None:
                paciente = meta.Session.query(Paciente).filter(Paciente.id == self.paciente_id).one()
            elif self.paciente_idunico is not None:
                paciente = meta.Session.query(Paciente).filter(Paciente.idunico == self.paciente_idunico).one()
            elif self.paciente_nhc is not None and centro is not None:
                paciente_id = meta.Session.query(Rel_Pacientes_Centros).\
                    filter(and_(Rel_Pacientes_Centros.nhc == self.paciente_nhc,
                                Rel_Pacientes_Centros.centro_id == Centro.id)).one().paciente_id
                paciente = meta.Session.query(Paciente).filter(Paciente.id == paciente_id).one()
        except sqlalchemy.exceptions.InvalidRequestError as e:
            log.error(e)    # se lanza esta excepcion si .one() no devuelve nada, es decir, si no existe el paciente
        except Exception as e:
            log.error(e)
            raise

        h2 = ""
        if paciente:
            if config.get('IDENTIFICADORES_PACIENTE', 'idunico').upper() == 'IDUNICO' or \
                            config.get ('IDENTIFICADORES_PACIENTE', 'idunico').upper() == 'IDUNICO+NHC':
                identificador = formatea_valor(paciente.idunico)
            else:
                if centro:
                    try:
                        identificador = formatea_valor(meta.Session.query(Rel_Pacientes_Centros). \
                                                   filter(and_(Rel_Pacientes_Centros.paciente_id == paciente.id,
                                                               Rel_Pacientes_Centros.centro_id == centro.id)).one().nhc)
                    except sqlalchemy.exceptions.InvalidRequestError as e:
                        log.error(e)
                        identificador = ""
                else:
                    abort(400, _("No se ha podido obtener el centro necesario para identificar por NHC."))
            h2 = u"<em>%s</em> - %s %s %s" % (
                            formatea_valor(identificador),
                            formatea_valor(paciente.nombre),
                            formatea_valor(paciente.apellido1),
                            formatea_valor(paciente.apellido2)
                        )

        html = html.replace("|ENDOTOOLS:SUBTITULO_CONTENIDO|", h2.encode('utf-8'))



        if '_agrupado' in request.params.keys() and request.params["_agrupado"] == "si":
            # Agrupa los informes por exploracion
            informes_agrupados = {} # {'111': {exploracion: DATOS_EXPL, informes: [array de informes]}, '112'...}
            orden_exploraciones = [] # mantiene un array con el orden de las exploraciones.
            for informe in informes:
                if str(informe.exploracion.id) not in informes_agrupados.keys():
                    orden_exploraciones.append(informe.exploracion.id)
                    informes_agrupados[str(informe.exploracion.id)] = {'exploracion': None, 'informes': [], 'deshabilitado': False}
                    informes_agrupados[str(informe.exploracion.id)]["exploracion"] = informe.exploracion
                    informes_agrupados[str(informe.exploracion.id)]["deshabilitado"] = informe.exploracion.paciente.deshabilitado

                informes_agrupados[str(informe.exploracion.id)]["informes"].append(informe)

            li_exploraciones = u""
            for exploracion in orden_exploraciones:

                clase_deshabilitado = ''
                if informes_agrupados[str(exploracion)]["deshabilitado"]:
                    clase_deshabilitado = ' paciente_deshabilitado '

                #creacion de los li de los informes
                li_informes = u""
                for informe in informes_agrupados[str(exploracion)]["informes"]:



                    li_informes += u'<li class="li_informe '+clase_deshabilitado+'">'

                    if informe.tipo < 10:
                        tipo = _(u'Informe')
                    else:
                        tipo = _(u'Adjunto')

                    a_informes = u'<a href="%s" target="_blank">%s: # %s - %s: %s - %s</a>' % \
                                    ( h.url_for('formatted_rest_informe', id=informe.id, format='pdf'),
                                      tipo,
                                      formatea_valor(informe.numero),
                                       _(u'Fecha'),
                                      formatea_valor(informe.fecha),
                                      formatea_valor(informe.exploracion.tipoExploracion.nombre)
                                    )

                    '''
                    a_informes = '<a href="'+h.url_for('formatted_rest_informe', id=informe.id, format='pdf')+'" target="_blank">' + \
                                    tipo.encode() + ': #' + formatea_valor(informe.numero) + ' - ' + \
                                    _('Fecha').encode() + formatea_valor(informe.fecha) + ' - ' + \
                                    formatea_valor(informe.exploracion.tipoExploracion.nombre) + \
                                    '</a>'
                    '''

                    if informe.borrado:
                        li_informes += u'<del>%s</del>' % a_informes
                    else:
                        li_informes += a_informes

                    li_informes += u'</li>'

                #creacion  de los li de las exploraciones
                li_exploraciones += u'<li class="li_exploracion '+ clase_deshabilitado +'"><span> %s : # %s - %s: %s </span><ul>%s</ul></li>' % \
                                    (_(u"exploraci&oacute;n")[0].upper() + _(u"exploraci&oacute;n")[1:] ,
                                     formatea_valor(informes_agrupados[str(exploracion)]['exploracion'].numero),
                                     _(u'Fecha'),
                                     formatea_valor(informes_agrupados[str(exploracion)]['exploracion'].fecha),
                                     li_informes)


                #li_exploraciones += li

            if not informes:
                if paciente:
                    lis = u'<li>%s</li>' % _(u'Paciente sin informes asociados')#IDIOMAOK
                else:
                    lis = u'<li>%s</li>' % _(u'Sin informes')#IDIOMAOK

            contenido = u'<div class="endo-panel-detail listado-informes"><ul>%s</ul></div>' % li_exploraciones

            html = html.replace("|ENDOTOOLS:CONTENIDO|", contenido.encode('utf-8'))

        else:
            # NO agrupado - Para Compatiblidad anterior
            lis = ''
            for informe in informes:

                if informe.tipo < 10:
                    tipo = _('Informe')
                else:
                    tipo = _('Adjunto')
                paciente = informe.exploracion.paciente
                clase_deshabilitado = ''
                if paciente.deshabilitado:
                    clase_deshabilitado = ' class="paciente_deshabilitado" '
                s = '<li '+ clase_deshabilitado +'><a href="%s" target="%s">%s</a></li>'
                # el prefijo "formatted_" es para que use el route que permite el formato mediante
                # la extension. Ver: http://routes.readthedocs.org/en/latest/restful.html
                link =  h.url_for('formatted_rest_informe', id=informe.id, format='pdf')
                target = config.get('INFORMES.LISTADO.TARGET', '_blank')
                plantilla = os.path.splitext(formatea_valor(informe.plantilla))[0]
                tipo_expl = formatea_valor(informe.exploracion.tipoExploracion.nombre)
                num_expl = formatea_valor(informe.exploracion.numero)
                fecha_expl = formatea_valor(informe.exploracion.fecha)
                descr = '<b>%s</b> %s - %s <b> - %s </b> #%s - %s - %s' % \
                           (_(u"exploraci&oacute;n")[0].upper() + _(u"exploraci&oacute;n")[1:], num_expl, fecha_expl,
                            tipo, formatea_valor(informe.numero), formatea_valor(informe.fecha), tipo_expl)#IDIOMAX
                if informe.borrado:
                    descr = '<del>%s</del>' % descr
                s = s % (link, target, descr)
                lis = lis + s


            if not informes:
                if paciente:
                    lis = u'<li>%s</li>' % _(u'Paciente sin informes asociados')#IDIOMAOK
                else:
                    lis = u'<li>%s</li>' % _(u'Sin informes')#IDIOMAOK

            contenido = u'<div class="endo-panel-detail listado-informes"><ul>%s</ul></div>' % lis

            html = html.replace("|ENDOTOOLS:CONTENIDO|", contenido.encode('utf-8'))


        return html

    @conditional_authorize(HasAuthKitRole([roles.consultar_exploraciones_todas]))   #XXX para acceso informes Gregorio!!!
    def index(self, exploracion_id=None, paciente_id=None, format='xml'):
        # si tiene permiso para ver una exploracion, lo tiene para listar los informes
        # XXX   en el caso de que sea "consultar_exploraciones_user", filtrar solo los del usuario actual
        p = request.params
        if exploracion_id != None: p['exploracion_id'] = exploracion_id
        if paciente_id != None: p['paciente_id'] = paciente_id

        existe_paciente = False
        existe_centro = False

        if 'paciente_id' in p:
            if p["paciente_id"]!="":
                self.paciente_id = p['paciente_id']
                existe_paciente = True
            else:
                self.paciente_id = None

            del p['paciente_id']
        else:
            self.paciente_id = None

        # filtrado por datos de centro para poder usar NHC_Centro
        for campo_centro in ('centro_id', 'centro_codigo'):
            if campo_centro in p:
                if p[campo_centro] != "":
                    setattr(self, campo_centro, p[campo_centro])
                    existe_centro = True
                else:
                    setattr(self, campo_centro, None)
                del p[campo_centro]
            else:
                setattr(self, campo_centro, None)

        if 'SERVICIO' in p:
            self.COD_SERVICIO = p['SERVICIO']
            existe_centro = True
            # setattr(self, 'COD_SERVICIO',  p['SERVICIO'])
            del p['SERVICIO']

        # Si no hemos encontrado el centro, miraremos si solo existe un centro.
        if not existe_centro:
            q = meta.Session.query(Centro)
            if q.count() == 1:
                self.centro_id = q[0].id

        # filtrado por datos de paciente NHC Centro
        if 'paciente_nhc' in p:
            if p['paciente_nhc'] != "" and existe_centro:
                self.paciente_nhc = p['paciente_nhc']
                existe_paciente = True
            else:
                self.paciente_nhc = None
            del p['paciente_nhc']
        else:
            self.paciente_nhc = None

        # filtrado por datos de paciente
        if 'paciente_idunico' in p:
            if p['paciente_idunico'] != "":
                self.paciente_idunico = p['paciente_idunico']
                existe_paciente = True
            else:
                self.paciente_idunico = None
            del p['paciente_idunico']
        else:
            self.paciente_idunico = None

        if not existe_paciente and format=="html":
            html = cargar_layout_main()
            html = html.replace("|ENDOTOOLS:TITULO|", _(u'Listado de informes').encode())#IDIOMAOK
            html = html.replace("|ENDOTOOLS:SUBTITULO_CONTENIDO|", "")#IDIOMAOK
            html = html.replace("|ENDOTOOLS:TITULO_CONTENIDO|", _(u'Listado de informes').encode())#IDIOMAOK
            html = html.replace("|ENDOTOOLS:CONTENIDO|", '<div class="error-html-informes">'+_(u'Error: No se especifico el paciente').encode()+'</div>')#IDIOMAOK
            return html

        # 2.4.10
        self.mostrar_de_exploraciones_borrada = False
        if authorized( HasAuthKitRole(roles.borrado_logico)):
            self.mostrar_de_exploraciones_borrada = True

        return self._doIndex(p, format)


    def _filtrar_index(self, query, format= None):
        query = query.join(Informe.exploracion)

        if hasattr(self,'COD_SERVICIO'):
            servicio_id = get_servicio_id(codigo=self.COD_SERVICIO)
            query = query.filter( Exploracion.servicio_id == servicio_id )

        # filtrar por paciente_id (de la exploracion)
        if self.paciente_id != None:
            query = query.filter(Exploracion.paciente_id == self.paciente_id)

        # filtrar por datos del paciente (CIP/NUHSA, historia/NHC)
        if self.paciente_idunico is not None:
            query = query.filter( Exploracion.paciente.has(Paciente.idunico == self.paciente_idunico) )

        # 2.4.10
        if not self.mostrar_de_exploraciones_borrada:
            query = query.filter( or_(Exploracion.borrado == 0, Exploracion.borrado == None))

        return query


    @conditional_authorize(HasAuthKitRole([roles.informes_exploraciones_user, roles.informes_exploraciones_todas]))  # XXX para acceso informes Gregorio!!!
    def show(self, id, exploracion_id=None, format='html'):
        """
        TODO: El show no tiene en cuenta si el informe esta borrado o no.
              Solo se esta controlando en el caso de que se pida el _LAST, pero no en los otros casos.
              Si el usuario no tiene permiso para visualizar informes borrado, no tendria que mostrarse.
              Analizar si tampoco tendrian que verse si la exploración esta borrada

        si id == '_LAST' se devolverá el último informe (ordenando por 'numero').
        es útil para tener la última versión de informe de una exploracion asi:
            rest/exploraciones/N/informe/_LAST.pdf

        si id == '_PREVIEW' se previsualiza un informe. Se crea uno temporal
        a partir de la exploracion y lista de capturas indicados y se devuelve.
        """
        # XXX   en el caso de que sea "informes_exploraciones_user", comprobar el usuario
        if str(id).upper() == '_FIRMAR': # tiene que venir la exploracion_id y plantilla
            if not exploracion_id or not('plantilla' in request.params):
                abort_xml(400, u'Se requieren los parámetros "exploracion_id" y "plantilla" para firmar un informe')
            if not format in ('json'):
                abort_xml(400, u'Solo se permite el formato JSON')
            informe = None
            exploracion = registro_by_id(Exploracion, exploracion_id)

            # Obtiene las imagenes de la exploracion para incluirlas en la previsualizacion
            imagenes = meta.Session.query(Captura).filter(and_(Captura.seleccionada==True, Captura.exploracion_id==exploracion.id)).order_by(Captura.orden).all()
            imagenes_lista = map(lambda img: int(img.id), imagenes)
            pdf_para_firmar, uuid = previsualizar_para_firmar(exploracion, request.params['plantilla'], imagenes_lista)
            # Devuelve 2 versiones del pdf en base64.
            b64pdf = b64encode(pdf_para_firmar['content'])
            informes = { 'uuid': uuid , 'b64pdf': b64pdf}

            if config.get("FIRMA_ELECTRONICA.TIPO") == "viafirma":
                #la firma a través de viafirma se realiza en el propio servidor, 
                #se deberá pasarle los parametros de firma, 
                #entre los que se incluyen el fichero en base 64 la posición y texto del sello
                viafirmaParams = {
                            "autoSend": False,
                            "files": [{
                                "filename": uuid+".pdf",
                                "base64Content": b64pdf,
                                "signaturePolicy": {
                                    "signatureFormat": "PAdES_BES",
                                    "signatureType": "ATTACHED",
                                    "parameters": {
                                      "DIGITAL_SIGN_PAGE": "0",
                                      "DIGITAL_SIGN_STAMPER_HIDE_STATUS": "true",
                                      "DIGITAL_SIGN_IMAGE_STAMPER_AUTOGENERATE": "false",
                                      "SIGNATURE_ALGORITHM":"SHA256withRSA",
                                      "DIGITAL_SIGN_RECTANGLE": "{'x':10,'y':10,'height':75,'width':75}",
                                      "DIGITAL_SIGN_STAMPER_TEXT": " ",
                                    }
                                }
                            }],
                            "locale": "es",
                            "sessionId": uuid
                        }

                try:
                    import urllib2
                    viafirmaUrl= config.get("FIRMA_ELECTRONICA.URL")
                    url = viafirmaUrl+"/api/rest/services/signature"
                    auth = b64encode('%s:%s' % (config.get("FIRMA_ELECTRONICA.USER"),config.get("FIRMA_ELECTRONICA.PASSWORD")))
                    req = urllib2.Request(url, simplejson.dumps(viafirmaParams), {'Content-Type': 'application/json'})
                    req.add_header("Authorization", "Basic %s" % auth) 
                    f = urllib2.urlopen(req)
                    res = f.read()
                    informes["operationId"] = simplejson.loads(res)["operationId"]
                    informes["viafirmaUrl"]=viafirmaUrl
                    f.close()
                except Exception, e:
                    error = str(e)
                    log.error(error + " [exploracion_id="+ str(exploracion_id) + "]")
                    abort_json(500, _(u"Error al acceder a la plataforma de firma") )#IDIOMAOK

            response.headers['Content-Type'] = "application/json"
            return simplejson.dumps(informes)



        elif str(id).upper() == '_PREVIEW': # obtener el informe previsualizado

            if not format in ('pdf'):
                abort_xml(400, u'Solo se puede obtener la previsualización de un informe en formato PDF (.pdf)')
            if not 'uuid' in request.params:
                abort_xml(400, u'El parametro uuid es necesario')
            informe = None

            #crea la ruta donde se guardo el archivo con marca de agua
            nombre_archivo_marca_agua = os.path.join( tempfile.gettempdir(), request.params["uuid"] + '_marca_agua.pdf')
            try:
                pdfinfo = {}
                f = open(nombre_archivo_marca_agua, 'rb')
                pdfinfo['content'] = f.read()
                f.close()
                pdfinfo['size'] = os.path.getsize(nombre_archivo_marca_agua)
            finally:
                #se elimina el archivo de preview
                if os.path.exists(nombre_archivo_marca_agua): os.remove(nombre_archivo_marca_agua)

            response.headers['content-length'] = pdfinfo['size']
            response.headers['Content-Type'] = "application/pdf"
            return pdfinfo['content']

        else:
            q = meta.Session.query(self.tabla)
            if exploracion_id:
                q = q.filter(self.tabla.exploracion_id == exploracion_id)

            if str(id).upper() != '_LAST':
                q = q.filter(self.tabla.id == id)
            else: # si se pide el ultimo entonces no tener en cuenta los borrado
                q = q.filter(or_(self.tabla.borrado == 0,self.tabla.borrado == None))
                # 2.4.14 . Si tipo < 10 entonces es un informe y se tiene en cuenta para el show
                q = q.filter(self.tabla.tipo < 10)

            if q.count() == 0:
                response.status_code = 404
                return "error"

            if str(id).upper() != '_LAST':
                informe = q.one()
            else:
                informe = q.all()[-1]

            username = request.environ.get('REMOTE_USER', registro.DEFAULT_REMOTE_USER)
            ipaddress = obtener_request_ip(request)
            exploracion = registro_by_id(Exploracion, informe.exploracion_id)
            # REGISTRAR
            #   la consulta del informe
            registro.nuevo_registro(username, ipaddress, exploracion, registro.eventos.mostrar,
                                    registro.res.informe, 'NUMERO', str(informe.numero), None)
            # #################################

        # 2.4.10 - Verifica si esta autorizado si es que tiene la exploracion borrada
        if exploracion and exploracion.borrado and not authorized( HasAuthKitRole(roles.borrado_logico)):
            abort(400, _(u'No es posible visualizar el informe porque la exploración se encuentra borrada'))#IDIOMAOK
        else:
            if informe and informe.exploracion.borrado and not authorized( HasAuthKitRole(roles.borrado_logico)):
                abort(400, _(u'No es posible visualizar el informe porque la exploración se encuentra borrada'))#IDIOMAOK

        if format == 'xml':
            response.content_type = "text/xml"
            data = self._crear_data(informe, format)
            root = obj_to_xml(data, self.nombre_recurso, self.nombre_recursos)
            return tostring(root)


        if format == 'html':
            response.content_type = "text/html"

            # devolver el archivo html estatico
            f = file( nombre_archivo_informe(informe, 'html'), 'rb' )
            s = f.read()
            f.close()

            response.headers['content-length'] = len(s)
            return s


        if format in ('pdf'):
            try:
                if informe:
                    pdfinfo = get_pdf(informe)
                    response.headers['content-length'] = pdfinfo['size']
                    response.headers['Content-Type'] = "application/pdf"
                    return pdfinfo['content']
            except Exception as exception:
                log.error(exception)
                raise

    @authorize(HasAuthKitRole([roles.informes_exploraciones_user, roles.informes_exploraciones_todas]))
    def create(self, format='xml'):
        """
        Genera un nuevo informe para la exploracion indicada, o adjunto uno ya generado (en PDF)
        Parametros:
            - exploracion_id    el id de la exploracion
            - pdf               el archivo PDF, en base64, si se está adjuntando
            - plantilla     la plantilla a utilizar en la generación (o la utilizada si se está enviando ya generado)
            - imagenes      lista de imagenes para generarlo (o las utilizadas si se está enviando ya generado)
            - tipo          0 para interno, 1 para adjunto (externo), 2 para firmado
        """
        informe_id = None

        # --> Bloque que genera el informes y la relacion de capturas en la BD.
        try:


            # XXX   En el caso de que sea "informes_exploraciones_user", comprobar el usuario
            #       parametro "imagenes" -> lista de los ids de las imagenes seleccionadas para este informe, separados por comas (,)
            #       si no se pasa parametro "imagenes" cogerlas de la tabla imagenes, las que tengan el campo "seleccionada"=1
            #       ahora mismo, creo que al generar el informe no se pasa parametro "imagenes"

            # XXX   No se debería guardar el informe en BBDD hasta que no se ha
            #       generado correctamente. Por ejemplo, si falla la generación del PDF no
            #       se llega a realizar el envío del ORU, y si posteriormente se genera otro
            #       correctamente, como ya no será el primero (porque en bbdd tiene el
            #       registro del que ha fallado), tampoco se realizará el envío del ORU.
            #       Actualizacion 24/03/2017 (nacho): si bien seria lo mas correcto, hay que realizar mucho cambio.
            #                                         - hay que cambiar la funcion generar_informe, ya que en este punto no estaria
            #                                           generado el informe
            #                                         - Rel_capturas_informes se tendria que generar despues de crear correctamente el
            #                                           informe. Por lo que esta tabla tampoco tendria mucho sentido ya que solo serviria
            #                                           como informacion y no para la propia generacion. Igualmente como informacion
            #                                           tambien puede servir para otras funcionalidades de endotools en el futuro

            # Leer parametros
            if 'webob._parsed_post_vars' in request.environ:
                #en el caso de viafirma, nos envía un pdf binario en un multipart/form-data
                params=request.environ['webob._parsed_post_vars'][0]
                
                exploracion_id = params['exploracion_id']
                if "plantilla" in params:
                    plantilla = params['plantilla']
                else:
                    plantilla = None
                if "tipo" in params:
                    tipo = int(params['tipo'])
                else:
                    tipo = 0
                if "comentarios" in params:
                    comentarios = params['comentarios']
                else:
                    comentarios = None
            else:

                exploracion_id = request.params['exploracion_id']
                if "plantilla" in request.params:
                    plantilla = request.params['plantilla']
                else:
                    plantilla = None
                if "tipo" in request.params:
                    tipo = int(request.params['tipo'])
                else:
                    tipo = 0
                if "comentarios" in request.params:
                    comentarios = request.params['comentarios']
                else:
                    comentarios = None
            username = request.environ.get('REMOTE_USER', None)
            medico = medico_from_user(username)
            expl = registro_by_id(Exploracion, exploracion_id)

            # 2.4.10 - Comprueba que la exploracion no este eliminada logicamente.
            if is_exploracion_borrada(expl.id):
                abort_xml(400, _(u'La exploración se encuentra borrada'))#IDIOMAOK

            # Normativa de serguridad al generar un informe. Hay dos variantes:
            #   1) Puede generar el informe el usuario que ha generado la exploracion y tiene el rol informes_exploraciones_user
            #   2) Tambien puede generar informe el usuario que tiene el permiso informes_exploraciones_todas,
            #      independientemente de si la exploración es suya o no
            autorizado = ( expl.medico_id == medico.id and authorized( HasAuthKitRole(roles.informes_exploraciones_user) )) \
            or (authorized( HasAuthKitRole(roles.informes_exploraciones_todas) ))
            if not autorizado:
                abort(403, _(u'El usuario actual no puede generar informes para esta exploración'))#IDIOMAOK

            # Añadir un nuevo registro en la tabla de informes
            nuevoInforme = self.tabla()
            nuevoInforme.exploracion_id = exploracion_id
            nuevoInforme.plantilla = plantilla
            nuevoInforme.fecha = datetime.datetime.today().date()
            nuevoInforme.enviado =  False
            nuevoInforme.medico_id = formatea_valor(medico.id)
            nuevoInforme.tipo = tipo
            nuevoInforme.comentarios = comentarios

            # Para el numero de informe, coger el ultimo asignado y añadirle 1
            q = meta.Session.query(Informe)
            n = q.max(Informe.numero)
            if n is None: n = 0
            nuevoInforme.numero = formatea_valor(n+1)
            meta.Session.save(nuevoInforme)
            meta.Session.commit()
            informe_id = nuevoInforme.id # guardo el id, pq lo necesito para saber si borrarlo logicamente en caso de error
            log.debug(informe_id)
            # procesar parametro 'imagenes', creando los registros necesarios en la tabla "rel_Capturas_Informes"
            # XXX ojo si da algun error esto!, porque el registro en la tabla de informes ya se ha creado (se ha hecho ya el commit)
            if 'imagenes' in request.params:
                # se respeta el orden del parametro
                s = request.params['imagenes'].split(',')
            else:
                # ordenadas por columna "orden"
                imagenes = meta.Session.query(Captura).filter(and_(Captura.seleccionada==True, Captura.exploracion_id==nuevoInforme.exploracion_id)).order_by(Captura.orden).all()
                s = map(lambda img: img.id, imagenes)
            orden = 1
            for captura_id in s:
                rel = Rel_Capturas_Informes()
                rel.captura_id = captura_id
                rel.informe_id = nuevoInforme.id
                rel.orden = orden
                meta.Session.save(rel)
                orden += 1
            meta.Session.commit()
            
            # busca todas las capturas seleccionadas y mira si existe el archivo. Si no existe
            # y esta almacenado en el pacs entonces las obtiene para generar el informe
            imagenes = meta.Session.query(Captura).filter(and_(Captura.seleccionada==True, Captura.exploracion_id==nuevoInforme.exploracion_id)).order_by(Captura.orden).all()
            for captura in imagenes:
                if not _archivo(captura.id, captura.tipo):
                    archivo = obtener_del_pacs(captura)
                    if not archivo:
                        raise Exception(_(u"No se pudo obtener captura del pacs, no se puede generar informe") + " (captura id:" + str(captura.id) + ")")#IDIOMAOK
            
            ipaddress = obtener_request_ip(request)
            exploracion = registro_by_id(Exploracion, exploracion_id)
            # Registrar la creacion del informe en BBDD
            registro.nuevo_registro(username, ipaddress, exploracion, registro.eventos.crear,
                                    registro.res.informe, 'NUMERO', None, str(nuevoInforme.numero))
        except Exception, e:
            self._borrado_logico_por_error(informe_id)

            error = _(u"Ocurrio un error en la creación del informe") + " (" + str(e) + ")"#IDIOMAOK
            log.error(error + " [informe_id="+ str(informe_id) + "]")
            abort_json(500, error)

        # --> Bloque de generacion del archivo de informe
        try:
            if 'pdf' in request.params:
                # guardar el informe PDF pasado en base64 a un archivo
                # este caso es usado por ejemplo cuando se forma el informe desde el
                # navegador y es necesario guardarlo firmado en el servidor.
                nombre_archivo = nombre_archivo_informe(nuevoInforme, 'pdf',True)
                f = open(nombre_archivo, 'wb')
                f.write( b64decode(request.params['pdf'].split("data:application/pdf;base64,")[-1]) )
                f.close()
            elif 'firma' in params and params["firma"] == 'viafirma':
                fieldstorage = params['files']
                nombre_archivo = nombre_archivo_informe(nuevoInforme, 'pdf',True)
                f = open(nombre_archivo, 'wb')
                import shutil
                shutil.copyfileobj(fieldstorage.file, f)
                fieldstorage.file.close()
                f.close() 
            else:
                # generar el informe (HTML->HTML+PDF  o  DOC->PDF)
                generar_informe(nuevoInforme)

        except Exception, e:
            # borro logicamente el informe y devuelvo error
            self._borrado_logico_por_error(informe_id)
            error = str(e)
            log.error(error + " [informe_id="+ str(informe_id) + "]")
            if error == "openoffice: Timeout":
                abort_json(500, _(u"Se ha terminado el tiempo de espera de creación de informe. Intentelo nuevamente.") )#IDIOMAOK
            elif error == "openoffice: Error 1":
                abort_json(500, _(u"Ocurrio un error en la creación del informe") + " (" + error + ")" )#IDIOMAOK
            else:
                abort_json(500, _(u"Ocurrio un error en la creación del informe") + " (" + error + ")" )#IDIOMAOK

        # --> Bloque de integracion - Este blque si falla no genera una exception ni retorna error
        #                             usuario. El informe en este punto ya esta generado correctamente
        try:
            # 2.4.14 . Si tipo < 10 entonces es un informe y se envia, sino es un adjunto
            if nuevoInforme.tipo < 10:

                # en este punto existe ya el .pdf, y se puede copiar ya en una carpeta
                # si esta configurado asi en el INI (para integración mediante copia de PDFs)
                guardar_pdf_en_carpeta(nuevoInforme)

                # si hay algún plugin de informes que tenga que hacer algo cuando se genera
                # un nuevo informe, se hace ahora.
                self._informe_generado(nuevoInforme)

                # enviar mensaje ORU R01, si está configurado asi. Ademas dependera de si es
                # el primer informe, de si va incrustado y de si se envian versiones
                if config.get('ENVIAR_ORU.ACTIVO', '0') == '1':
                    import endotools.lib.hl7_wrapper.sending
                    enviado_informe = False

                    if config.get('ENVIAR_ORU.INCRUSTADO', '0') == '1':
                        # cuando es incrustado en base64, siempre es por versiones
                        enviado_informe = endotools.lib.hl7_wrapper.sending.enviar_ORU_R01(nuevoInforme, True, True)


                    elif config.get('ENVIAR_ORU.VERSIONES', '0') == '0':
                        #IMPORTANTE - Se ha reimplentado la logica de que envie el ORU si es el primer informe
                        #la nueva implementación mira si se ha enviado correctamete al menos 1 informe de la exploración.
                        #en el caso de que no se haya enviado ningun informe, se envia.
                        algun_informe_enviado = False
                        for informe in nuevoInforme.exploracion.informes:
                            if informe.enviado == True or informe.enviado == None:
                                algun_informe_enviado = True
                        if algun_informe_enviado == False:
                            enviado_informe = endotools.lib.hl7_wrapper.sending.enviar_ORU_R01(nuevoInforme)
                    else:
                        # enviar siempre
                        enviado_informe = endotools.lib.hl7_wrapper.sending.enviar_ORU_R01(nuevoInforme, True)

                    if enviado_informe == True:
                        nuevoInforme.enviado =  True
                        meta.Session.update(nuevoInforme)
                        meta.Session.commit()

        except Exception, e:
            log.error("Error en REST CREATE de informe [Bloque integracion]: " + str(e))

        # --> Bloque de retorno de valor
        try:
            # devolver como xml o json
            data = { 'id': formatea_valor(nuevoInforme.id) }
            response.status_code = 201
            if format == 'xml':
                response.content_type = "text/xml"
                return tostring(obj_to_xml(data, self.nombre_recurso))
            elif format == 'json':
                response.content_type = 'application/json'
                return simplejson.dumps(data)

        except Exception, e:
            log.error(e)
            # seria muy extraño que falle en este punto si no hay fallado antes.
            # Es casi imposible que entre en esta excepcion
            abort_json(500, _(u"Ocurrio un error en la creación del informe") + " (" + str(e) + ")" )#IDIOMAOK

    @conditional_authorize(RemoteUser())
    def update(self, id):
        response.status_code = 405
        return _('ERROR: No se puede modificar un informe')#IDIOMAOK

    @conditional_authorize(RemoteUser())
    def delete(self, id):

        # nuevo en 2.4.10
        username = request.environ['REMOTE_USER']
        ipaddress = obtener_request_ip(request)
        informe = self._registro_by_id(id)
        medico_conect = medico_from_user(username)

        #primero intenta borrar logico, si el usuario tiene permisos.
        autorizado =  authorized(HasAuthKitRole(roles.borrado_logico))
        if not autorizado:
            abort_json(403, _(u'El usuario actual no puede borrar el informe'))#IDIOMAOK

        # 2.4.10 - Comprueba que la exploracion no este eliminada logicamente.
        if is_exploracion_borrada(informe.exploracion.id):
            abort_json(400, _(u'La exploración se encuentra borrada'))#IDIOMAOK

        # XXX Definir si solo borra si tiene un motivo --
        if 'borrado_motivo' in request.params and request.params["borrado_motivo"].strip()!="":
            
            motivo = request.params["borrado_motivo"].strip()
            informe.borrado_motivo = motivo
            informe.borrado = 1
            meta.Session.update(informe)
            meta.Session.commit()
            registro.nuevo_registro(username, ipaddress, informe.exploracion,
                                    registro.eventos.eliminar,
                                    registro.res.informe, 'BORRADO',
                                    "0", "1 - Motivo: " + motivo )

            self._informe_borrado(informe)

            if config.get('ENVIAR_ORU.ACTIVO', '0') == '1' and config.get('ENVIAR_ORU.ANULAR', '0') == '1':

                enviado_informe = False
                from  endotools.lib.hl7_wrapper.sending import enviar_ORU_R01

                #comprobamos si no existe ningun otro informe
                q = meta.Session.query(Informe).filter(Informe.exploracion_id == informe.exploracion_id)
                q = q.filter(Informe.borrado == None)
                #versionado= q.max(Informe.numero) == informe.numero
                #q = q.order_by(Informe.numero)
                informes = q.all()

                #comprobamos que no exista algun informe anterior
                anular= not len(informes)
                nuevoInforme=informe

                #pendiente de revisar si hacemos versionado hacia atras automático
                #if not anular:
                #    nuevoInforme = informes[len(informes)-1]

                #Si no existe ningun informe anterior enviamos el mensaje de anulación
                if anular:
                    if config.get('ENVIAR_ORU.INCRUSTADO', '0') == '1':
                        # cuando es incrustado en base64, siempre es por versiones
                        enviado_informe = enviar_ORU_R01(nuevoInforme, True, True, anular=anular)

                    elif config.get('ENVIAR_ORU.VERSIONES', '0') == '1':
                        enviado_informe = enviar_ORU_R01(nuevoInforme, True, anular=anular)
                        
        else:
            abort_json(400, _(u'Es necesario un motivo de borrado'))#IDIOMAOK


    def _informe_generado(self, informe):

        # ejecutar el plugin
        if pluginInformes:
            medico = medico_from_user(request.environ['REMOTE_USER'])
            try:
                pluginInformes.informe_generado(informe, medico)
##              pluginInformes.informe_generado(informe.id, contenido_informe, medico)#, params)
            except PluginException, e:
                log.error(e)
                abort_xml(e.http_status, str(e))
            except Exception, e:
                log.error(e)
                #raise # XXX para pruebas
                abort_xml(500, _(u'Ha ocurrido un error al finalizar la generación del informe (%s)') % e)#IDIOMAOK

    def _informe_borrado(self, informe):

        # ejecutar el plugin
        if pluginInformes:
            medico = medico_from_user(request.environ['REMOTE_USER'])
            try:
                pluginInformes.informe_borrado(informe, medico)
            except PluginException, e:
                log.error(e)
                abort_xml(e.http_status, str(e))
            except Exception, e:
                log.error(e)
                #raise # XXX para pruebas
                abort_xml(500, _(u'Ha ocurrido un error al finalizar la generación del informe (%s)') % e)#IDIOMAOK

    def _borrado_logico_por_error(self, informe_id):
        if informe_id != None:
            # se guardo un informe en la base de datos, pero como hay un error hay que borrarlo logicamente.
            q = meta.Session.query(Informe).filter( Informe.id == informe_id )
            if q.count():
                informe = q.one()
                informe.borrado = True
                informe.borrado_motivo = u"Error Interno de creación de informe"
                meta.Session.update(informe)
                meta.Session.commit()

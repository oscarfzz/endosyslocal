from pylons.i18n import _
from xml.etree.ElementTree import Element, SubElement, tostring, XML
import logging
import hl7
import datetime
from endosys.model import meta
import endosys.model.prioridades
from endosys.model.motivosCancelacion import MotivoCancelacion
from endosys.lib.fusiones import FusionarPacientes
from endosys.model.servicios import get_servicio_id, get_servicio_y_agenda_id
from endosys.model.agendas import get_agenda_id, get_agenda
from endosys.model.campos import Campo
from endosys.model.valores import ValorSelec
from endosys.lib.misc import *
from sqlalchemy.sql import and_, or_
from endosys.config.plugins import pluginHL7
from endosys.lib.informes import get_pdf
from endosys.lib.valores import get_valor_class_by_tipo
from base64 import b64encode
from endosys.lib.hl7_wrapper.log import nuevo_log_HL7_output, cambio_estado_log_HL7
import endosys.lib.hl7_wrapper
import endosys.lib.hl7_wrapper.receiving
from endosys.lib.hl7_wrapper import HL7_ABSENT
import endosys.lib.registro as registro
from endosys.model.provincias import provincia_nombre_by_codigo
from endosys.model.poblaciones import poblacion_nombre_by_codigo
from endosys.model.pacientes import Rel_Pacientes_Centros
from endosys.model.centros import get_centro_id
from endosys.lib.elementos import get_by_id
from endosys.lib.informes.valores import get_no_definido_value

log = logging.getLogger(__name__)

SENDING_APPLICATION =   "endosys"
SENDING_FACILITY =      "endosys"
RECEIVING_APPLICATION = "HIS"
RECEIVING_FACILITY =    "HIS"
VERSION_ID =            "2.5"

def _make_MSH(centro, message_code, trigger_event, message_structure):
    """
    Construye un segmento MSH y lo devuelve como cadena unicode (latin_1).
    
      centro                Registro bbdd indicando el centro, o None.
      message_code          Valor para MSH.9.1
      trigger_event         Valor para MSH.9.2
      message_structure     Valor para MSH.9.3
    
    VAR/CONST   FIELD       NAME                                VALUE (TABLE)
    ----------------------------------------------------------------------------
    C           MSH.1       Field Separator                     |
    C           MSH.2       Encoding Characters                 ^~\&
    V           MSH.3       Sending Application
    V           MSH.4       Sending Facility
    V           MSH.5       Receiving Application
    V           MSH.6       Receiving Facility
    V           MSH.7       Date/Time of Message
                MSH.8       Security
    V           MSH.9       Message type
    V           MSH.9.1         Message Code                    (0076)
    V           MSH.9.2         Trigger Event                   (0003)
    V           MSH.9.3         Message Structure               (0354)
    V           MSH.10      Message Control Id
    C           MSH.11      Processing Id                       P
    V           MSH.12      Version Id
                MSH.13      Sequence Number
                MSH.14      Continuation Pointer
    C           MSH.15      Accept Acknowledgement Type         AL
    C           MSH.16      Application Acknowledgement Type    NE
                

    NOTAS:
    
    MSH-11 (Processing ID) – specifies the HL7 processing ID or processing mode;
            HL7 processing IDs include D (debugging), P (production),
            T (training); HL7 processing modes include A (archive),
            R (restore from archive), I (initial load), not present
            (default value, means “current processing”)    
    """
    facility = ""
    if centro: facility = centro.codigo
    datetime_message =      endosys.lib.hl7_wrapper.datetime_to_hl7(datetime.datetime.now())
    message_control_id =    endosys.lib.hl7_wrapper.datetime_to_hl7(datetime.datetime.now(), True)
    msh = "MSH|^~\&|%s|%s|%s|%s|%s||%s^%s^%s|%s|P|%s|||AL|NE\r" % (
                    config.get('HL7.APPLICATION_ID', 'endosys'),
                    facility,
                    config.get('HL7.EXTERNAL_APPLICATION_ID', 'HIS'),
                    facility,
                    datetime_message,
                    message_code,
                    trigger_event,
                    message_structure,
                    message_control_id,
                    VERSION_ID
                )
    return unicode(msh, 'latin_1')
    
def _make_PID(centro, paciente):
    """
    Construye un segmento PID y lo devuelve como cadena unicode (latin_1).
    
      centro                Registro bbdd indicando el centro.
      paciente              Registro bbdd indicando el paciente.
    
    VAR/CONST   FIELD       NAME                                VALUE (TABLE)
    ----------------------------------------------------------------------------
    V           PID.2       Patient Id                          idunico
    V           PID.3       Patient Identifier List             lista ids
    V           PID.5       Patient Name                        apellido1+nombre
    V           PID.6       Mother's Maiden Name                apellido2
    V           PID.7       Date/Time Of Birth                  fecha nacimiento
    V           PID.8       Administrative Sex                  sexo
    V           PID.11      Patient Address                     dirección
    """
    
    patient_ids = [
        endosys.lib.hl7_wrapper.CX(paciente.CIP,           "", "JHN"),
        endosys.lib.hl7_wrapper.CX(paciente.DNI,           "", "NNESP"),
        endosys.lib.hl7_wrapper.CX(paciente.idunico,       "", "PN"),
        endosys.lib.hl7_wrapper.CX(paciente.numAfiliacion, "", "SS")
    ]

    # tratar dee obtener el NHC del centro. Si el paciente no tiene NHC para el
    # centro indicado, no se añade la repetición de tipo "PI".
    rels = filter(lambda rel: rel.centro_id == centro.id, paciente.centros)
    if len(rels) > 0:
        patient_ids.append( endosys.lib.hl7_wrapper.CX(rels[0].nhc, centro.codigo, "PI") )

    patient_id_list = endosys.lib.hl7_wrapper.FIELD_REPEAT_SEPARATOR.join(patient_ids)
    
    pid = "PID||%s|%s||%s^%s|%s|%s|%s|||%s^^%s^%s^%s\r" % (
                    endosys.lib.hl7_wrapper.to_str(paciente.idunico),
                    patient_id_list,
                    endosys.lib.hl7_wrapper.to_str(paciente.apellido1),
                    endosys.lib.hl7_wrapper.to_str(paciente.nombre),
                    endosys.lib.hl7_wrapper.to_str(paciente.apellido2),
                    endosys.lib.hl7_wrapper.date_to_hl7(paciente.fechaNacimiento),
                    endosys.lib.hl7_wrapper.to_sex(paciente.sexo),
                    endosys.lib.hl7_wrapper.to_str(paciente.direccion),
                    endosys.lib.hl7_wrapper.to_str(paciente.poblacion),
                    endosys.lib.hl7_wrapper.to_str(paciente.provincia),
                    endosys.lib.hl7_wrapper.to_str(paciente.codigoPostal)
                )

    return unicode(pid, 'latin_1')

def _construir_campo_prest_realizada(obr_prestacion):
    """
    """

    # read ini configuration
    cpr = config.get('ENVIAR_CAPTURA_ACTIVIDAD.CAMPO_PRESTACION_REALIZADA',None)

    if cpr:
        try:
            # Construcción del obr prestacion mediante un campo del formaulario.
            log.debug('campo_prestacion_realizada=%s' % (cpr,) )
            q = meta.Session.query(Campo).filter( Campo.nombre == cpr )
            log.debug('total campos encontrados: %s' % (q.count(),) )
            cpr_id = q.one().id
            log.debug('campo_prestacion_realizada_id: %s' % (cpr_id,) )
            log.debug('cita.exploracion_id: %s' % (exploracion.id,) )
            q = meta.Session.query(ValorSelec).filter(and_(
                    ValorSelec.exploracion_id == exploracion.id,
                    ValorSelec.campo_id == cpr_id))
            log.debug('total valores encontrados: %s' % (q.count(),) )
            elem_prest_realizada = q.one().elemento
            obr_prestacion = obr_prestacion + '^^' +\
                             (elem_prest_realizada.codigo or HL7_ABSENT) + \
                             '^' + \
                             (elem_prest_realizada.nombre or HL7_ABSENT)
            return obr_prestacion
        except Exception as e:
            msg = 'Error obteniendo valor del campo de prest. realizada: %s'
            log.error(msg % (e,) )
            raise Exception(msg)
    else:
        # no hace ningun cambio al obr
        return obr_prestacion

def _make_obx_campos(exploracion, seq_start):
    #import pdb; pdb.set_trace()
    """ 
    Params:
        - exploracion: la exploracion de la cual se extraeran los datos
        - seq_start es el numero de secuencia de ese tipo de segmento.
          Ejemplo: si seq_start=2 el primer OBX que se genere será OBX|2|... 
    
    Retorno
        - Un array de obx
    """
    #import pdb; pdb.set_trace()
    
    obxs = []

    # Iterar las claves ini con posfijo 
    ini_base = 'ENVIAR_ORU.OBX_DAT'
    ini_pos = 1
    ini_campos = 'CAMPOS'
    application_id = config.get('HL7.APPLICATION_ID', 'endosys')
    # CAMPO_EXTERNO es el valor del INI que sirve para completar el OBX 3.1
    #ini_externo = 'CAMPO_EXTERNO' 

    # ex.: ENVIAR_ORU.OBX_DAT.1.CAMPOS = colono_proc,gastro_proc
    current = '%s.%s.%s' % (ini_base, str(ini_pos), ini_campos)
    while config.get(current,None) != None:
        # si encuentra claves con ese formato entonces hace el procesamiento
        obx_base = 'OBX|%s|%s|%s|%s|%s||||||||||||\r'
        # El formato de los valores será (IDELEMENTO^CODIGO^NOMBRE)
        valor_base = '%s^%s^%s'
        campo_base = '%s^%s'

        # el obx.3 es un tipo de campo CE. por lo que la estructura es:
        # ID^Descripción^SistemaCodificación^AlternateID^Descripcion^SistemaCodificacion
        obx_3 = '%s^%s^%s^%s^%s^%s' % (str(exploracion.id), 'expl_id', application_id, '', '', '')

        # recorre ini_campos hasta encontrar uno que pertenezca al form de la
        # exploracion
        campos = config.get(current).split(",")
        for campo in campos:
            campo = campo.strip()

            # busca el id del campo
            q_campo = meta.Session.query(Campo).filter( Campo.nombre == campo )
            if q_campo.count() == 0:
                # salta a la proxima iteracion
                continue

            # obtiene el primer campo de los que encontró
            campo_db = q_campo.one()
            
            # busca valores de ese campo segun si tipo
            class_valor = get_valor_class_by_tipo(campo_db.tipo)
            if class_valor == None:
                # el tipo no esta soportado, sigue con el siguiente
                continue

            q_valores = meta.Session.query(class_valor).filter( and_(
                    class_valor.exploracion_id == exploracion.id,
                    class_valor.campo_id == campo_db.id
                ))

            if q_valores.count() == 0:
                # no hay valores, sigue con el siguiente.
                continue
            
            agregar = False
            valores_db = q_valores.all()
            for v in valores_db:

                if campo_db.tipo in (1,4,5):
                    # tipo texto, bool o texto predefinido
                    # el valor esta en el campo valor
                    if v.valor:
                        tipo_campo = 'ST'
                        obx_5 = '%s' % (v.valor)
                        agregar = True

                if campo_db.tipo in(2,3):
                    # tipo selec o multi
                    # el valor esta dentro del elemento, hay que buscar
                    # el elmento relacionado.
                    if v.elemento:
                        e = v.elemento
                        cod = e.codigo or ''
                        tipo_campo = 'CE'

                        obx_5 = '%s^%s^%s^%s^%s^%s' % (str(e.id), \
                                                       e.nombre, \
                                                       application_id, \
                                                       cod, \
                                                       '', '')
                        agregar = True

                if agregar:
                    obxs.append(obx_base % (seq_start, \
                                            tipo_campo, \
                                            obx_3, \
                                            str(campo_db.id),
                                            obx_5))   
                    seq_start += 1

            # ya encontro un campo que existe en esa exploracion.
            # No se necesita seguir recorriendo campos, por lo que se sale del
            # for 
            break 
        
        # Continua con otra posicion de la clave del ini. 
        ini_pos += 1
        current = '%s.%s.%s' % (ini_base, str(ini_pos), ini_campos) 

    return obxs


def _crear_mensaje_oru_r01(informe, versiones=False, incrustado=False, anular=False):
    """
    Genera un mensaje ORU a partir de la información de un informe y lo
    envía a Mirth, para que lo transforme y lo reenvíe al HIS.

    PARAMS:
    - informe       Registro de bbdd
    - versiones     Indica si se enviará el link a la versión concreta del
                    informe o si se envía un link que retorna siempre la
                    última versión (_LAST.pdf)
    - incrustado    Indica si se incrustará el archivo PDF en lugar de enviar el
                    link (No es compatible con versiones=False)

    TODO:
    - Poder configurarlo para que se ejecute al generar el primer informe,
      cualquier informe, o al finalizar la exploración.
    - Controlar la respuesta de Mirth. Si es distinto de "200 OK", ahora
      lanza una excepción...

    INFO ADICIONAL:
    - La libreria de python hl7 no sirve para crear mensajes HL7, solo para
      parsearlos, asi que este ORU se genera "a mano".
    - Los segmentos OBX tendran este formato: 
      'OBX|1|RP|%s|INF|http://endosys-server/rest/exploraciones/117/informes/_LAST.pdf\r'
      'OBX|%s|RP|%s|IMG|http://endosys-server/rest/capturas/254.jpg\r'
      'OBX|2|RP|ID|IMG|http://endosys-server/rest/capturas/254.jpg||||\r' +\
      'OBX|3|RP|ID|IMG|http://endosys-server/rest/capturas/255.jpg||||\r' +\
      'OBX|4|RP|ID|IMG|http://endosys-server/rest/capturas/256.jpg||||'

    LIMITACIONES:
    - en PID solo se indica el NHC
    """
    import urlparse
    log_prefix = "[_crear_mensaje_oru_r01]"

    exploracion = informe.exploracion

    if not exploracion.cita:
        # Condición necesaria que tenga una Cita
        log.debug(log_prefix+'Expl. Sin cita asociada. No se puede enviar ORU')
        return False
    
    if not exploracion.cita.ex and not exploracion.cita.work:
        # la cita ha de venir de integración o de worklist
        log.debug(log_prefix+'Cita sin cita_ex o work. No se puede enviar ORU')
        return False

    # Identificar el médico que va a generar el informe
    # Formato: COLEGIADO^APELLIDO1 APELLIDO2^NOMBRE
    username =  request.environ.get('REMOTE_USER', None)
    registro_medico = medico_from_user(username)
    medico = '%s^%s %s^%s' % (str(registro_medico.colegiado or ''),
                              (registro_medico.apellido1 or ''),
                              (registro_medico.apellido2 or ''),
                              (registro_medico.nombre or ''))
    
    # Leer configuraciones del INI
    host_ = config.get('ENVIAR_ORU.LINKS.HOST', '127.0.0.1')
    incluir_imagenes = config.get('ENVIAR_ORU.INCLUIR_IMAGENES', '1')
    
    # formato base de OBXs        
    obx_informe =   'OBX|1|%s|%s|INF|%s|||||||||||%s|\r'
    obx_captura =   'OBX|%s|RP|%s|IMG|%s\r'
    # variable donde se almacena el obx resultante
    obxs = u''

    msh = _make_MSH(exploracion.servicio.centro, "ORU", "R01", "ORU_R01")
    pid = _make_PID(exploracion.servicio.centro, exploracion.paciente)
    
    # PV1 ---
    # - PV1.19.1    IDENTIFICADOR_CITA  (de momento no)
    # - PV1.50.1    ALTERNATE_VISIT_ID  (Candelaria: es el ID_PROCESO_SELENE)
    if exploracion.cita.work:
        # PV1 de worklist se envia sin información
        # NOTA: de momento solo se usa en HUCA (EOS - Millenium)
        pv1 = unicode('PV1||', 'latin_1')
    else:
        # Se usa el PV1 que llega por SIU/ORM
        pv1 = unicode(exploracion.cita.ex.pv1 or '', 'latin_1')
    if pv1:
        pv1 = pv1 + '\r'

    # OBR ---
    # - OBR.3.1     ID_EXPLORACION_ENDOTOOLS
    # - OBR.4.1     COD_PRESTACION
    # - OBR.4.2     NOMBRE_PRESTACION
    # - OBR.7.1     FECHAHORA
    # - OBR.18.1    PLACER_FIELD_1 (para Candelaria significa TIPO_DEPART)
    # - OBR.19.1    PLACER_FIELD_2 (para Candelaria significa COD_DEPART)
    # - OBR.24.1    DIAGNOSTIC_SERV_SECT_ID (para Candelaria significa PROVEEDOR)

    # * Recoge de BBDD el mismo segmento OBR recibido en la petición y le
    #   asigna el exploracion.id y date_to_hl7(exploracion.fecha) en los
    #   campos correspondientes.
    # * Además, ahora si venía de Worklist se construye un nuevo segmento OBR
    #   con los datos obtenidos del WL.
    
    if not exploracion.fecha:
        fechahora = None
    elif not exploracion.hora:
        fechahora = exploracion.fecha
    else:
        f = exploracion.fecha 
        hora = exploracion.hora
        fechahora = datetime.datetime(f.year, f.month, f.day,
                                      hora.hour, hora.minute, hora.second)
    
    if exploracion.cita.work:
        # Construcción del OBR mediante worklist
        wlst = exploracion.cita.work
        
        obr_prestacion = '%s^%s' % ((wlst.schProcStepID or HL7_ABSENT),
                                    (wlst.schProcStepDescription or HL7_ABSENT))

        obr = 'OBR|1|%s|%s|%s|||%s|||||||||||||||||\r'
        obr = obr % (exploracion.cita.work.placerOrderNumber or '',
                     exploracion.id or '',
                     obr_prestacion,
                     endosys.lib.hl7_wrapper.datetime_to_hl7(fechahora))
        obr = unicode(obr, 'latin_1')
    
    elif exploracion.cita.ex.obr:
        # Construcción de OBR a partir de un ORM
        obr = unicode(exploracion.cita.ex.obr, 'latin_1')
        # TODO:  si "exploracion.cita.ex.obr" no tiene un seg. válido dará error
        obr = hl7.parse(obr).segment('OBR')   
        obr[3] = exploracion.id
        obr[7] = endosys.lib.hl7_wrapper.datetime_to_hl7(fechahora)
        obr = unicode(obr) + '\r'

    else:
        # Construcción de un OBR a partir de un SIU
        c_ex = exploracion.cita.ex
        obr_prestacion = '%s^%s' % ((c_ex.prestacion_cod or HL7_ABSENT),
                                    (c_ex.prestacion_descr or HL7_ABSENT))
 
        try:
            # construye el obr prestacion con los datos de un campo 
            # del formulario. Para que funcione se tiene que configurar la 
            # clave ini inidicando el campo que se usará
            obr_prestacion = _construir_campo_prest_realizada(obr_prestacion)
        except Exception as e:
            log.error(e)
       
        # Construcción del OBR
        obr = 'OBR|1|%s|%s|%s|||%s|||||||||||||||||\r'
        obr = obr % ( exploracion.cita.ex.numero_peticion or '',
                      exploracion.id or '',
                      obr_prestacion,
                      endosys.lib.hl7_wrapper.datetime_to_hl7(fechahora))
        obr = unicode(obr, 'latin_1')

    # ORC ---
    # - ORC.2.1     NUMERO PETICION

    if exploracion.cita.work:
        # Ahora si venía de Worklist se construye un nuevo segmento ORC
        # con los datos obtenidos del WL.
        # - ORC 11      MEDICO
        orc = 'ORC||%s|%s||||||||%s|||||||||||||\r'
        orc = orc % (exploracion.cita.work.placerOrderNumber or '',
                     exploracion.id or '',
                     medico)
        orc = unicode(orc, 'latin_1')

    elif exploracion.cita.ex.orc: 
        # ORC a partir de un ORM
        orc = unicode(exploracion.cita.ex.orc, 'latin_1')
        orc = orc + '\r'
    
    else: 
        # ORC a partir de un SIU
        # - ORC 11      MEDICO
        orc = 'ORC||%s|%s||||||||%s|||||||||||||\r'
        orc = orc % (exploracion.cita.ex.numero_peticion or '',
                     exploracion.id or '',
                     medico)
        orc = unicode(orc, 'latin_1')

    if anular:
        orc = hl7.parse(orc).segment('ORC')
        orc[1] = 'OC'
        orc = unicode(orc)+'\r'

    # OBX ---
    def cambia_host_url(url, host):
        url = list( urlparse.urlparse(url) )
        s = url[1].split(':')   #   [1] = .netloc
        s[0] = host
        url[1] = ':'.join(s)
        return urlparse.urlunparse(url)

    # Informe ***
    # - OBX.3      Id del informe 
    #              (dependerá de si se envía el link a 
    #               un inf concreto o al _LAST.pdf)
    # - OBX.5      link http al informe, o el informe incrustado en base64.
    # - OBX 16.1   Numero de colegiado, 
    #   OBX 16.2   Apellidos del medico
    #   OBX 16.3   Nombre del medico

    if incrustado:
        # Base64
        # NOTA: El tamaño del mensaje HL7 termina siendo
        #       aproximadamente un 133 % del tamaño del archivo PDF.
        pdfinfo = get_pdf(informe)
        obx5 = '^AP^Octet-stream^Base64^' + b64encode(pdfinfo['content'])
        obx2 = 'ED'
    else:
        # Link HTTP
        if versiones:
            obx5 = h.url_for(controller='rest/informes', 
                             exploracion_id=exploracion.id, 
                             action='show', 
                             format='pdf', 
                             id=informe.id, 
                             qualified=True)
        else:
            obx5 = h.url_for(controller='rest/informes', 
                             exploracion_id=exploracion.id, 
                             action='show', 
                             format='pdf', 
                             id='_LAST', 
                             qualified=True)
        
        obx5 = cambia_host_url(obx5, host_)
        obx2 = 'RP'

    obx = obx_informe % (obx2,
                         exploracion.id,
                         obx5,
                         medico)
    obx = unicode(obx, 'latin_1')
    obxs = obxs + obx

    # Para hacer separacion de obx se usa "contador". El 1 es el informe y 
    # los demas son variables, empieza del 2 pq el uno siempre se usará para 
    # el informe
    contador = 2

    # Captura ***
    # - OBX.1      Contador (empieza en 2)
    # - OBX.3      Id de la imagen
    # - OBX.5      Link http a la imagen
    if incluir_imagenes == '1':
        for captura in exploracion.capturas:
            link = h.url_for(controller='rest/capturas', 
                             action='show',
                             id=captura.id,
                             format='auto',
                             qualified=True)
            link = cambia_host_url(link, host_)
            obx = obx_captura % (contador,
                                 captura.id,
                                 link)
            obx = unicode(obx, 'latin_1')
            obxs = obxs + obx
            contador += 1

    # agrega los obx de valores de campos.
    obxs_valores = _make_obx_campos(exploracion, contador)
    for obx_valor in obxs_valores:
        obxs = obxs + unicode(obx_valor, 'latin_1')
        contador += 1


    # CTI ---
    # - CTI.1   ACCESSION NUMBER (sólo de Worklist)

    if exploracion.cita.work:
        # Si tiene cita de Worklist, se añade el AccessionNumber
        # en el nuevo segmento CTI (según requisitos de Parc Tauli).
        # En caso contrario, no se añade el segmento.
        cti = 'CTI|%s\r'
        cti = cti % exploracion.cita.work.accessionNumber
    else:
        cti = ''
    cti = unicode(cti, 'latin_1')

    # Construcción del mensaje ORU
    msg = msh + pid + pv1 + orc + obr + obxs + cti
    return msg

def enviar_ORU_R01(informe, versiones=False, incrustado=False, anular=False):
    """ Envia un mensaje ORU_R01
    """
    log_prefix = "[enviar_ORU_R01]"

    # Leer INI
    timeout_oru = config.get('ENVIAR_ORU.TIMEOUT', 30)
    destino_ = config.get('ENVIAR_ORU.DESTINO', '127.0.0.1:6000')

    # variables usadas
    exploracion = informe.exploracion

    # Crea contenido de mensaje ORU
    msg = _crear_mensaje_oru_r01(informe, versiones, incrustado, anular)
    log.debug('%sEnviar mensaje HL7: %s' % (log_prefix,msg))

    # registrar mensaje de salida en hl7_log
    id_hl7_log = nuevo_log_HL7_output(msg_out = msg, 
                                      idunico = exploracion.paciente.idunico, 
                                      exploracion_id = exploracion.id)

    # Enviar el mensaje a Mirth
    #  - Siempre devolverá 200 OK, independientemente de que el reenvío al HIS
    #    sea correcto (si falla es "problema" del Mirth, queda marcado como error)
    #    si el mensaje no se llega a enviar por problemas de comunicación,
    #    request() lanza una excepción. Esto si que lo tiene que tratar EndoTools!
    #    NOTA: finalmente hago que si Mirth devuelve un codigo distinto de 200
    #          significa que necesita que se le vuelva a enviar el mensaje, lo
    #          mismo que si no le hubiera llegado.
    import httplib
    try:
        conn = httplib.HTTPConnection(destino_, 
                                      timeout = float(timeout_oru) )
        conn.request('POST', '/', msg.encode('latin_1'))
        response = conn.getresponse()
        log.debug('response status: %s', response.status)
        data = response.read()
        log.debug('response data: %s', data)

        if response.status == 200:
            cambio_estado_log_HL7(id_hl7_log, 1)

        if response.status != 200:
            raise Exception(data)

    except Exception as e:
        log.error(e)
        try: 
            cambio_estado_log_HL7(id_hl7_log, 2)
        except Exception as e: 
            log.error(e)
            raise
            # TODO: si hay un error se tendria que hacer algo, 
            #       como marcar el informe como NO enviado para reprocesarlo
            #       con un timer o algo asi...
        try: 
            # Cerrar la conexión
            conn.close()
        except Exception as e: 
            log.error(e)
            raise

    return True

def consulta_pacientes(id_unico_hl7):
    """
    La consulta de pacientes solo se llega a hacer en el index de pacientes, si
    está activa la clave HL7.CONSULTA_PACIENTES.ACTIVO.
    Siempre se hace por el IDUNICO del paciente, no por el NHC+CENTRO. Por lo
    tanto, en el MSH no se indicará ningún centro.
    Si requieren un centro tendrá que ser una constante, y eso se puede poner
    desde Mirth.
    """
    #QBP_RSP
    tipo_mensajeria = config.get('HL7.CONSULTA_PACIENTES.TIPO', 'QBP_RSP')
    destino_ = config.get('HL7.CONSULTA_PACIENTES.DESTINO', '127.0.0.1:6000')
    pacientes=[]
    if tipo_mensajeria == 'QBP_RSP':
        # MSH
        msh = _make_MSH(None, "QBP", "Q22", "QBP_Q21")
        
        # QPD
        qpd = 'QPD|Q22^FindCandidates^HL7|%s|@PID.3.1^%s~@PID.3.5^%s'

        tipo_identificador = 'PI'
        if config.get('ID_UNICO_PACIENTE') == 'CIP': # XXX deberia usarse IDENTIFICADORES_PACIENTE ?
            tipo_identificador = 'JHN'

        query_tag = endosys.lib.hl7_wrapper.datetime_to_hl7(datetime.datetime.now())
        qpd = qpd % (   query_tag,
                        id_unico_hl7,
                        tipo_identificador
                    )
        #rcp
        rcp = 'RCP|I||'
        #rcp = unicode(rcp)

        msg = msh + qpd + '\r' + rcp

        ########################### ENVIO ##############################################

        id_hl7_log = nuevo_log_HL7_output(msg_out = msg)
        log.debug('enviar mensaje HL7: %s' % msg)

        import httplib
        try:
            validacion_envio = False

            conn = httplib.HTTPConnection( destino_, timeout = float(config.get('HL7.CONSULTA_PACIENTES.TIMEOUT', 30)) )
            conn.request('POST', '/', msg.encode('latin_1'))
            response = conn.getresponse()
            log.debug('response status: %s', response.status)
            data = response.read()
            log.debug('response data: %s', data)


            if response.status in (200, 404):
                cambio_estado_log_HL7(id_hl7_log, 1)
                validacion_envio =True

            if response.status == 404:
                pacientes = []

            elif response.status == 200:
                ipaddress = obtener_request_ip(request)
                hl7_process = endosys.lib.hl7_wrapper.receiving.Hl7Process(data)
                hl7_process.ipaddress = ipaddress
                pacientes = hl7_process.procesar_mensaje()

            else:

                raise Exception(_("Error en sistema externo"))

        except Exception as e:
            log.error(e)
            if validacion_envio is False:
                try: cambio_estado_log_HL7(id_hl7_log, 2)
                except Exception as e: log.error(e)

            try: conn.close()
            except Exception as e: log.error(e)

            raise

    elif tipo_mensajeria == 'QRY_ADR':
        log.error("QRY_ADR not implemented yet")

    return pacientes

def consulta_citas(codigo_agenda, fecha):
    # NOTA: Copiado de consulta_pacientes()
    #SQM_SQR
    tipo_mensajeria = config.get('HL7.CONSULTA_CITAS.TIPO', 'SQM_SQR')
    destino_ = config.get('HL7.CONSULTA_CITAS.DESTINO', '127.0.0.1:6000')
    citas = []
    if tipo_mensajeria == 'SQM_SQR':
        # MSH
        msh = _make_MSH(None, "SQM", "S25", "SQM_S25")

        # QRD
        qrd = 'QRD|%s|T|I|%s|||0||OTH|^^^%s\r'
        param = endosys.lib.hl7_wrapper.datetime_to_hl7(datetime.datetime.now())
        qrd = qrd % (param, param, codigo_agenda)

        # QRF
        qrf = 'QRF||%s|%s\r'
        param = endosys.lib.hl7_wrapper.datetime_to_hl7(fecha)
        qrf = qrf % (param, param)

        msg = msh + qrd + qrf
        
        # XXX PRUEBA
        #msg = 'MSH|^~\&|INSIS||||20150526171336|USER_TEST|SQM^S25^SQM_S25|5874589635|T|2.5|1||||ESP|UNICODE UTF-8\r'
        #msg = msg + 'QRD|20150526171336|T|I|3692581476|||0|^^^^^^^^^^^^^EOXIOU&&1|OTH|^^^0001\r'
        #msg = msg + 'QRF|INSIS|20150526171336|20150526181336\r'
        ############

        ########################### ENVIO ##############################################

        id_hl7_log = nuevo_log_HL7_output(msg_out = msg)
        log.debug('enviar mensaje HL7: %s' % msg)

        import httplib
        try:
            validacion_envio = False

            conn = httplib.HTTPConnection( destino_, timeout = float(config.get('HL7.CONSULTA_CITAS.TIMEOUT', 30)) )
            conn.request('POST', '/', msg.encode('latin_1'))
            response = conn.getresponse()
            log.debug('response status: %s', response.status)
            data = response.read()
            log.debug('response data: %s', data)

            
            if response.status in (200, 404):
                cambio_estado_log_HL7(id_hl7_log, 1)
                validacion_envio =True
            
            if response.status == 404:
                citas = []

            elif response.status == 200:
                ipaddress = obtener_request_ip(request)
                hl7_process = endosys.lib.hl7_wrapper.receiving.Hl7Process(data)
                hl7_process.ipaddress = ipaddress
                citas = hl7_process.procesar_mensaje()

            else:

                raise Exception(_("Error en sistema externo"))

        except Exception as e:
            log.error(e)
            if validacion_envio is False:
                try: cambio_estado_log_HL7(id_hl7_log, 2)
                except Exception as e: log.error(e)

            try: conn.close()
            except Exception as e: log.error(e)

            raise
            
    else:
        raise Exception(_("Consulta de citas HL7: Solo se soporta SQM_SQR"))

    return citas

def enviar_captura_actividad(cita, estado, motivo_id=None):
    """
    Genera un mensaje ORR (o ORM) a partir de la información de una exploración y
    lo envía a Mirth, para que lo transforme y lo reenvíe al HIS.

    4-12-2014:
    Además también se puede enviar un ADT^A04/A11, ya que es más correcto como
    respuesta a las citas (SIU). El ORR/ORM es más correcto como respuesta a
    las peticiones (ORM).
    Si se envía ORR/ORM, se enviará primero, y luego el ADT. ojo!, en ese caso
    si falla el envío del ORR/ORM luego ya no se envía el ADT.

    params:
      cita             registro de bbdd
      estado           true = cita finalizada, false=cita cancelada
      motivo_id      identificador interno del motivo de cancelacion

    XXX Falta:
            ·Controlar la respuesta de Mirth. Si es distinto de "200 OK", ahora
             lanza una excepción...

    LIMITACIONES:
        ·en PID solo se indica el NHC
    """
    import urlparse

    # mirar si existe el registro asociado de cita en cita_ex, o de worklist
    if not cita.ex and not cita.work:
        log.debug('la cita no tiene CITA_EX ni WORK asociado, por lo que no se enviara el mensaje ORR/ORM/ADT a Mirth')
        return False

    #si la cita esta finalizada y tiene una exploracion asociada
    if cita.exploracion and estado:
    # if hasattr(cita, 'exploracion') and estado:
        if not cita.exploracion.fecha:
            fechahora = None
        elif not cita.exploracion.hora:
            fechahora = cita.exploracion.fecha
        else:
            fechahora = datetime.datetime(cita.exploracion.fecha.year, cita.exploracion.fecha.month, cita.exploracion.fecha.day, cita.exploracion.hora.hour, cita.exploracion.hora.minute, cita.exploracion.hora.second)
        fecha_expl = endosys.lib.hl7_wrapper.datetime_to_hl7(fechahora)  # Hasta la versión 2.3.3.4 se enviaba solo la fecha!
        id_expl = cita.exploracion.id
        estado_order = 'CM'
    #si la cita esta cancelada no tiene exploración
    else:
        fecha_expl = ''
        id_expl = ''
        estado_order = 'CA'

    motivoCancelacion = None
    q = meta.Session.query(MotivoCancelacion).filter( MotivoCancelacion.id == motivo_id )
    if q.count():
        motivoCancelacion = q.one()

    # leer config
    destino_ = config.get('ENVIAR_CAPTURA_ACTIVIDAD.DESTINO', '127.0.0.1:6000')

    # variables para diferenciar las tipos de mensajeria posibles ORR - ORM - ADT
    tipo_mensaje = config.get('ENVIAR_CAPTURA_ACTIVIDAD.TIPO', 'ORR').upper()
    if tipo_mensaje in ('ORR', 'ORR+ADT'):      tipo_mensaje_order = 'ORR'
    elif tipo_mensaje in ('ORM', 'ORM+ADT'):    tipo_mensaje_order = 'ORM'
    else:                                       tipo_mensaje_order = None

    envia_mensaje_ADT = tipo_mensaje in ('ADT', 'ORR+ADT', 'ORM+ADT')


    # MENSAJE ORR/ORM
    msg_order = None
    if tipo_mensaje_order:

        # MSH
        if tipo_mensaje_order == 'ORR':
            msh = _make_MSH(cita.agenda.servicio.centro, "ORR", "O02", "ORR_O02")
        else: #ORM
            msh = _make_MSH(cita.agenda.servicio.centro, "ORM", "O01", "ORM_O01")

        # PID
        pid = _make_PID(cita.agenda.servicio.centro, cita.paciente)

        # OBR
            #   OBR.2.1     NUMERO_PETICION
            #   OBR.3.1     ID_EXPLORACION_ENDOTOOLS
            #   OBR.4.1     COD_PRESTACION
            #   OBR.4.2     NOMBRE_PRESTACION
            #   OBR.7.1     FECHAHORA
            #   OBR.18.1    PLACER_FIELD_1 (para Candelaria significa TIPO_DEPART)
            #   OBR.19.1    PLACER_FIELD_2 (para Candelaria significa COD_DEPART)
            #   OBR.24.1    DIAGNOSTIC_SERV_SECT_ID (para Candelaria significa PROVEEDOR)

        # recoge de BBDD el mismo segmento OBR recibido en la petición y le
        # asigna el id_expl y fecha_expl en los campos correspondientes

        # Prestación (OBR.4): Si ya se tenía un segmento OBR (extraído de la petición ORM)
        #   no se vuelve a asignar, pues ya venía en el OBR.4.
        #   Si no se tenía (porque se usan citas SIU, no peticiones) se tiene que asignar.
        #   En este caso se puede asignar la extraída del SIU (del SCH.6) y que es la
        #   pedida (ordered), o se puede usar la realmente realizada (performed), extraída
        #   de uno campo de formulario. Esto se configura en el INI.
        #   (Esta funcionalidad se podría añadir también aunque vaya por peticiones)

        if cita.work:
            obr_prestacion = (cita.work.schProcStepID or endosys.lib.hl7_wrapper.HL7_ABSENT) + '^' + (cita.work.schProcStepDescription or endosys.lib.hl7_wrapper.HL7_ABSENT)
            obr = 'OBR|1|%s|%s|%s|||%s|||||||||||||||||\r'
            obr = obr % (   cita.work.placerOrderNumber or '',
                        id_expl or '',
                        obr_prestacion,
                        fecha_expl
                    )
            obr = unicode(obr, 'latin_1')
            # XXX NOTA: en el caso de worklist, no se ha implementado el "campo_prestacion_realizada"

        elif cita.ex.obr:
            obr = unicode(cita.ex.obr, 'latin_1')
            obr = hl7.parse(obr).segment('OBR')   #   XXX si "cita.ex.obr" no tiene un segmento válido dará error
            obr[3] = id_expl
            obr[7] = fecha_expl
            obr = unicode(obr) + '\r'

        else:
            # gestionar la prestación, tal como se indica mas arriba
            obr_prestacion = (cita.ex.prestacion_cod or endosys.lib.hl7_wrapper.HL7_ABSENT) + '^' + (cita.ex.prestacion_descr or endosys.lib.hl7_wrapper.HL7_ABSENT)

            campo_prestacion_realizada = config.get('ENVIAR_CAPTURA_ACTIVIDAD.CAMPO_PRESTACION_REALIZADA', None)
            if campo_prestacion_realizada:
                # buscar el valor del campo
                try:
                    if cita.exploracion:
                        log.debug( 'campo_prestacion_realizada=%s' % (campo_prestacion_realizada,) )
                        q = meta.Session.query(Campo).filter( Campo.nombre == campo_prestacion_realizada )
                        log.debug( 'total campos encontrados: %s' % (q.count(),) )
                        campo_prestacion_realizada_id = q.one().id
                        log.debug( 'campo_prestacion_realizada_id: %s' % (campo_prestacion_realizada_id,) )
                        log.debug( 'cita.exploracion_id: %s' % (cita.exploracion_id,) )
                        q = meta.Session.query(ValorSelec).filter( and_(
                                ValorSelec.exploracion_id == cita.exploracion_id,
                                ValorSelec.campo_id == campo_prestacion_realizada_id
                        ))
                        log.debug( 'total valores encontrados: %s' % (q.count(),) )
                        elemento_prestacion_realizada = q.one().elemento
                        obr_prestacion =    obr_prestacion + '^^' +\
                                            (elemento_prestacion_realizada.codigo or endosys.lib.hl7_wrapper.HL7_ABSENT) + '^' +\
                                            (elemento_prestacion_realizada.nombre or endosys.lib.hl7_wrapper.HL7_ABSENT)

                except Exception as e:
                    log.error( 'Ha ocurrido un error obteniendo el valor del campo de prestación realizada: %s' % (e,) )

            # #############################
            obr = 'OBR|1|%s|%s|%s|||%s|||||||||||||||||\r'
            obr = obr % (   cita.ex.numero_peticion or '',
                        id_expl or '',
                        obr_prestacion,
                        fecha_expl
                    )
            obr = unicode(obr, 'latin_1')

        # ORC
            # ORC 1.1 ACCION A REALIZAR SEGUN PETICIONARIO, EN NUESTRO CASO SIEMPRE ES 'NW'
            # ORC 2.1 ID PETICION SELENE
            # ORC 5.1 ACCION REALIZADA EN NUESTRO SISTEMA CA= PRUEBA CANCELADA CANCELAR // CM=PRUEBA FINALIZADA
            # ORC 16 (ORDER CONTROL CODE REASON), motivo de cancelacion
            # ORC 16.1 codigo de candelacion
            # ORC 16.2 descripcion de la cancelacion

        if cita.work:
            orc_motivo_cancel = endosys.lib.hl7_wrapper.HL7_ABSENT
            if motivoCancelacion:
                orc_motivo_cancel = motivoCancelacion.codigo + '^' + motivoCancelacion.nombre
            orc = 'ORC||%s|%s||%s|||||||||||%s|||||||||\r'
            orc = orc % (   cita.work.placerOrderNumber or '',
                        id_expl or '',
                        estado_order or '',
                        orc_motivo_cancel
                    )
            orc = unicode(orc, 'latin_1')
            
        elif cita.ex.orc:
            orc = unicode(cita.ex.orc, 'latin_1')
            orc = hl7.parse(orc).segment('ORC')
            orc[5] = estado_order

            if motivoCancelacion:
                orc[16] = unicode(motivoCancelacion.codigo, 'latin_1') + '^' + unicode(motivoCancelacion.nombre, 'latin_1')
            orc = unicode(orc) + '\r'

        else:
            orc_motivo_cancel = endosys.lib.hl7_wrapper.HL7_ABSENT
            if motivoCancelacion:
                orc_motivo_cancel = motivoCancelacion.codigo + '^' + motivoCancelacion.nombre

            orc = 'ORC||%s|%s||%s|||||||||||%s|||||||||\r'
            orc = orc % (   cita.ex.numero_peticion or '',
                        id_expl or '',
                        estado_order or '',
                        orc_motivo_cancel
                    )

            orc = unicode(orc, 'latin_1')

        # PV1
            # PV1 19 OJO SE HA IMPLEMENTADO EXCLUSIVAMENTE PARA CANDELARIA PARA DEVOLVER EL NUMERO DE CITA
            # 5-2-2015 hemos detectado que el pv1 en el ORR no cumple con el estandar, se debería de quitar
            # 1-2-2018 Para evitar fallos si no tiene un segmento pv1 de una cita, por defecto se usa un segmento PV1 vacío
        if cita.work:
            pv1 = unicode('PV1||', 'latin_1')
        else:
            pv1 = unicode(cita.ex.pv1 or 'PV1||', 'latin_1')
        if pv1:
            pv1 = pv1 + '\r'

        # CTI
        #   CTI.1   ACCESSION NUMBER (sólo de Worklist)

        # A partir de 2.4.17 - Si tiene cita de Worklist, se añade el AccessionNumber
        # en el nuevo segmento CTI (según requisitos de Parc Tauli).
        # En caso contrario, no se añade el segmento.
        if cita.work:
            cti = 'CTI|%s\r'
            cti = cti % cita.work.accessionNumber
        else:
            cti = ''    
        cti = unicode(cti, 'latin_1')

        msg_order = msh + pid + pv1 + orc + obr + cti

    # MENSAJE ADT (A04 o A11)
    msg_ADT = None
    if envia_mensaje_ADT:

        # MSH
        if estado:
            # finalizada
            msh = _make_MSH(cita.agenda.servicio.centro, "ADT", "A04", "ADT_A01")
        else:
            # NO finalizada
            msh = _make_MSH(cita.agenda.servicio.centro, "ADT", "A11", "ADT_A09")

        # PV2
        if estado:
            # finalizada
            pv2 = ""
        else:
            # NO finalizada
            pv2 = "PV2|||%s||||" % (motivoCancelacion.codigo)

        pv2 = unicode(pv2, 'latin_1')

        # PID
        pid = _make_PID(cita.agenda.servicio.centro, cita.paciente)
        
        # PV1
            # PV1 19    En Selene (HULAMM...) le llaman "acto clinico". Parece que
            #          es lo único que neesitan para identificar la "cita" según
            #          los ejemplos (coincide con el "numero de cita", del SCH.1).
            # 1-2-2018 Para evitar fallos si no tiene un segmento pv1 de una cita, por defecto se usa un segmento PV1 vacío
        pv1 = unicode(cita.ex.pv1 or 'PV1||', 'latin_1')
        pv1 = pv1 + '\r'
    ##  pv1 = pv1 % (cita.ex.numero_cita)

        msg_ADT = msh + pid + pv1 + pv2

    #   PLUGIN
    #   (pasar los msgs como parametros de esta manera para que se puedan modificar en la funcion)
    if pluginHL7:
        #print 'tiene pluginHL7'
        #print msg_order
        #print msg_ADT
        msgs = {
            'msg_order': msg_order,
            'msg_ADT': msg_ADT
        }
        pluginHL7.enviar_captura_actividad(msgs, cita, estado, motivo_id)
        msg_order = msgs['msg_order']
        msg_ADT = msgs['msg_ADT']
        #print msg_order
        #print msg_ADT
    #   #########

    #   enviar el mensaje a Mirth
    #   siempre devolverá 200 OK, independientemente de que el reenvío al HIS
    #   sea correcto (si falla es "problema" del Mirth, queda marcado como error)
    #   si el mensaje no se llega a enviar por problemas de comunicación,
    #   request() lanza una excepción. Esto si que lo tiene que tratar EndoTools!
    #   NOTA:   finalmente hago que si Mirth devuelve un codigo distinto de 200
    #           significa que necesita que se le vuelva a enviar el mensaje, lo
    #           mismo que si no le hubiera llegado.
    import httplib
    
    conn = None
    id_hl7_log = None
    if not id_expl: id_expl = None
    try:
        #hemos duplicado esta linea para que tenga mas sentido el hl7 log de salida
        #conn = httplib.HTTPConnection( destino_, timeout = float(config.get('ENVIAR_CAPTURA_ACTIVIDAD.TIMEOUT', 30)) )
        if msg_order:

            id_hl7_log = nuevo_log_HL7_output(msg_out = msg_order, idunico = cita.paciente.idunico, exploracion_id = id_expl)

            conn = httplib.HTTPConnection( destino_, timeout = float(config.get('ENVIAR_CAPTURA_ACTIVIDAD.TIMEOUT', 30)) )

            log.debug('enviar mensaje HL7: %s' % msg_order)
            conn.request('POST', '/', msg_order.encode('latin_1'))
            response = conn.getresponse()
            log.debug('response status: %s', response.status)
            data = response.read()
            log.debug('response data: %s', data)
            if response.status != 200: raise Exception(data)

            cambio_estado_log_HL7(id_hl7_log, 1)

        if msg_ADT:

            id_hl7_log = nuevo_log_HL7_output(msg_out = msg_ADT, idunico = cita.paciente.idunico, exploracion_id = id_expl)

            conn = httplib.HTTPConnection( destino_, timeout = float(config.get('ENVIAR_CAPTURA_ACTIVIDAD.TIMEOUT', 30)) )

            log.debug('enviar mensaje HL7: %s' % msg_ADT)
            conn.request('POST', '/', msg_ADT.encode('latin_1'))
            response = conn.getresponse()
            log.debug('response status: %s', response.status)
            data = response.read()
            log.debug('response data: %s', data)
            if response.status != 200: raise Exception(data)

            cambio_estado_log_HL7(id_hl7_log, 1)

    except Exception as e:

        log.error(e)

        try:
            if id_hl7_log != None: cambio_estado_log_HL7(id_hl7_log, 2)
        except Exception as e:
            log.error(e)

        #   XXX si hay un error se tendria que hacer algo, como marcar el informe
        #      como NO enviado para reprocesarlo con un timer o algo asi...

        #   intentar cerrar la conexión
        try:
            if conn != None: conn.close()
        except Exception as e:
            pass

        raise

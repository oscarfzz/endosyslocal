import os
import logging

from xml.etree.ElementTree import Element, SubElement, tostring

from endotools.lib.genericREST import *

from authkit.authorize.pylons_adaptors import authorized, authorize, NotAuthorizedError, NotAuthenticatedError
from authkit.permissions import RemoteUser, ValidAuthKitUser, UserIn, HasAuthKitRole, And
from authkit.users.sqlalchemy_driver import UsersFromDatabase
from pylons import config
from endotools.lib.misc import obj_to_xml
import simplejson

log = logging.getLogger(__name__)

class OpcionesconfigController(BaseController):

    _opciones_basicas = {
        'THEME_ENDOTOOLS': 'classic',
        'EWC_MODO.ACTIVO':0,
    }

    _opciones = {   'MOSTRAR_BOTONES_MODIFICACION_PACIENTES': 0,
                    'MOSTRAR_OPCION_NUEVA_EXPLORACION': 0,
                    'FIRMA_ELECTRONICA.ACTIVO': 0,
                    'MOSTRAR_OPCION_GESTION_CITAS': 0,
                    'FORMATO_INFORMES': 'html',
                    'PERMITIR_CAMBIAR_TIPO_EXPLORACION_DE_CITA': 0,
                    'GRUPOS_CAMPOS_USAR_TABS': 0,
                    'INTEGRACION_SIHGA': 0,
                    'MOSTRAR_PRESTACION_EN_CITAS': 0,
                    'COLUMNAS_CITAS': '',
                    'IDENTIFICADORES_PACIENTE': 'IDUNICO',
                    'IDUNICO_LABEL': 'Identificador',                   # permite cambiar la etiqueta mostrada para el campo CIP. p.ej. "NUHSA" en el caso de Huelva/Andaluc?a
                    'CIP_LABEL': 'CIP',
                    'USAR_MOTIVO_CANCELACION': 1,                       # indica si se utilizar? la funcionalidad de indicar el motivo de cancelaci?n de EndoTools (ojo: es independiente del de SIHGA, motivo de fallo!)
                    'PACIENTES_DESHABILITADOS': 0,                      # activa las opciones relativas a los pacientes deshabilitados en la aplicaci?n: XXX No hace nada, no se ha implementado ninguna funcionalidad dependiente de esta opci?n
                    'FORMULARIOS.LABELS.MODO': 1,                       # indica el modo de los labels, a la izquierda o encima de los campos (1 o 2)
                    'FORMULARIOS.LABELS.ANCHO': 0,                      # indica el ancho de los labels, en pixels (solo util cuando est?n a la izq)
                    'FORMULARIOS.LABELS.FONTSIZE': 0,                   # indica el tama?o de fuente de los labels (se recomienda en %, p.e. "75%")
                    'TIPOS_EXPLORACION.BOTONES.MULTIPLES_COLUMNAS': 0,  # indica si en la pantalla de seleccion de tipo de expl se mostrar?n los botones en varias columnas. Util si hay muchos.
                    'DEVELOPMENT': 0,
                    'PACIENTES_DESHABILITADOS.INCLUIR_POR_DEFECTO': 0,  # indica si por defecto se activa el check de "pacientes deshabilitados" en la busqueda de pacientes
                    'CAMPOS_CALCULADOS': 0,                             # si se usar? la funcionalidad de campos calculados (en cliente, javascript)
                    'THEME_ENDOTOOLS': 'pentax',    
                    'CONFIRMACION_PACIENTE_CITAS': 0,
                    'MOSTRAR_COLUMNA_CENTRO_EN_EXPLORACIONES': 0,
                    'CITAS_PENDIENTES_MODO': 0,
                    'CITAS_PENDIENTES_REFRESCO': 0,
                    'IMAGEN_UPLOAD_SIZE': 1000000,
                    'TIPOS_EXPLORACION.MOSTRAR_NUMERO': 0,              # Obsoleta a partir de 2.4.8 - Se mantiene por compatibiliad de 2.4.7
                    'TIPOS_EXPLORACION.MOSTRAR_CONTADOR': 0,            # 0=NO(*Default) | 1=SI. Nueva en 2.4.8 - Reemplazo de TIPOS_EXPLORACION.MOSTRAR_NUMERO
                    'MOSTRAR_COLUMNA_SERVICIO_EN_EXPLORACIONES': 0,
                    'MOSTRAR_OPCION_CITAS_PENDIENTES': 1,               # 1 'mostrar' - 0 'ocultar' / 1 por defecto para mantener compatibilidad co versiones anteriores que siempre les aparecia esta opcion
                    'ENTORNO': 'PRODUCCION',
                    'MOSTRAR_ATRAS_EXPLORACION' : 0,                    # 1 mostrar 0 ocultar / 0 por defecto,
                    'CIERRE_SESION.ACTIVO': 0,                          # 0 desactivad / 1 activado
                    'CIERRE_SESION.TIEMPO': 28800000,                   # tiempo maximo de sesion/ 8 horas por defecto
                    'CIERRE_SESION.TIEMPO_AVISO': 30000,                # Cantidad de tiempo en la que aparece el aviso de cierre de sesion / 30 segundos por defecto
                    'WORKSTATIONS.PERMITIR_SIN_IP': 0,
                    'GESTION_AGENDA.CELDA.MINUTOS': 30,                 # Cantidad de minutos que contiene una celda del intervalo
                    'GESTION_AGENDA.CELDA.ALTURA': 20,                  # altura en pixeles de la celda de la agenda 
                    'GESTION_AGENDA.CITA.FORMATO_TITULO': '$historia',  # formato por defecto del titulo de la cita 
                    'GESTION_AGENDA.CITA.TIEMPO_POR_DEFECTO': 30,       # Tiempo por defecto en una cita
                    'PACIENTE.NHC_AUTOMATICO': 0,                       # 0 (defecto): no usa nhc automatico / 1: si usa nhc automatico
                    'CITAS_PENDIENTES_BUSQUEDA_POR_HISTORIA': 1,            # 1 (defecto)
                    'NOTIFICACIONES.REFRESCO': 60000,                   # 60000 por defecto / 1 minuto
                    'HABILITAR_CODIGOS_ELEMENTOS': 0,
                    'PERMITIR_API_KEY': 0,
                    'HL7.APPLICATION_ID': 'endotools',
                    'HL7.EXTERNAL_APPLICATION_ID': 'HIS',
                    'HL7.FUSIONES.MODO': 0,
                    'CANCELAR_CITAS_EXPLORACIONES': 1,
                    'PACIENTE.PERMITIR_EDITAR_IDUNICO': 0
               }


    def __init__(self, *args, **kwargs):
        BaseController.__init__(self, *args, **kwargs)

##  @authorize(RemoteUser())
    def index(self, format='xml'):
        basicas = request.params.get('basicas', None)
        if basicas:
            lista_opciones = self._opciones_basicas
        else:
            if not authorized(RemoteUser()): raise NotAuthenticatedError
            lista_opciones = self._opciones

        data = []
        for opcion, valor in lista_opciones.iteritems():
            data.append({
                'id': opcion,
                'valor': formatea_valor( config.get(opcion, valor) )
            })

        response.headers['cache-control'] = "no-cache, no-store, must-revalidate"
        if format == 'xml':
            response.content_type = "text/xml"
            return tostring(obj_to_xml(data, 'opcionConfig', 'opcionesConfig'))
        elif format == 'json':
            response.content_type = "application/json"
            return simplejson.dumps(data)


    def show(self, id, format='xml'):
        """
        XXX  se usa? seria necesario devolver las basicas?
        """
        if format == 'xml':
            response.content_type = "text/xml"
            response.headers['cache-control'] = "no-cache, no-store, must-revalidate"

            v = config.get(id, self._opciones.get(id, None))
            if v is None: abort(404)
            root = Element('opcionConfig', {'id': id})
            SubElement(root, 'valor').text = formatea_valor(v)

            return tostring(root)

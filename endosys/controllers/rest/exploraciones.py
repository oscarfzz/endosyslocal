import time
import datetime
import logging
from pylons.i18n import _
from endosys.model import meta
from endosys.model.exploraciones import Exploracion, Rel_Formularios_Exploraciones
from endosys.model.exploraciones_dicom import Exploracion_dicom
from endosys.model.citas import Cita
from endosys.model.motivosCancelacion import motivo_by_id
from endosys.model import Paciente
from xml.etree.ElementTree import Element, SubElement, tostring
from endosys.lib.genericREST import *
from authkit.authorize.pylons_adaptors import authorized, authorize, authorize_request, NotAuthorizedError
from authkit.permissions import RemoteUser, ValidAuthKitUser, UserIn, HasAuthKitRole, And
from endosys.lib.usuarios.seguridad import roles
from endosys.lib.plugins.base import *
from endosys.config.plugins import pluginExploraciones
from endosys.lib.plugins.base.exploraciones import Exploracion_DICOM_data
import endosys.lib.dicom
import endosys.lib.dicom.util
from endosys.lib.formularios import nuevo_valor
from endosys.lib.busquedas import ejecutar_busqueda
import endosys.lib.registro as registro
import endosys.lib.organizacion_centros as organizacion_centros
from endosys.lib.misc import *
from endosys.lib.exploraciones import *
from sqlalchemy.sql import or_
from pylons import config
from endosys.lib.dicom.util import create_series_instance_uid

log = logging.getLogger(__name__)

class ExploracionesController(GenericRESTController):

    def __init__(self, *args, **kwargs):
        GenericRESTController.__init__(self, *args, **kwargs)
        self.tabla = Exploracion
        self.nombre_recurso = 'exploracion'
        self.nombre_recursos = 'exploraciones'
        self.campos_index = ('id', 'tipoExploracion', 'estado', 'paciente', 'fecha', 'hora', 'medico', 'numero', 'exploracion_dicom', 'cita', 'medico_id', 'paciente_id', 'centro', 'servicio')

    '''
    Asignar formularios a una exploracion
    '''
    def _asignar_formularios(self,exploracion):

        for f in exploracion.tipoExploracion.formularios:
            rel = Rel_Formularios_Exploraciones()
            rel.formulario_id = f.formulario_id
            rel.exploracion_id = exploracion.id
            exploracion.formularios.append(rel)

        meta.Session.commit()    # si no se hace este commit, luego no estan actualizadas las propiedades del obj, de la relacion...

    '''
    Asignar valores por defecto a una exploracion
        - Recorrer todos los formularios de la exploracion, y de cada formulario
        - Recorrer todos sus campos, y asignar el valor por defecto (si tiene)
    '''
    def _asignar_valores_defecto(self,exploracion):

        username = request.environ['REMOTE_USER']
        ipaddress = obtener_request_ip(request)

        campos_ya_asignados = []

        for f in exploracion.formularios:
            # Primero buscar los valores por defecto en la relación campo-formulario
            for c in f.formulario.valoresPorDefecto:
                #print "REL CAMPOS-FORMULARIO: ", c.campo.nombre, c.valor
                if c.valor != None:
                    nuevo_valor(username, ipaddress, f, c.campo.id, c.valor, True)
                    campos_ya_asignados.append(c.campo.id)

            # Luego buscar directamente los de los campos
            for c in f.formulario.campos:
                #print "CAMPO: ", c.campo.nombre, c.campo.valorPorDefecto
                if c.campo.valorPorDefecto != None and (c.campo.id not in campos_ya_asignados):
                    nuevo_valor(username, ipaddress, f, c.campo.id, c.campo.valorPorDefecto, True)
                    campos_ya_asignados.append(c.campo.id)

        meta.Session.commit()

    def _created(self, exploracion):
        """ cuando se crea una exploracion asignarle los formularios predefinidos de ese tipo de exploracion """

        self._asignar_formularios(exploracion)

        username = request.environ['REMOTE_USER']
        ipaddress = obtener_request_ip(request)

        # REGISTRAR
        #   la creacion de la exploracion (XXX se esta haciendo este registro despues del commit...)
        registro.nuevo_registro(username, ipaddress, exploracion, registro.eventos.crear,
        ##                      registro.res.exploracion, None, None, None)
                                registro.res.exploracion, 'NUMERO', None, str(exploracion.numero))

        self._asignar_valores_defecto(exploracion)

    @authorize(HasAuthKitRole([roles.realizar_exploraciones]))
    def create(self, format='xml'):
        #print 'Creando nueva exploracion...'
        username =  request.environ.get('REMOTE_USER', None)
        ipaddress = obtener_request_ip(request)
        medico = medico_from_user(username)

        # XXX de momento esto lo quito, ya avisa la aplicacion web antes de iniciar una exploracion.
        # lo quito porque si no se bloquearia la aplicacion si hay una exploracion con estado=0 porque se habia colgado el IE o algo asi...
##      # comprobar que este medico no tenga una exploracion sin terminar
##      q = Session.query(Exploracion)
##      q = q.filter( and_(Exploracion.medico_id == medico.id, Exploracion.estado == 0) )
##      if q.count() > 0:
##          response.status_code = 400
##          return "error: existe una exploracion sin finalizar del mismo medico"

        p = request.params

        # A partir de la 2.4.7 se requiere que se indique el servicio, que es el "servicio actual de trabajo"
        # seleccionado en el equipo cliente al iniciar sesión
        if not 'servicio_id' in p:
            abort_json(400, _(u'No se ha indicado el servicio de la exploración'), 'ERR_NUEVA_EXPL_SERVICIO_NO_INDICADO')#IDIOMAOK

        # comprobar si se ha indicado el cita_id, y que no sea -1
        self.cita_id = None
        if "cita_id" in p:
            self.cita_id = p.pop("cita_id")
            if self.cita_id == '-1':
                self.cita_id = None
            else:
                log.debug('se ha indicado cita_id. ncita: %s', self.cita_id)
        if not self.cita_id:
            log.debug('NO se ha indicado cita_id')

        if self.cita_id:
            cita = registro_by_id(Cita, self.cita_id)
            #verificar que la cita no ha sido iniciada por otro usuario, antes de iniciar la exploración
            if cita.exploracion_id:
                abort_json(400, _(u'No se puede realizar la exploración, la cita ya ha sido iniciada'), 'ERR_NUEVA_EXPL_CITA_INICIADA')#IDIOMAOK
            #verificar que la cita no ha sido cancelada por otro usuario, antes de iniciar la exploracion
            if cita.cancelada:
                abort_json(400, _(u'No se puede realizar la exploración, la cita ya ha sido cancelada'), 'ERR_NUEVA_EXPL_CITA_CANCALEADA')#IDIOMAOK
            p['aseguradora_id'] = cita.aseguradora_id

        # comprobar que al menos se indique paciente_id y tipoExploracion_id
        #   en teoria si se indica cita_id no haria falta indicar tambien paciente_id, pero
        #   de momento por web siempre se envía.
        if not('paciente_id' in p):
            abort_json(400, _(u'No se ha indicado el paciente'), 'ERR_NUEVA_EXPL_PACIENTE_NO_INDICADO')#IDIOMAOK
        if not('tipoExploracion_id' in p):
            abort_json(400, _(u'No se ha indicado el tipo de exploración'), 'ERR_NUEVA_EXPL_TIPO_EXPL_NO_INDICADO')#IDIOMAOK

        # comprobar que el paciente no este deshabilitado, ya que no se permite realizarle
        # nuevas exploraciones
        paciente = registro_by_id(Paciente, int(p['paciente_id']))
        if paciente.deshabilitado:
            abort_json(400, _(u'El paciente indicado está deshabilitado. No se puede hacer una nueva exploración'), 'ERR_NUEVA_EXPL_PACIENTE_DESHABILITADO')#IDIOMAOK

        # asignar la edad del paciente, en el caso de que tenga fecha de nacimiento
        if paciente.fechaNacimiento:
            p['edad_paciente'] = calcular_edad(paciente.fechaNacimiento)

        if paciente.aseguradora_id and not p.has_key('aseguradora_id'):
            p['aseguradora_id'] = paciente.aseguradora_id;

        # asignar automaticamente el medico a partir del usuario
        p['medico_id'] = formatea_valor(medico.id)
        p['fecha'] = formatea_valor(datetime.datetime.today().date())
        p['hora'] = formatea_valor(datetime.datetime.today().time())
        p['estado'] = '0'

        # asignar el centro por defecto del puesto
        # XXX ya no se usa centro_id a partir de la 2.4.7
        ##p['centro_id'] = organizacion_centros.get_default(username, ipaddress).get('centro_id', None)

        # para el numero de exploracion, coger el ultimo asignado y añadirle 1
        # TODO estaria bien poder configurar que se lleve una numeracion independiente anual.
        q = meta.Session.query(Exploracion)
        n = q.max(Exploracion.numero)
        if n is None: n = 0
        p['numero'] = formatea_valor(n+1)

        # crea el SeriesInstanceUID, este es un UUID aleatorio y tiene que ser generado por 
        # nosotros.
        p['SeriesInstanceUID'] = create_series_instance_uid()

        if format == 'xml':
            resultado = self._doCreate(p)
        else:
            resultado = self._doCreate(p, format)

        return resultado


    def _return_doCreate(self, registro, data):
##  def _return_doCreate(self, registro, root):
        # si se habia indicado un cita_id, asignar a la cita el exploracion_id
        # de esta forma, al llamar a inicia_exploracion ya se sabe si tenia cita o no
        log.debug('(return_docreate) cita_id: %s', self.cita_id) 
        if self.cita_id:
            log.debug('buscar la cita...')
            cita = registro_by_id(Cita, self.cita_id)
            log.debug('asignar el exploracion_id...')
            cita.exploracion_id = registro.id
            meta.Session.update(cita)
            meta.Session.commit()
            log.debug('y guardar la cita')
        log.debug('exploracion creada Ok')

        # por si hay un plugin que haga algo al iniciar (crear) una exploracion.
        # (aprovecho a hacerlo aqui porque tengo acceso al registro recien
        # creado en el doCreate, y necesito el id)
        # XXX controlar si falla, ya que el registro ya esta creado... deberia eliminarlo en ese caso?
        self._inicia_exploracion(registro, request.params)

##      SubElement(root, 'numero').text = formatea_valor(registro.numero)
##      return root
        data['numero'] = formatea_valor(registro.numero)
        return data


    @conditional_authorize(HasAuthKitRole([roles.consultar_exploraciones_todas]))
    def index(self, paciente_id=None, format='xml'):
        p = request.params
        if paciente_id != None: p['paciente_id'] = paciente_id

        if not "dicom" in p:
            # en el caso de que no sea "consultar_exploraciones_todas", filtrar solo las del usuario actual
            username = request.environ.get('REMOTE_USER', registro.DEFAULT_REMOTE_USER)
            medico = medico_from_user(username)

            if not authorized( HasAuthKitRole(roles.consultar_exploraciones_todas) ):
                p['medico_id'] = medico.id

            #saca el parametro borrado si no tiene permisos para consultar borrados
            if not authorized(HasAuthKitRole(roles.borrado_logico)) and 'borrado' in p:
                if int(p["borrado"])==1:
                    abort(403, _(u'El usuario actual no tiene permisos para visualizar exploraciones borradas'))#IDIOMAOK
                #del p['borrado']
        else:
            username="sysadmin"
            medico = medico_from_user(username)
            del p["dicom"]

        p = self._crear_parametros_medico(p, username)

        p = self._procesar_params_especiales(p)

        return self._doIndex(p, format)
##      return GenericRESTController.index(self, format)

    def _filtrar_index(self, query,  format= None):
        # filtro general para acotar de primeras el resultado de las exploraciones
        # a los servicos asignados a un mÃ©dico.
        query = query.filter( or_(Exploracion.servicio_id.in_(self.servicios_del_medico), Exploracion.servicio_id == None))

        # filtrar por fechamin y fecha max
        if self.fecha_min != None:
            t = time.strptime(self.fecha_min, "%d/%m/%Y")
            d = date(t.tm_year, t.tm_mon, t.tm_mday)
            query = query.filter( Exploracion.fecha >= d )

        if self.fecha_max != None:
            t = time.strptime(self.fecha_max, "%d/%m/%Y")
            d = date(t.tm_year, t.tm_mon, t.tm_mday)
            query = query.filter( Exploracion.fecha <= d )

        # fistrar por servicio_activo
        # tambiÃ©n se ha tenido que añadir el filtro de servicio_id = None, para que no se pierda las exploraciones ya
        # realizadas antes de que exita este código, en esas exploraciones no existira servicio_id, a no ser que se migre.
        if self.servicio_activo != None:
            query = query.filter( or_(Exploracion.servicio_id == self.servicio_activo, Exploracion.servicio_id == None) )

        # filtrar por dicom_stored
        if self.dicom_stored != None:
            self.dicom_stored = False if self.dicom_stored == '0' else True
            query = query.filter( Exploracion.exploracion_dicom.has(Exploracion_dicom.stored == self.dicom_stored) )

        # filtrar por datos del paciente (CIP/NUHSA, historia/NHC)
        if self.CIP:
            cip = self.CIP
            query = query.filter( Exploracion.paciente.has(Paciente.CIP == cip) )
        if self.idunico:
            idunico = self.idunico
            query = query.filter( Exploracion.paciente.has(Paciente.idunico == idunico) )

        # filtrar por busqueda avanzada...
        if self.busqueda != None:
            query = ejecutar_busqueda(self.busqueda, query)

        return query

    def _return_doIndex(self, exploraciones, data, format=None):
        if format == "csv":

            # Definido en lib/exploraciones.py
            data = ampliar_data_exploraciones(exploraciones,data,format)

        else:

            """
            añadir info dicom (? creo que no)
            se añade el detalle de la agenda, dentro de la cita, incluyendo el
            servicio y centro

            2.4.7: Poner el centro a partir del servicio, ya que el centro_id ya no se guardará
            """
            for expl in exploraciones:
                a = filter(lambda i: str(i['id']) == str(expl.id), data)
                if len(a) > 0:
                    expl_el = a[0]
                if not expl_el: continue

                #   asignar info del centro
                if expl.servicio:
                    expl_el['centro'] = {
                        'id': formatea_valor(expl.servicio.centro_id),
                        'codigo': formatea_valor(expl.servicio.centro.codigo),
                        'nombre': formatea_valor(expl.servicio.centro.nombre)
                    }
                else:
                    expl_el['centro'] = None

                if expl.paciente:
                    expl_el['paciente']['centros'] = []
                    for centro in expl.paciente.centros:
                        expl_el["paciente"]['centros'].append({
                            'id': formatea_valor(centro.centro_id),
                            'nhc': formatea_valor(centro.nhc)})

                #   info de la cita
                if not expl_el['cita']: continue
                #   añadir agenda
                expl_el['cita']['agenda'] = {'id': formatea_valor(expl.cita.agenda_id)}
                if expl.cita.agenda:
                    expl_el['cita']['agenda']['codigo'] = formatea_valor(expl.cita.agenda.codigo)
                    expl_el['cita']['agenda']['nombre'] = formatea_valor(expl.cita.agenda.nombre)
                    #   añadir servicio
                    expl_el['cita']['agenda']['servicio'] = {
                        'id': formatea_valor(expl.cita.agenda.servicio_id),
                        'codigo': formatea_valor(expl.cita.agenda.servicio.codigo),
                        'nombre': formatea_valor(expl.cita.agenda.servicio.nombre)
                    }
                    #   añadir centro
                    expl_el['cita']['agenda']['servicio']['centro'] = {
                        'id': formatea_valor(expl.cita.agenda.servicio.centro_id),
                        'codigo': formatea_valor(expl.cita.agenda.servicio.centro.codigo),
                        'nombre': formatea_valor(expl.cita.agenda.servicio.centro.nombre)
                    }

                #   añadir campos tabla cita_ex
                if expl.cita and expl.cita.ex:
                    expl_el['cita']['ex'] = {}

                    #expl_el['cita']['ex']['nhc'] = formatea_valor(expl.cita.ex.nhc)
                    expl_el['cita']['ex']['idunico'] = formatea_valor(expl.cita.ex.idunico)
                    expl_el['cita']['ex']['cip'] = formatea_valor(expl.cita.ex.cip)
                    expl_el['cita']['ex']['numero_cita'] = formatea_valor(expl.cita.ex.numero_cita)
                    expl_el['cita']['ex']['numero_episodio'] = formatea_valor(expl.cita.ex.numero_episodio)
                    expl_el['cita']['ex']['numero_peticion'] = formatea_valor(expl.cita.ex.numero_peticion)
                    expl_el['cita']['ex']['prestacion_cod'] = formatea_valor(expl.cita.ex.prestacion_cod)
                    expl_el['cita']['ex']['prestacion_descr'] = formatea_valor(expl.cita.ex.prestacion_descr)
                    expl_el['cita']['ex']['servicio_cod'] = formatea_valor(expl.cita.ex.servicio_cod)
                    expl_el['cita']['ex']['servicio_descr'] = formatea_valor(expl.cita.ex.servicio_descr)
                    expl_el['cita']['ex']['agenda_cod'] = formatea_valor(expl.cita.ex.agenda_cod)
                    expl_el['cita']['ex']['agenda_descr'] = formatea_valor(expl.cita.ex.agenda_descr)
                    expl_el['cita']['ex']['procedencia_cod'] = formatea_valor(expl.cita.ex.procedencia_cod)
                    expl_el['cita']['ex']['procedencia_descr'] = formatea_valor(expl.cita.ex.procedencia_descr)
                    expl_el['cita']['ex']['servicio_peticionario_cod'] = formatea_valor(expl.cita.ex.servicio_peticionario_cod)
                    expl_el['cita']['ex']['servicio_peticionario_descr'] = formatea_valor(expl.cita.ex.servicio_peticionario_descr)
                    expl_el['cita']['ex']['medico_peticionario_cod'] = formatea_valor(expl.cita.ex.medico_peticionario_cod)
                    expl_el['cita']['ex']['medico_peticionario_descr'] = formatea_valor(expl.cita.ex.medico_peticionario_descr)
                    expl_el['cita']['ex']['estado'] = formatea_valor(expl.cita.ex.estado)

                if expl.cita.work:
                    expl_el['cita']['work'] = {}
                    expl_el['cita']['work']['id'] = formatea_valor(expl.cita.work.id)
                    expl_el['cita']['work']['date_queried'] = formatea_valor(expl.cita.work.date_queried)
                    expl_el['cita']['work']['cita_id'] = formatea_valor(expl.cita.work.cita_id)
                    expl_el['cita']['work']['exploracion_id'] = formatea_valor(expl.cita.work.exploracion_id)
                    expl_el['cita']['work']['accessionNumber'] = formatea_valor(expl.cita.work.accessionNumber)
                    expl_el['cita']['work']['patientID'] = formatea_valor(expl.cita.work.patientID)
                    expl_el['cita']['work']['patientName'] = formatea_valor(expl.cita.work.patientName)
                    expl_el['cita']['work']['patientBirthDate'] = formatea_valor(expl.cita.work.patientBirthDate)
                    expl_el['cita']['work']['patientSex'] = formatea_valor(expl.cita.work.patientSex)
                    expl_el['cita']['work']['schProcStepStartDate'] = formatea_valor(expl.cita.work.schProcStepStartDate)
                    expl_el['cita']['work']['schProcStepStartTime'] = formatea_valor(expl.cita.work.schProcStepStartTime)
                    expl_el['cita']['work']['studyInstanceUID'] = formatea_valor(expl.cita.work.studyInstanceUID)
                    expl_el['cita']['work']['schProcStepDescription'] = formatea_valor(expl.cita.work.schProcStepDescription)
                    expl_el['cita']['work']['schProcStepID'] = formatea_valor(expl.cita.work.schProcStepID)
                    expl_el['cita']['work']['reqPhysician'] = formatea_valor(expl.cita.work.reqPhysician)
                    expl_el['cita']['work']['reqService'] = formatea_valor(expl.cita.work.reqService)
                    expl_el['cita']['work']['refPhysicianName'] = formatea_valor(expl.cita.work.refPhysicianName)
                    expl_el['cita']['work']['placerOrderNumber'] = formatea_valor(expl.cita.work.placerOrderNumber)
                    expl_el['cita']['work']['reqProcedureDesc'] = formatea_valor(expl.cita.work.reqProcedureDesc)
                    expl_el['cita']['work']['schProcStepLoc'] = formatea_valor(expl.cita.work.schProcStepLoc)
                    expl_el['cita']['work']['admissionID'] = formatea_valor(expl.cita.work.admissionID)
                    expl_el['cita']['work']['modality'] = formatea_valor(expl.cita.work.modality)


        return data

    def _return_show(self, exploracion, data):
        # rellenar el item formularios ordenado por el orden indicado en rel_Formulario_TipoExploracion
        formularios = []
        for rel in exploracion.formularios:
            lista_exploraciones_tipoexp = [x for x in rel.formulario.tiposExploracion if
                                   x.tipoExploracion_id == exploracion.tipoExploracion_id]

            # Solo ordenamos formularios que tengan actualmente la relación formulario con su tipo de exploracion
            if len(lista_exploraciones_tipoexp) > 0:
                orden = lista_exploraciones_tipoexp[0].orden
            else:
                orden = 0

            formularios.append({
                'id': formatea_valor(rel.formulario.id),
                'titulo': formatea_valor(rel.formulario.titulo),
                'orden': orden
            })

        data['formularios'] = sorted(formularios, key=lambda formulario: formulario['orden'])
        #print exploracion.tipoExploracion_id

        # obtener que numero de exploracion es dentro de las exploraciones del mismo tipo
        if config.get('TIPOS_EXPLORACION.MOSTRAR_NUMERO', '0') == '1' or config.get('TIPOS_EXPLORACION.MOSTRAR_CONTADOR', '0') == '1':
            data['numero_tipo_exploracion'] = obtener_numero_tipo_exploracion(exploracion)

        if exploracion.cita and exploracion.cita.ex:
            data['cita']['ex'] = {}

            #data['cita']['ex']['nhc'] = formatea_valor(exploracion.cita.ex.nhc)
            data['cita']['ex']['idunico'] = formatea_valor(exploracion.cita.ex.idunico)
            data['cita']['ex']['cip'] = formatea_valor(exploracion.cita.ex.cip)
            data['cita']['ex']['numero_cita'] = formatea_valor(exploracion.cita.ex.numero_cita)
            data['cita']['ex']['numero_episodio'] = formatea_valor(exploracion.cita.ex.numero_episodio)
            data['cita']['ex']['numero_peticion'] = formatea_valor(exploracion.cita.ex.numero_peticion)
            data['cita']['ex']['prestacion_cod'] = formatea_valor(exploracion.cita.ex.prestacion_cod)
            data['cita']['ex']['prestacion_descr'] = formatea_valor(exploracion.cita.ex.prestacion_descr)
            data['cita']['ex']['servicio_cod'] = formatea_valor(exploracion.cita.ex.servicio_cod)
            data['cita']['ex']['servicio_descr'] = formatea_valor(exploracion.cita.ex.servicio_descr)
            data['cita']['ex']['agenda_cod'] = formatea_valor(exploracion.cita.ex.agenda_cod)
            data['cita']['ex']['agenda_descr'] = formatea_valor(exploracion.cita.ex.agenda_descr)
            data['cita']['ex']['procedencia_cod'] = formatea_valor(exploracion.cita.ex.procedencia_cod)
            data['cita']['ex']['procedencia_descr'] = formatea_valor(exploracion.cita.ex.procedencia_descr)
            data['cita']['ex']['servicio_peticionario_cod'] = formatea_valor(exploracion.cita.ex.servicio_peticionario_cod)
            data['cita']['ex']['servicio_peticionario_descr'] = formatea_valor(exploracion.cita.ex.servicio_peticionario_descr)
            data['cita']['ex']['medico_peticionario_cod'] = formatea_valor(exploracion.cita.ex.medico_peticionario_cod)
            data['cita']['ex']['medico_peticionario_descr'] = formatea_valor(exploracion.cita.ex.medico_peticionario_descr)
            data['cita']['ex']['estado'] = formatea_valor(exploracion.cita.ex.estado)

        if exploracion.paciente:
            data['paciente']['centros'] = []
            for centro in exploracion.paciente.centros:
                data["paciente"]['centros'].append({
                    'id': formatea_valor(centro.centro_id),
                    'nhc': formatea_valor(centro.nhc)})


    @conditional_authorize(HasAuthKitRole([roles.consultar_exploraciones_todas]))
    def show(self, id, format='xml'):
##      # en el caso de que no sea "consultar_exploraciones_todas", comprobar que sea del usuario actual
##      if not authorized( HasAuthKitRole(roles.consultar_exploraciones_todas) ):
##          medico = medico_from_user(request.environ['REMOTE_USER'])
##          if self._registro_by_id(id).medico_id != medico.id:
##              raise NotAuthorizedError
##
        return GenericRESTController.show(self, id, format)


    def _crear_registro_exploracion_dicom(self, exploracion):
        ''' "exploracion" es el nuevo registro creado en la tabla Exploraciones.
        '''
        ed = Exploracion_dicom()
        ed.exploracion_id = exploracion.id
        ed.stored = False

        dicom_data = None
        if pluginExploraciones:
##          medico = medico_from_user(request.environ['REMOTE_USER'])

            dicom_data = pluginExploraciones.get_datos_dicom(exploracion.id)
##          try:
##              dicom_data = pluginExploraciones.get_datos_dicom(exploracion.id)
##          except PluginException, e:
##              abort_xml(e.http_status, str(e))
##          except Exception, e:
##              abort_xml(500, u'Ha ocurrido un error obteniendo los datos de dicomización de la exploración (%s)' % e)
        else:
            #   si la exploracion tenia cita con info de worklist asociada, se crea
            #   automáticamente un registro en "exploraciones_dicom" con la info
            #   del worklist.
            if exploracion.cita and exploracion.cita.work:
                #print "La exploración tiene cita, asignar los datos del worklist al registro de exploraciones_dicom"
                dicom_data = Exploracion_DICOM_data()
                dicom_data.stored = False
                dicom_data.accessionNumber = exploracion.cita.work.accessionNumber
                dicom_data.studyInstanceUID = exploracion.cita.work.studyInstanceUID

                #   XXX   recoger estos datos del worklist???
                #dicom_data.studyID = exploracion.cita.work.studyID
                #dicom_data.institutionName = exploracion.cita.work.institutionName
                #dicom_data.stationName = exploracion.cita.work.stationName

                dicom_data.patientName = exploracion.cita.work.patientName
                dicom_data.patientBirthDate = exploracion.cita.work.patientBirthDate
                dicom_data.patientSex = exploracion.cita.work.patientSex
##              dicom_data.studyDate = endotools.lib.dicom.util.date_to_DICOM(exploracion.fecha)
##              dicom_data.studyTime = endotools.lib.dicom.util.time_to_DICOM(exploracion.hora)

                dicom_data.studyDescription = exploracion.cita.work.schProcStepDescription

                #dicom_data.placerOrderNumber = exploracion.cita.work.placerOrderNumber # XXX?

        if dicom_data:

            ed.stored = dicom_data.stored

            ed.accessionNumber = dicom_data.accessionNumber
            ed.studyInstanceUID = dicom_data.studyInstanceUID
            ed.studyID = dicom_data.studyID

            ed.institutionName = dicom_data.institutionName
            ed.stationName = dicom_data.stationName

            ed.studyDescription = dicom_data.studyDescription

            #ed.placerOrderNumber = ed.placerOrderNumber # XXX?

            #   datos de pacientes, si no se indican extrarlos de bbdd
            if dicom_data.patientName == None:
                ed.patientName = u'%s %s^%s' % (formatea_valor(exploracion.paciente.apellido1),
                                                formatea_valor(exploracion.paciente.apellido2),
                                                formatea_valor(exploracion.paciente.nombre))
            else:
                ed.patientName = dicom_data.patientName

            if dicom_data.patientBirthDate == None:
                ed.patientBirthDate = endosys.lib.dicom.util.date_to_DICOM(exploracion.paciente.fechaNacimiento)
            elif isinstance(dicom_data.patientBirthDate, datetime.date):
                ed.patientBirthDate = endosys.lib.dicom.util.date_to_DICOM(dicom_data.patientBirthDate)
            else:
                ed.patientBirthDate = dicom_data.patientBirthDate

            if dicom_data.patientSex == None:
                if exploracion.paciente.sexo == 0: ed.patientSex = 'F'
                elif exploracion.paciente.sexo == 1: ed.patientSex = 'M'
                else: ed.patientSex = ''
            else:
                ed.patientSex = dicom_data.patientSex

            #   fecha y hora, si no se indican poner la fecha y hora de la exploracion
            if dicom_data.studyDate == None:
                ed.studyDate = endosys.lib.dicom.util.date_to_DICOM(exploracion.fecha)
            elif isinstance(dicom_data.studyDate, datetime.date):
                ed.studyDate = endosys.lib.dicom.util.date_to_DICOM(dicom_data.studyDate)
            else:
                ed.studyDate = dicom_data.studyDate
            if dicom_data.studyTime == None:
                ed.studyTime = endosys.lib.dicom.util.time_to_DICOM(exploracion.hora)
            elif isinstance(dicom_data.studyDate, datetime.time):
                ed.studyTime = endosys.lib.dicom.util.time_to_DICOM(dicom_data.studyTime)
            else:
                ed.studyTime = dicom_data.studyTime

        meta.Session.save(ed)
        meta.Session.commit()


    def _inicia_exploracion(self, exploracion, params):

        # ejecutar el plugin
        if pluginExploraciones:
            medico = medico_from_user(request.environ['REMOTE_USER'])
            pluginExploraciones.inicia_exploracion(exploracion.id, medico, params)
##          try:
##              pluginExploraciones.inicia_exploracion(exploracion.id, medico, params)
##          except PluginException, e:
##              abort_xml(e.http_status, str(e))
##          except Exception, e:
##              abort_xml(500, _('Ha ocurrido un error iniciando la exploracion (%s)') % e)#IDIOMAOK

        # crear registro en tabla "exploraciones_dicom"
        #print self
        #print self._crear_registro_exploracion_dicom
        self._crear_registro_exploracion_dicom(exploracion)


    def _finaliza_exploracion(self, exploracion):

        # actualizar los campos dicom de la exploracion de fecha y hora
        # XXX   ya lo hago al crear la exploracion
##      endotools.lib.dicom.util.date_to_DICOM()
##      exploracion.exploracion_dicom.studyDate =
##      exploracion.exploracion_dicom.studyTime =
##      Session.commit()

        # ejecutar el plugin
        if pluginExploraciones:
            medico = medico_from_user(request.environ['REMOTE_USER'])
            pluginExploraciones.finaliza_exploracion(exploracion.id, medico)
##          try:
##              pluginExploraciones.finaliza_exploracion(exploracion.id, medico)
##          except PluginException, e:
##              abort_xml(e.http_status, str(e))
##          except Exception, e:
##              abort_xml(500, 'Ha ocurrido un error finalizando la exploracion (%s)' % e)

        # si esta habilitado el envio de imagenes a un pacs, hacerlo ahora
##      if endotools.lib.dicom.PACS.get_store_enabled():
##          endotools.lib.dicom.PACS.store(exploracion.id)

        # enviar a Mirth el mensaje ORR, si está configurado asi, y si tiene cita
        # XXX ya no se utiliza ENVIAR_ORR, ahora es ENVIAR_CAPTURA_ACTIVIDAD!!!
        if (config.get('ENVIAR_CAPTURA_ACTIVIDAD.ACTIVO', '0') == '1'):
            if exploracion.cita:
                import endosys.lib.hl7_wrapper.sending
                endosys.lib.hl7_wrapper.sending.enviar_captura_actividad(exploracion.cita, True)


    def _cancela_exploracion(self, exploracion, motivo_id):
        # ejecutar el plugin
        if pluginExploraciones:
            medico = medico_from_user(request.environ['REMOTE_USER'])
            try:
                pluginExploraciones.cancela_exploracion(exploracion.id, medico)
            except PluginException, e:
                log.error(e)
                abort_xml(e.http_status, str(e))
            except Exception, e:
                log.error(e)
                abort_xml(500, _('Ha ocurrido un error finalizando la exploracion (%s)') % e)#IDIOMAOK

        # Si esta habilitado el envio de imagenes a un pacs, hacerlo ahora
        #if endotools.lib.dicom.PACS.get_store_enabled():
        #   endotools.lib.dicom.PACS.store(exploracion.id)

        # enviar a Mirth el mensaje ORR, si está configurado asi, y si tiene cita
        if config.get('ENVIAR_CAPTURA_ACTIVIDAD.ACTIVO', '0') == '1':
            if exploracion.cita:
                import endosys.lib.hl7_wrapper.sending
                endosys.lib.hl7_wrapper.sending.enviar_captura_actividad(exploracion.cita, False, motivo_id)


    @conditional_authorize(HasAuthKitRole([roles.realizar_exploraciones]))
    def update(self, id):
        #print request.params

        """
        Solo se pueden modificar:
            - estado            => Requerido
            - motivo_id         => Opcional (Verifica que estado=2)
            - orden_capturas    =>

        -----------
        NUEVO 2.4.8
        -----------
        Admite:
            - tipoExploracion_id => Si viene el mismo que el actual no se cambia
            - cita_id            => Si viene el mismo que el actual no se cambia
            - paciente_id        => Si viene el mismo que el actual no se cambia

        """

        ipaddress = obtener_request_ip(request)

        # XXX mejorar esta logica...
        # Si el parametro es "dicom_stored", tratarlo aqui
        if 'dicom_stored' in request.params:
            self._set_dicom_stored(id, request.params['dicom_stored'])
            del request.params['dicom_stored']
            return

        username = request.environ['REMOTE_USER']
        exploracion = self._registro_by_id(id)

        # ----------------------
        # Normativa de seguridad
        # Para poder modificar una exploración ha de corresponder al usuario conectado o
        # tener el permiso de modificar todas
        medico = medico_from_user(username)
        autorizado = ( exploracion.medico_id == medico.id) \
        or (authorized( HasAuthKitRole(roles.modificar_exploraciones_todas) ))

        if not autorizado:
            abort(403, _(u'El usuario actual no puede modificar la exploración'))#IDIOMAOK
        # Fin Normativa
        # ----------------------

        # PACIENTE_ID
        # 2.4.8
        # Esta funcionalidad ya estaba realizada antes de usarla en el "ir hacia atras" de la 2.4.8
        # Hay que revisar si se puede hacer si el estado != 0 (Sin finalizar
        if 'paciente_id' in request.params:
            paciente_id_anterior = exploracion.paciente_id
            paciente_id_nuevo = int(request.params['paciente_id'])

            if paciente_id_anterior != paciente_id_nuevo:

                paciente_nuevo = registro_by_id(Paciente, paciente_id_nuevo)

                if paciente_nuevo.deshabilitado:
                    abort_xml(400, _(u'El paciente indicado está deshabilitado. No se puede cambiar el paciente'))#IDIOMAOK

                exploracion.paciente_id = paciente_id_nuevo
                # actualizar la edad del paciente, en el caso de que tenga fecha de nacimiento,
                # sino asignarle None para que no quede la edad del antiguo paciente.
                if paciente_nuevo.fechaNacimiento:
                    exploracion.edad_paciente = calcular_edad(paciente_nuevo.fechaNacimiento)
                else:
                    exploracion.edad_paciente = None

                if paciente_nuevo.aseguradora_id:
                    exploracion.aseguradora_id = paciente_nuevo.aseguradora_id

                meta.Session.update(exploracion)
                registro.nuevo_registro(username, ipaddress, exploracion,
                                            registro.eventos.modificar,
                                            registro.res.exploracion, 'PACIENTE_ID',
                                            str(paciente_id_anterior),
                                            str(exploracion.paciente_id)
                )
                meta.Session.commit()

        # ORDEN_CAPTURAS
        if 'orden_capturas' in request.params and request.params['orden_capturas']:
            capturas_ids = request.params['orden_capturas'].split(',')
            for index, captura_id in enumerate(capturas_ids):
                for captura in exploracion.capturas:
                    if captura.id == int(captura_id):
                        captura.orden = index
                        meta.Session.update(captura)
            meta.Session.commit()

        if 'aseguradora_id' in request.params:
            if len(request.params['aseguradora_id']) > 0:
                aseguradora_id = request.params['aseguradora_id']
            else:
                aseguradora_id = None
            exploracion.paciente.aseguradora_id = aseguradora_id
            exploracion.aseguradora_id = aseguradora_id
            meta.Session.update(exploracion)
            meta.Session.commit()

        # ESTADO
        if 'estado' in request.params:
            # Para cambiar el estado, de momento que solo pueda el medico que la ha realizado
            # XXX Revisar si es necesario. Mas arriba esto se comprueba pero muestra otro error
            if self._registro_by_id(id).medico_id != medico.id:
                raise NotAuthorizedError

            estado_anterior = exploracion.estado

            # como solo se permite modificar el estado, seguro que se esta finalizando o
            # cancelando la exploracion...
            # si _finaliza_exploracion o _cancela_exploracion lanzan una excepción,
            # la exploracion NO quedará como finalizada/cancelada.
            if (estado_anterior == 0):
                if (request.params['estado'] == '1'):
                    self._finaliza_exploracion(exploracion)
                elif (request.params['estado'] == '2'):
                    # se ha puesto una opción para permitir cancelar sin indicar motivo de cancelación...
                    if (config.get('USAR_MOTIVO_CANCELACION', '1') == '1') and (not 'motivo_id' in request.params):
                        raise NotAuthorizedError
                    self._cancela_exploracion(exploracion, request.params.get('motivo_id', None))

            # hacer el update en la BBDD del campo 'estado'
            params = { 'estado': request.params['estado'] }
            if 'motivo_id' in request.params:
                params['motivo_id'] = request.params['motivo_id']

            # REGISTRAR
            #   la modificación del estado, y el posible motivo de cancelación
            estado_anterior = exploracion.estado
            motivo_id_anterior = exploracion.motivo_id
            self._update_registro_from_params( exploracion, params )
            if estado_anterior != exploracion.estado:
                registro.nuevo_registro(username, ipaddress, exploracion,
                                        registro.eventos.modificar,
                                        registro.res.exploracion, 'ESTADO',
                                        registro.estado_exploracion(estado_anterior),
                                        registro.estado_exploracion(exploracion.estado)
                )
            if motivo_id_anterior != exploracion.motivo_id:
                registro.nuevo_registro(username, ipaddress, exploracion,
                                        registro.eventos.modificar,
                                        registro.res.exploracion, 'MOTIVO CANCELACION',
                                        motivo_by_id(motivo_id_anterior),
                                        motivo_by_id(exploracion.motivo_id)
                )
            # #################################
            meta.Session.commit()


        #2.4.8: se puede modificar el tipo de exploracion usando el ir hacia atras
        if 'tipoExploracion_id' in request.params:

            # Solo actualizar si la exploracion es distinta.
            if (request.params['tipoExploracion_id'] != exploracion.tipoExploracion_id):

                # El tipo de exploracion solo se puede editar si el estado=0
                if exploracion.estado != 0:
                    abort(403, _(u'Solo se puede modificar el tipo de exploración cuando la exploración esta sin finalizar'))#IDIOMAOK
                else:
                    # Se actualiza el tipo de exploracion
                    params = {'tipoExploracion_id': request.params['tipoExploracion_id']}
                    self._update_registro_from_params( exploracion, params )

                    # Se eliminan:
                    # - Valores
                    # - Formularios
                    # - Informes
                    for v in exploracion.valoresTexto:
                        meta.Session.delete(v)
                    meta.Session.commit()
                    for v in exploracion.valoresMulti:
                        meta.Session.delete(v)
                    meta.Session.commit()
                    for v in exploracion.valoresSelec:
                        meta.Session.delete(v)
                    meta.Session.commit()
                    for v in exploracion.valoresBool:
                        meta.Session.delete(v)
                    meta.Session.commit()
                    for f in exploracion.formularios:
                        meta.Session.delete(f)
                    meta.Session.commit()
                    for i in exploracion.informes:
                        # no tendria que tener informes pero igual se intenta borrar (pq estado=0)
                        meta.Session.delete(i)

                    meta.Session.commit()


                    # Asignacion de los formularios
                    self._asignar_formularios(exploracion)

                    # Esto se hace porque sino da error de sqlAlquemy
                    id_exploracion = exploracion.id
                    meta.Session.close()
                    exploracion = registro_by_id(Exploracion, id_exploracion)

                    self._asignar_valores_defecto(exploracion)
                    meta.Session.commit()

        #2.4.8: se puede modificar la cita usando el ir hacia atras
        # No comprueba que el medico que esta editando una cita que no este en sus agendas asignadas

        if 'cita_id' in request.params:
            cita_id = request.params["cita_id"]
            if int(cita_id) > 0:
                cita = registro_by_id(Cita, cita_id)

                if not cita:
                    abort_xml(400, _(u'La cita no existe'))
                else:
                    #Cita ya usada por otra exploracion, no se puede hacer el cambio
                    if cita.exploracion_id and cita.exploracion_id!=exploracion.id:
                        abort_xml(400, _(u'La cita ya esta en uso por otra exploración'))
                    #La cita esta cancelada y no puede usarse
                    if cita.cancelada:
                        abort_xml(400, _(u'La cita ya ha sido cancelada'))

                    # Tengo que sacar la cita que tiene adjunta
                    cita_anterior = meta.Session.query(Cita).filter_by(exploracion_id=exploracion.id).one()
                    if (cita_anterior):
                        cita_anterior.exploracion_id = None
                    meta.Session.commit()

                    # Si llego hasta aqui, entonces puede cambiar la cita a la exploracion
                    cita.exploracion_id = exploracion.id
                    meta.Session.commit()
                    log.debug("Se actualizo la cita")

        if '_recuperar' in request.params:
            recuperar = request.params["_recuperar"]
            if recuperar: #si viene un 1

                # verifica si esta autorizado
                autorizado =  authorized( HasAuthKitRole(roles.borrado_logico))
                if not autorizado:
                    abort(403, _(u'El usuario actual no puede eliminar la exploración'))#IDIOMAOK

                exploracion.borrado = 0
                meta.Session.update(exploracion)
                meta.Session.commit()
                # XXX Esto tiene que ser asi?
                # exploracion.borrado_motivo = ""

                #guarda en el registro
                registro.nuevo_registro(username, ipaddress, exploracion,
                                        registro.eventos.modificar,
                                        registro.res.exploracion, 'BORRADO',
                                        "1",
                                        "0"
                )


    def _set_dicom_stored(self, id, dicom_stored):
        #print '_set_dicom_stored', dicom_stored
        exploracion = self._registro_by_id(id)
        exploracion.exploracion_dicom.stored = True
        meta.Session.commit()

    @conditional_authorize(HasAuthKitRole([roles.modificar_exploraciones_todas]))
    def delete(self, id):
        ''' Borra una exploración. La forma de borrado depende del estado de la exploración.
            Si estado = 0 (sin finalizar): - Hace borrado logico.
                                           - Libera la cita.
                                           - Graba en registro el ID de la cita desvinculada.
                                           - Solo puede hacerlo el medico que hizo la exploración
                                           - NO BORRA si tiene imagenes

            Si estado = 1 (finalizado): - Hace un borrado logico. No libera la cita.
                                           - Solo puede hacerlo un usuario con permisos de borrado_logico

        '''

        # Usuario en sesion
        username = request.environ['REMOTE_USER']
        ip = obtener_request_ip(request)
        medico_conect = medico_from_user(username)

        e = self._registro_by_id(id)

        if e.estado == 0:
            # Sin finalizar.


            # Comprobacion: cantidad de capturas
            if len(e.capturas) > 0:
                abort_json(403, _(u'La exploración no se puede descartar porque tiene imagenes asociadas.'))#IDIOMAOK

            # Comprobacion: medico en sesion sea medico de exploracion
            if e.medico_id != medico_conect.id:
                abort_json(403, _(u'La exploración no se puede descartar con este usuario.'))#IDIOMAOK

            # Realizar el borrado logico
            e.borrado_motivo = _("Descartar")#IDIOMAOK
            e.borrado = 1
            meta.Session.update(e)
            meta.Session.commit()

            # Graba en el registro
            registro.nuevo_registro(username, ip, e, registro.eventos.eliminar,
                                    registro.res.exploracion, 'DESCARTAR',
                                    "borrado=0", "borrado=1,motivo=" + e.borrado_motivo)

            # Liberar la cita
            cita = meta.Session.query(Cita).filter(Cita.exploracion_id == e.id)
            if cita.count():
                cita_liberar = cita.one()
                cita_liberar.exploracion_id = None
                meta.Session.update(cita_liberar)
                meta.Session.commit()

                registro.nuevo_registro(username, ip, e, registro.eventos.modificar,
                                        registro.res.cita, 'exploracion_id',
                                        str(e.id), None)


        elif e.estado == 1:
            # Finalizada


            # Comprobacion: permisos
            if not authorized(HasAuthKitRole(roles.borrado_logico)):
                abort_json(403, _(u'El usuario actual no tiene permisos para borrar la exploración'))#IDIOMAOK

            # Comprobacion: si ya esta borrada.
            if e.borrado == 1:
                abort_json(400, _(u'La exploración ya está borrada'))#IDIOMAOK

            # Comprobacion: tener motivo
            if not ('borrado_motivo' in request.params and request.params["borrado_motivo"].strip()!=""):
                abort_json(400, _(u'Es necesario un motivo para borrar la exploración'))#IDIOMAOK

            # Borrado logica de exploracion
            motivo = request.params["borrado_motivo"].strip()
            e.borrado_motivo = motivo
            e.borrado = 1
            meta.Session.update(e)
            meta.Session.commit()

            # Graba en el registro
            registro.nuevo_registro(username, ip, e, registro.eventos.eliminar,
                                    registro.res.exploracion, 'BORRADO',
                                    "borrado=0", "borrado=1,motivo=" + e.borrado_motivo)



        else:
            # Otro estado. No permite borrado.
            abort_json(403, _(u'No se permite borrar esta exploración'))#IDIOMAOK




    def _procesar_params_especiales(self,p):

        # filtrado por min. y max. fecha: se usan los parametros especiales fecha_max y fecha_min
        # me los guardo en variables y luego para no pasar parametros incorrectos a "_doIndex" los quito
        if 'fecha_min' in p:
            self.fecha_min = p['fecha_min']
            del p['fecha_min']
        else:
            self.fecha_min = None

        if 'fecha_max' in p:
            self.fecha_max = p['fecha_max']
            del p['fecha_max']
        else:
            self.fecha_max = None

        #filtrado servicio_activo
        if 'servicio_activo' in p:
            self.servicio_activo = p['servicio_activo']
            del p['servicio_activo']
        else:
            self.servicio_activo = None

        # filtrar por exploraciones almacenadas en el PACS
        # (que el registro vinculado en la tabla exploraciones_dicom tenga
        # el valor indicador en el campo "dicom_stored")
        if 'dicom_stored' in p:
            self.dicom_stored = p['dicom_stored']
            del p['dicom_stored']
            #print type(self.dicom_stored), self.dicom_stored
        else:
            self.dicom_stored = None

        # filtrado por datos de paciente (CIP/NUHSA, historia/NHC)
        for campo_paciente in ('CIP', 'idunico'):
            if campo_paciente in p:
                setattr(self, campo_paciente, p[campo_paciente])
                del p[campo_paciente]
            else:
                setattr(self, campo_paciente, None)

        # si se trata de una busqueda avanzada (puede ser un int que es el
        # id o todo el xml indicando la busqueda, para busquedas puntuales)
        if '_busqueda' in p:
            self.busqueda = p['_busqueda']
            del p['_busqueda']
        else:
            self.busqueda = None

        return p

    def _crear_parametros_medico(self,p,username):

        medico = medico_from_user(username)
        # SERVICIOS DEL MEDICO
        servicios_del_medico = []
        for rel in medico.servicios:
            servicios_del_medico.append(rel.servicio.id)
        self.servicios_del_medico = servicios_del_medico

        return p

# XXX es necesario quitar el param fecha en el Index para volverlo a poner en el _doIndex?
import time
from datetime import date, timedelta
import logging
import binascii
import json

from pylons.i18n import _
from sqlalchemy.sql import and_, or_
from authkit.authorize.pylons_adaptors import authorized, authorize, authorize_request, NotAuthorizedError
from authkit.permissions import RemoteUser, ValidAuthKitUser, UserIn, HasAuthKitRole, And
from xml.etree.ElementTree import Element, SubElement, tostring

from endosys.model import meta
import endosys.model as model
from endosys.model.citas_ex import get_cita_ex
from endosys.model.exploraciones import Exploracion
from endosys.lib.genericREST import *

from endosys.lib.usuarios.seguridad import roles
from endosys.lib.citas import nueva_cita, guardar_cita, from_params, get_hora_fin, CAMPOS_CITA_EX, set_cita
from endosys.lib.plugins.base import *
from endosys.config.plugins import pluginCitas
import paste.httpexceptions as httpexceptions
import endosys.lib.hl7_wrapper.sending as hl7_sending
import endosys.lib.misc
import endosys.model.agendas
from endosys.model import Configuracion
from endosys.lib.pydicom_wrapper.mwl import WorklistRequest
from endosys.lib.dicom.worklist.utils import convert_keys_str2hex
from endosys.lib.dicom.worklist.receiving import WorklistProcess

log = logging.getLogger(__name__)

class CitasController(GenericRESTController):

    def __init__(self, *args, **kwargs):
        GenericRESTController.__init__(self, *args, **kwargs)
        self.tabla = model.Cita
        self.nombre_recurso = 'cita'
        self.nombre_recursos = 'citas'
        self.campos_index = ('id', 'paciente', 'fecha', 'hora', 'duracion', 'agenda_id', 'agenda', 'prioridad', #'servicio',    #   QUITAR_CITA.SERVICIO_ID
            'sala', 'medico', 'tipoExploracion', "tipoExploracion_id", "prioridad_id", 'exploracion_id',
            'observaciones', 'ex', 'cancelada', 'medico_id', 'sala_id', 'aseguradora_id')
        #self.cita_updating = None

    def _return_doIndex(self, registros, data, format):
        """
        añade la hora_fin (tanto si hay pluginCitas como si no)
        """
        for cita in registros:

            a = filter(lambda i: str(i['id']) == str(cita.id), data)
            if len(a) > 0:
                cita_el = a[0]
                cita_el['hora_fin'] = formatea_valor(get_hora_fin(cita))

            if cita.exploracion:
                cita_el['exploracion'] = {'id': formatea_valor(cita.exploracion.id)}
                cita_el['exploracion']['estado'] = formatea_valor(cita.exploracion.estado)
                cita_el['exploracion']['borrado'] = formatea_valor(cita.exploracion.borrado)
                if cita.exploracion.medico:
                    cita_el['exploracion']['medico'] = {'id': formatea_valor(cita.exploracion.medico.id)}
                    cita_el['exploracion']['medico']['nombre'] = formatea_valor(cita.exploracion.medico.nombre)

            if cita.paciente:
                if cita.paciente.aseguradora_id:
                    cita_el["paciente"]["aseguradora"] = {'id': formatea_valor(cita.paciente.aseguradora.id) }
                    cita_el["paciente"]["aseguradora"]["nombre"] = formatea_valor(cita.paciente.aseguradora.nombre)

                cita_el["paciente"]["centros"] = []
                for centro in cita.paciente.centros:
                    cita_el["paciente"]['centros'].append({'id': formatea_valor(centro.centro_id), \
                                                            'nhc': formatea_valor(centro.nhc)})

            if cita.work:
                cita_el["work"] = {'accessionNumber': formatea_valor(cita.work.accessionNumber)}
                cita_el["work"]['studyInstanceUID'] = formatea_valor(cita.work.studyInstanceUID)
                cita_el["work"]['schProcStepLoc'] = formatea_valor(cita.work.schProcStepLoc)
                cita_el["work"]['schProcStepID'] = formatea_valor(cita.work.schProcStepID)
                cita_el["work"]['schProcStepDescription'] = formatea_valor(cita.work.schProcStepDescription)
                cita_el["work"]['reqProcedurePriority'] = formatea_valor(cita.work.reqProcedurePriority)
                cita_el["work"]['patientLocation'] = formatea_valor(cita.work.patientLocation)
                cita_el["work"]['admissionID'] = formatea_valor(cita.work.admissionID)
                cita_el["work"]['reqService'] = formatea_valor(cita.work.reqService)
                cita_el["work"]['refPhysicianName'] = formatea_valor(cita.work.refPhysicianName) 
                cita_el["work"]['reqPhysician'] = formatea_valor(cita.work.reqPhysician)
                cita_el["work"]['schStationName'] = formatea_valor(cita.work.schStationName) 
                cita_el["work"]['schPerfPhysicianName'] = formatea_valor(cita.work.schPerfPhysicianName)
                cita_el["work"]['schStationAETitle'] = formatea_valor(cita.work.schStationAETitle)

        return data

    def _doIndex(self, params, format='xml'):
        #   XXX     si no hay parametro "fecha" entonces NO usar el plugin de citas...
        if not pluginCitas or (not self.fecha):

            # NOTA: Copiado y adaptado desde rest/pacientes.py:PacientesController._doIndex()
			# Consultar el listado de citas mediante un mensaje HL7 (SQM^S25)
            if (config.get('HL7.CONSULTA_CITAS.ACTIVO', '0') == '1') and \
                hasattr(self, 'fecha') and hasattr(self, 'agenda_id') and \
                self.fecha != None and self.agenda_id != None:
                #consulta de citas via HL7
                agenda = endosys.lib.misc.registro_by_id(endosys.model.agendas.Agenda, self.agenda_id)
                t = time.strptime(self.fecha, "%d/%m/%Y")
                fecha = date(t.tm_year, t.tm_mon, t.tm_mday)
                citas = hl7_sending.consulta_citas(agenda.codigo, fecha)
                data = []
                for registro in citas:
                    o = {
                        'id': formatea_valor_json(registro.id),
                        'href': h.url_for('rest_' + self.nombre_recurso, id=registro.id, format=format)
                    }
                    for campo in self.tabla.__dict__:
                        # ...que esten en campos_index, excluyendo siempre el id
                        if not campo in self.campos_index: continue
                        if campo == 'id': continue
                        if isinstance(getattr(self.tabla, campo), InstrumentedAttribute):
                            self._anadir_campo_obj(o, registro, campo)
                    data.append(o)
                
                return GenericRESTController.respuesta_doIndex(self, citas, data, format)
            elif (config.get('WORKLIST.CONSULTA_CITAS.ACTIVO','0')=='1') and \
                hasattr(self, 'fecha') and hasattr(self, 'agenda_id') and \
                self.fecha != None and self.agenda_id != None:
                # consulta citas mediante Worklist - WIP

                # Niveles: 1: centro, 2: servicio, 3:agenda
                obj_nivel = {}
                obj_nivel['3'] = endosys.lib.misc.registro_by_id(endosys.model.agendas.Agenda, self.agenda_id)
                obj_nivel['2'] = obj_nivel['3'].servicio
                obj_nivel['1'] = obj_nivel['2'].centro

                current_conf = {'level': 0}

                # Leer configuraciones de worklist de la tabla configuraciones.
                confs_worklist = meta.Session.query(Configuracion).filter(Configuracion.clave=='worklist').one()
                if not confs_worklist:
                    abort_json(400, _(u'No hay configuraciones para obtener Worklist'))#IDIOMAOK
                
                worklist_dict = byteify(json.loads(confs_worklist.valor))
                for conf in worklist_dict["worklist"]:
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
                    abort_json(400, _(u'No existe ninguna lista de trabajo configurada para esta agenda'))#IDIOMAOK

                # convertir a hex los strings de los keys de los filtros
                current_conf = convert_keys_str2hex(current_conf)

                # a los filtros de current conf, le agrego el filtro 
                # de la fecha, que viene por parametro
                fecha_dicom = datetime.datetime.strptime(self.fecha, "%d/%m/%Y").strftime('%Y%m%d')
                filter_date = {"key": 0x00400002, "type": "DA", "value": fecha_dicom }
                for f in current_conf['filters']:
                    if f['key'] == 0x00400100:
                        # es el key del ScheduledSequence.
                        # dentro de los values de esta clave
                        # hay que meter la fecha
                        #pass
                        f['value'].append(filter_date)

                try:
                    worklist = WorklistRequest(current_conf)
                    citas_worklist = worklist.get_worklist()
                    for cita_worklist in citas_worklist:
                        print 'cita'
                        wlprocess = WorklistProcess(cita_worklist, current_conf)
                    return GenericRESTController._doIndex(self, params, format)
                except Exception,e:
                    abort_json(400, e.message)
            else:
                return GenericRESTController._doIndex(self, params, format)

        else:
            # añado el param fecha, que lo habia quitado en Index...
            params['fecha'] = self.fecha
            # se añade el medico actual, ya que desde el plugin no se tiene acceso al "request"
            params['__medico'] = medico_from_user(request.environ['REMOTE_USER'])
            # agenda
            params['agenda_id'] = self.agenda_id

            try:
                citas = pluginCitas.index(params)
            except E_NoEncontrado, e:
                log.error(e)
                abort_xml(404, _('No se ha encontrado ninguna cita'), 2)#IDIOMAOK
            except PluginException, e:
                log.error(e)
                abort_xml(e.http_status, str(e))
            except Exception, e:
                log.error(e)
                raise
##              abort_xml(500, 'Ha ocurrido un error cargando las citas (%s)' % e)

            # Si tiene activo el modo preprocess, lo que hace es ejecutar la funcionalidad del plugin,
            # que se supone que deja la tabla de citas de EndoSys en el estado correcto, y luego
            # continua con el funcionamiento normal del genericrest
            if pluginCitas.preprocess_mode:
                return GenericRESTController._doIndex(self, params, format)

            # si no se encuentra ningun registro, devolver error 404
            if len(citas) == 0: abort_xml(404, _('No se ha encontrado ninguna cita'), 2)#IDIOMAOK

            # #################################################################################
            # Ya no se usa .info.codigo_prestacion y .info.descripcion_prestacion para
            # mostrar la prestación que viene del worklist (schProcStepID y schProcStepDescription),
            # sino que se pone en .ex, asi queda igual que cuando viene de HL7, que se guarda
            # en la tabla citas_ex
            # #################################################################################

            data = self._crear_data(citas, format, valid_fields=self.campos_index)
            data = self._return_doIndex(citas, data, format)
            return self.respuesta_doIndex(citas, data, format)



    @authorize(RemoteUser())
    def index(self, paciente_id=None, format='xml'):
        p =         request.params
        username =  request.environ.get('REMOTE_USER', None)
        ipaddress = obtener_request_ip(request)

        # en el caso de que no sea "consultar_citas_todas", filtrar solo las del usuario actual
##      if not authorized( HasAuthKitRole(roles.consultar_citas_todas) ):
##          medico = medico_from_user(username)
##          p['medico_id'] = medico.id

        # controlar parametro 'agenda_id' (guardarlo en una varible y quitarlo de la lista de params),
        # y guardar info por defecto para el usuario y puesto
        import endosys.lib.organizacion_centros
        if 'agenda_id' in p:
            self.agenda_id = int(p['agenda_id'])
            del(p['agenda_id'])
        else:
            self.agenda_id = None
        endosys.lib.organizacion_centros.set_default(username, ipaddress, agenda = self.agenda_id)

        # controlar parametro 'semana'
        if 'semana' in p:
            self.semana = p['semana']
            del(p['semana'])
        else:
            self.semana = None

        # tambien controlar el parametro fecha, ya que ahora el _doIndex por defecto lo
        # trata todo como strings, y el formato de fecha es incorrecto
        if 'fecha' in p:
            self.fecha = p['fecha']
            del(p['fecha'])
        else:
            self.fecha = None

        # controlar el parametro id_unico_paciente, para filtrar por paciente
        if 'id_unico_paciente' in p:
            if config.get('CITAS_PENDIENTES_BUSQUEDA_POR_HISTORIA', 1):
                self.id_unico_paciente = p['id_unico_paciente']
                del(p['id_unico_paciente'])
            else: # si viene el parametro pero esta deshabilitada la busq por historia, no dejo que pase
                self.id_unico_paciente = None
                del(p['id_unico_paciente'])
        else:
            self.id_unico_paciente = None


        # controlar parametros de cita_ex
        self.ex = record()
        for c in CAMPOS_CITA_EX + ('estado',):
            if c in p:
                setattr(self.ex, c, p[c])
                del(p[c])

        # controlar parametro 'exploracion_estado'
        if 'exploracion_estado' in p:
            self.exploracion_estado = p['exploracion_estado']
            del(p['exploracion_estado'])
        else:
            self.exploracion_estado = None

        # cancelada: aunque es un campo normal de la tabla, se trata manualmente.
        self.cancelada = None
        if 'cancelada' in p:
            try:
                self.cancelada = int(p['cancelada'])
            except Exception as e:
                log.error(e)
            del(p['cancelada'])

        if paciente_id != None: p['paciente_id'] = paciente_id
        return self._doIndex(p, format)


    def _filtrar_index(self, query, format= None):
        # filtrar por agenda: si se ha indicado 'agenda_id' mostrar solo
        # las citas para esa agenda, pero ademas siempre se muestran las citas
        # que no tienen agenda asignada (null).
        if self.agenda_id != None:
            query = query.filter(or_( model.Cita.agenda_id == self.agenda_id, model.Cita.agenda_id == None ))

        # filtrar por fecha
        if self.fecha != None:
            t = time.strptime(self.fecha, "%d/%m/%Y")
            d = date(t.tm_year, t.tm_mon, t.tm_mday)
            query = query.filter( model.Cita.fecha == d )

        #  si no, filtrar por semana
        elif self.semana != None:
            t = time.strptime(self.semana, "%d/%m/%Y")
            d = date(t.tm_year, t.tm_mon, t.tm_mday)
            ini = d - timedelta(d.weekday())    # seleccionar el lunes de la semana correspondiente al dia indicado
            fin = ini + timedelta(6)              # el domingo
##  No hace falta pasarlos a str, el sqlalchemy ya trabaja con date
##          ini = ini.strftime("%d/%m/%Yx")
##          fin = fin.strftime("%d/%m/%Y")
            query = query.filter( and_(*[(model.Cita.fecha >= ini), (model.Cita.fecha <= fin)]) )

        #filtrar por historia o CIP
        if int(config.get('CITAS_PENDIENTES_BUSQUEDA_POR_HISTORIA', '1')): #solo si esta la clave activada, // 1 es el valor por defecto.
            if self.id_unico_paciente != None:
                if config.get('IDENTIFICADORES_PACIENTE', 'idunico').upper() == 'NHC' or \
                                config.get('IDENTIFICADORES_PACIENTE', 'idunico').upper() == 'NHC+IDUNICO':
                    campo_filtrar = 'NHC_CENTRO'
                else:
                    campo_filtrar = 'IDUNICO'
                if campo_filtrar == "IDUNICO":
                    paciente = meta.Session.query(model.Paciente).filter(
                        model.Paciente.idunico == self.id_unico_paciente)
                elif campo_filtrar == "NHC_CENTRO":
                    if self.agenda_id:
                        paciente = meta.Session.query(model.Paciente).filter(and_(
                            model.Paciente.id == model.Rel_Pacientes_Centros.paciente_id,
                            model.Rel_Pacientes_Centros.centro_id == model.Servicio.centro_id,
                            model.Servicio.id == model.Agenda.servicio_id,
                            model.Agenda.id == self.agenda_id,
                            model.Rel_Pacientes_Centros.nhc == self.id_unico_paciente
                        ))
                # Si hay pacientes entonces
                if paciente.count()>0:
                    paciente = paciente.one().id
                else:
                    paciente = None

                query = query.filter( model.Cita.paciente_id == paciente)


        # siempre, filtrar por el/los servicio/s del medico actual
        # XXX   con la gestion de centros y agendas ahora es distinto, el medico no tiene solo 1 servicio...
        # XXX   NO HACER ESTO! para la gestion de citas no se tiene que hacer... si es necesario que se envíe el param. "servicios" explicitamente
        # XXX   de momento se deja para que funcione Citas Pendientes, pero no sirve para Gestion Citas/Agendas
        medico = medico_from_user(request.environ['REMOTE_USER'])
##      if len(medico.servicios) > 0:
##          cond = [ (model.Cita.servicio_id == None) ]
##          for rel in medico.servicios:
##              cond.append( (model.Cita.servicio_id == rel.servicio_id) )
##          query = query.filter( or_(*cond) )
        #   QUITAR_CITA.SERVICIO_ID
        #   Ahora se filtra según las agendas del médico, buscando por la cita.agenda
        if len(medico.agendas) > 0:
            cond = [ (model.Cita.agenda_id == None) ]
            for rel in medico.agendas:
                cond.append( (model.Cita.agenda_id == rel.agenda_id) )
            query = query.filter( or_(*cond) )
        # #################

        # filtrar por "cancelada"
        #   Mostrar todas:              cancelada=None  (en BBDD, no aplicar filtro)
        #   Mostrar solo canceladas:    cancelada=True  (en BBDD, filtrar cancelada == 1)
        #   Mostrar solo NO canceladas: cancelada=False (en BBDD, filtrar cancelada != 1)
        if self.cancelada != None:
            if self.cancelada:
                query = query.filter(model.Cita.cancelada == True)
            else:
                query = query.filter( or_(*[(model.Cita.cancelada == False), (model.Cita.cancelada == None)]) )

        # filtrar por params de cita_ex (XXX de momento solo estado / resultado_enviado)
        if hasattr(self.ex, 'estado'):
            query = query.join(model.Cita.ex).filter(model.Cita_ex.estado == self.ex.estado)

        # filtrar por params de exploracion (estado)
        if self.exploracion_estado != None:
            query = query.join(model.Cita.exploracion).filter(model.Exploracion.estado == self.exploracion_estado)

        # orden
        query = query.order_by(model.Cita.fecha).order_by(model.Cita.hora)

        return query


    def _construir_plugin_xml_show(self, cita, root):
        # acceder directamente a los atributos de "cita", asi funciona tanto si es un registro de BBDD como un "Cita" de un plugin
        root.clear()

        root.attrib['id'] = formatea_valor( cita.id )

        SubElement(root, 'fecha').text = formatea_valor(cita.fecha)
        SubElement(root, 'hora').text = formatea_valor(cita.hora)
        SubElement(root, 'duracion').text = formatea_valor(cita.duracion)
        SubElement(root, 'observaciones').text = formatea_valor(cita.observaciones)
        #SubElement(root, 'prioridad').text = formatea_valor(cita.prioridad)

        SubElement(root, 'paciente_id').text = formatea_valor( cita.paciente.id )
        e = SubElement(root, 'paciente')
        e.attrib['id'] = formatea_valor( cita.paciente.id )
        SubElement(e, 'CIP').text = formatea_valor( cita.paciente.CIP )
        SubElement(e, 'nombre').text = formatea_valor( cita.paciente.nombre )
        SubElement(e, 'apellido1').text = formatea_valor( cita.paciente.apellido1 )
        SubElement(e, 'apellido2').text = formatea_valor( cita.paciente.apellido2 )

        if cita.tipoExploracion:
            SubElement(root, 'tipoExploracion_id').text = formatea_valor( cita.tipoExploracion.id )
            e = SubElement(root, 'tipoExploracion')
            e.attrib['id'] = formatea_valor( cita.tipoExploracion.id )
            SubElement(e, 'color').text = formatea_valor( cita.tipoExploracion.color )
            SubElement(e, 'nombre').text = formatea_valor( cita.tipoExploracion.nombre )

        if cita.sala:
            SubElement(root, 'sala_id').text = formatea_valor( cita.sala.id )
            e = SubElement(root, 'sala')
            e.attrib['id'] = formatea_valor( cita.sala.id )
            SubElement(e, 'nombre').text = formatea_valor( cita.sala.nombre )

        # xxx con la nueva gestion de agendas, ya no tendrá servicio directamente
        #   QUITAR_CITA.SERVICIO_ID
##      if cita.servicio:
##          SubElement(root, 'servicio_id').text = formatea_valor( cita.servicio.id )   # cita.servicio_id
##          e = SubElement(root, 'servicio')
##          e.attrib['id'] = formatea_valor( cita.servicio.id )
##          SubElement(e, 'nombre').text = formatea_valor( cita.servicio.nombre )

        if cita.agenda:
            SubElement(root, 'agenda_id').text = formatea_valor( cita.agenda.id )
            e = SubElement(root, 'agenda')
            e.attrib['id'] = formatea_valor( cita.agenda.id )
            SubElement(e, 'nombre').text = formatea_valor( cita.agenda.nombre )

        if cita.medico:
            SubElement(root, 'medico_id').text = formatea_valor( cita.medico.id )
            e = SubElement(root, 'medico')
            e.attrib['id'] = formatea_valor( cita.medico.id )
            SubElement(e, 'username').text = formatea_valor( cita.medico.username )
            SubElement(e, 'nombre').text = formatea_valor( cita.medico.nombre )

        if cita.exploracion:
            SubElement(root, 'exploracion_id').text = formatea_valor( cita.exploracion.id )
            e = SubElement(root, 'exploracion')
            e.attrib['id'] = formatea_valor( cita.exploracion.id )
            SubElement(e, 'estado').text = formatea_valor( cita.exploracion.estado ) # XXX y esto?
            SubElement(e, 'fecha').text = formatea_valor( cita.exploracion.fecha )
            SubElement(e, 'hora').text = formatea_valor( cita.exploracion.hora )
        else:
            SubElement(root, 'exploracion_id').text = ''

        if cita.prioridad:
            e = SubElement(root, 'prioridad')
            e.attrib['id'] = formatea_valor( cita.prioridad.id )
            SubElement(e, 'codigo').text = formatea_valor( cita.prioridad.codigo )
            SubElement(e, 'nombre').text = formatea_valor( cita.prioridad.nombre )
            SubElement(e, 'nivel').text = formatea_valor( cita.prioridad.nivel )

        if hasattr(cita, 'ex') and cita.ex:
            e = SubElement(root, 'ex')
            SubElement(e, 'id_ext_1').text = formatea_valor( cita.ex.id_ext_1 )
            SubElement(e, 'id_ext_2').text = formatea_valor( cita.ex.id_ext_2 )
            SubElement(e, 'id_ext_3').text = formatea_valor( cita.ex.id_ext_3 )
            SubElement(e, 'id_ext_4').text = formatea_valor( cita.ex.id_ext_4 )
            #SubElement(e, 'nhc').text = formatea_valor( cita.ex.nhc )
            SubElement(e, 'idunico').text = formatea_valor( cita.ex.idunico )
            SubElement(e, 'numero_cita').text = formatea_valor( cita.ex.numero_cita )
            SubElement(e, 'numero_episodio').text = formatea_valor( cita.ex.numero_episodio )
            SubElement(e, 'numero_peticion').text = formatea_valor( cita.ex.numero_peticion )
            SubElement(e, 'prestacion_cod').text = formatea_valor( cita.ex.prestacion_cod )
            SubElement(e, 'prestacion_descr').text = formatea_valor( cita.ex.prestacion_descr )
            SubElement(e, 'servicio_cod').text = formatea_valor( cita.ex.servicio_cod )
            SubElement(e, 'servicio_descr').text = formatea_valor( cita.ex.servicio_descr )
            SubElement(e, 'agenda_cod').text = formatea_valor( cita.ex.agenda_cod )
            SubElement(e, 'agenda_descr').text = formatea_valor( cita.ex.agenda_descr )
            SubElement(e, 'procedencia_cod').text = formatea_valor( cita.ex.procedencia_cod )
            SubElement(e, 'procedencia_descr').text = formatea_valor( cita.ex.procedencia_descr )
            SubElement(e, 'servicio_peticionario_cod').text = formatea_valor( cita.ex.servicio_peticionario_cod )
            SubElement(e, 'servicio_peticionario_descr').text = formatea_valor( cita.ex.servicio_peticionario_descr )
            SubElement(e, 'medico_peticionario_cod').text = formatea_valor( cita.ex.medico_peticionario_cod )
            SubElement(e, 'medico_peticionario_descr').text = formatea_valor( cita.ex.medico_peticionario_descr )
            SubElement(e, 'estado').text = formatea_valor( cita.ex.estado )

        if hasattr(cita, 'work') and cita.work:
            e = SubElement(root, 'work')
            SubElement(e, 'accessionNumber').text = formatea_valor( cita.work.accessionNumber )
            SubElement(e, 'patientID').text = formatea_valor( cita.work.patientID )
            SubElement(e, 'patientName').text = formatea_valor( cita.work.patientName )
            SubElement(e, 'patientBirthDate').text = formatea_valor( cita.work.patientBirthDate )
            SubElement(e, 'patientSex').text = formatea_valor( cita.work.patientSex )
            SubElement(e, 'scheduledProcedureStepStartDate').text = formatea_valor( cita.work.schProcStepStartDate )
            SubElement(e, 'scheduledProcedureStepStartTime').text = formatea_valor( cita.work.schProcStepStartTime )
            SubElement(e, 'studyInstanceUID').text = formatea_valor( cita.work.studyInstanceUID )

        # si la cita tiene info adicional, añadirla también
        if hasattr(cita, 'info'):
            if hasattr(getattr(cita, 'info'), '__dict__'):
                e = SubElement(root, 'info')
                for c, v in vars(getattr(cita, 'info')).iteritems():
                    if not(c.startswith('_')):
                        SubElement(e, c).text = formatea_valor( v )



    @authorize(RemoteUser())
    def show(self, id, format='xml'):
        # TODO  restringir solo a las citas propias aegun los permisos
        if not pluginCitas:
            return GenericRESTController.show(self, id, format)
        else:
            cita = pluginCitas.show(id)
##          try:
##              cita = pluginCitas.show(id)
##          except PluginException, e:
##              abort_xml(e.http_status, str(e))
##          except Exception, e:
##              abort_xml(500, 'Ha ocurrido un error cargando la cita (%s)' % e)

            # Convertir a formato compatible con GenericREST
            cita = self._crear_data(cita, format, valid_fields=self.campos_show)
            self._return_show(None, cita)
            return self.respuesta_show(None, cita, format)

    def _update_registro_from_params(self, cita, params, exclude = []):

        username = request.environ.get('REMOTE_USER', None)
        ipaddress = obtener_request_ip(request)

        if 'cancelada' in params:
            if not cita.exploracion_id:
                if cita.cancelada != True:
                #la cita no estaba cancelada, se puede cancelar

                    #codigo para modificar una cita
                    cita_old = {}
                    for campo in cita.c.keys():
                        cita_old[campo] = getattr(cita, campo)

                    cita_updating = record(**cita_old)


                    # extraer parametros
                    c = from_params(params)
                    # asignar los valores a la cita
                    try:
                        set_cita(cita, c)
                    except Exception as e:
                        log.error(e)
                        abort_xml(400, e.message, codigo=1000)

                    cita.cancelada = c.cancelada
                    cita.motivo_id = c.motivo_id

                    self._cancela_cita(cita, c.motivo_id)

                    guardar_cita(cita, username, ipaddress, cita_updating)


                else:
                #la cita YA esta cancelada
                    abort_xml(500, _('No se puede cancelar la cita, porque ya estaba cancelada'))#IDIOMAOK
            else:
                #la cita tiene una exploracion asociada, NO se puede cancelar
                abort_xml(500, _('No se puede cancelar la cita, porque tiene una exploración asociada'))#IDIOMAOK
            #codigo para cancelar una cita
            # cancelar cita: si "cancelada" pasa de FALSE a TRUE es que se está
            # cancelando


            #cancelada_anterior = cita.cancelada
            #cita.cancelada = c.cancelada
            #cita.motivo_id = c.motivo_id
            #if (cancelada_anterior != True) and (cita.cancelada):
                #self._cancela_cita(cita, c.motivo_id)


            # ##################################################

        else:
            #codigo para modificar una cita
            cita_old = {}
            for campo in cita.c.keys():
                cita_old[campo] = getattr(cita, campo)

            cita_updating = record(**cita_old)


            # extraer parametros
            c = from_params(params)
            # asignar los valores a la cita
            try:
                set_cita(cita, c)
            except Exception as e:
                log.error(e)
                abort_xml(400, e.message, codigo=1000)


            guardar_cita(cita, username, ipaddress, cita_updating)


    @authorize(HasAuthKitRole([roles.crear_modif_citas]))
    def update(self, id):
        # Si el pluginCitas tiene implementado un update (o sea, es distinto que el update del padre que solo hace un pass)
        # entonces ejecuta este update Y NADA MAS.
        # En caso contrario, hacer el update normal, que en caso de cancelacion puede ejecutar la funcion del plugin cancela_cita (desde _update_registro_from_params)
        from endosys.lib.plugins.base.citas import PluginCitas
        if pluginCitas and type(pluginCitas).update != PluginCitas.update:
            cita = pluginCitas.cita_from_params(request.params)
            pluginCitas.update(id, cita)
        else:
            return GenericRESTController.update(self, id) # ejecutar _update_registro_from_params


    def _doCreate(self, params, format='xml'):
        """
        Además de crear el registro Cita, también crea el registro Cita_ex
        """
        # extraer parametros
        c = from_params(params)

        username = request.environ.get('REMOTE_USER', None)
        ipaddress = obtener_request_ip(request)
        # crear cita
        cita = nueva_cita()

        # asignar los valores a la cita
        try:
            set_cita(cita, c)
        except Exception as e:
            log.error(e)
            raise # xxx
            abort_xml(400, e.message, codigo=1000)

        guardar_cita(cita, username, ipaddress)

        #   XXX copiado directamente de genericREST.py:_doCreate()... mejor refactorizar esto!
        #   devolver como xml o json
        data = { 'id': formatea_valor(cita.id) }
        data = self._return_doCreate(cita, data)
        response.status_code = 201
        if format == 'xml':
            response.content_type = "text/xml"
            return tostring(obj_to_xml(data, self.nombre_recurso))
        elif format == 'json':
            response.content_type = 'application/json'
            return simplejson.dumps(data)



    @authorize(HasAuthKitRole([roles.crear_modif_citas]))
    def create(self, format='xml'):
        if not pluginCitas:
            return GenericRESTController.create(self, format) # ejecutar doCreate
        else:
            try:
                cita = pluginCitas.cita_from_params(request.params)
                cita = pluginCitas.create(cita)
            except PluginException, e:
                log.error(e)
                abort_xml(e.http_status, str(e), codigo=e.endosys_errorcode)
            except Exception, e:
                log.error(e)
##              abort_xml(500, 'Ha ocurrido un error creando la cita (%s)' % e)
                raise e

            response.status_code = 201
            #   devolver como xml
            response.content_type = "text/xml"
            root = Element(self.nombre_recurso)
            root.attrib['id'] = formatea_valor(cita.id)
            return tostring(root)


    @authorize(HasAuthKitRole([roles.crear_modif_citas]))
    def delete(self, id):
        if not pluginCitas:
##          return GenericRESTController.delete(self, id)
            # si se pasa el parametro id_field, usar el campo indicado
            # como identificador. Sirve para eliminar utilizando otro
            # identificador, utilizado en integraciones desde Mirth
            # XXX revisar bien...
            if 'id_field' in request.params:
                cita_ex = get_cita_ex( **{request.params['id_field']: id} )
                if not cita_ex:
                    abort_xml(404, _('No se ha encontrado ninguna cita'), 2)#IDIOMAOK
                id = cita_ex.cita_id
            else:
                cita_ex = get_cita_ex( cita_id = id )

            # eliminar la peticion y la cita
            meta.Session.delete( cita_ex )
            meta.Session.delete( self._registro_by_id(id) )
            try:
                meta.Session.commit()
            except IntegrityError:
                log.error(e)
                abort_xml(403, _('No se puede eliminar la cita'))#IDIOMAOK
        else:
            try:
                pluginCitas.delete(id)
            except PluginException, e:
                log.error(e)
                abort_xml(e.http_status, str(e))
            except Exception, e:
                log.error(e)
                raise e


    def _cancela_cita(self, cita, motivo_id):
        # Si hay un plugin hacer algo adicional al cancelar la cita
        if pluginCitas:
##          medico = medico_from_user(request.environ['REMOTE_USER'])
            pluginCitas.cancela_cita(cita.id, motivo_id)

        # enviar a Mirth el mensaje ORR, si está configurado asi
        if config.get('ENVIAR_CAPTURA_ACTIVIDAD.ACTIVO', '0') == '1':
            import endosys.lib.hl7_wrapper.sending
            endosys.lib.hl7_wrapper.sending.enviar_captura_actividad(cita, False, motivo_id)

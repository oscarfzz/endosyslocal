import logging
log = logging.getLogger(__name__)

from pylons.i18n import _
from sqlalchemy.sql import or_

from endosys.model import meta
from endosys.model import Work, Paciente, Cita, Exploracion
from endosys.lib.citas import from_params, set_cita
from endosys.lib.dicom.util import DICOM_to_datetime, DICOM_to_date
from endosys.lib.dicom.worklist.utils import get_value_from_ds
from endosys.config.plugins import _import

class WorklistProcess:

    raw = None
    db_work = None
    db_cita = None
    db_paciente = None

    # Es la configuración que se almaceno 
    # en la tabla Configuraciones para este worklist
    conf = None
    
    # Si tiene_cita = True entonces el worklist con ese
    # AccessionNumber ya tiene una cita asignada
    tiene_cita = False 

    # Si tiene_expl = True entonces el worklist con ese
    # AccessionNumber ya tiene una expl. realizada
    tiene_expl = False 

    # usar paciente existente, no lo crea, sino que lo 
    # encuentra en la base de datos por su identificador.
    se_uso_paciente_existente = False

    plugin_module = None

    def __init__(self, cita_worklist, conf=None):
        """ 
        - cita_worklist: es el DataSet de pydicom con la info
        - conf: es la configuración que se almaceno 
          en la tabla Configuraciones para este worklist
        """
        self.raw = cita_worklist
        self.conf = conf
        
        try:
            # intenta cargar la libreria donde estan los plugins
            if 'plugins' in conf:
                plugins_module_name = 'custom.plugins'
                self.plugins_module = _import(plugins_module_name)
        except Exception, e:
            msg = _(u'No se pudieron cargar los plugins del worklist')
            log.error(msg)
            log.error(e.message)
            raise Exception(msg)

        self.process_cita() 

    def process_cita(self):
        """ procesa la cita y la graba en la base de datos
            Tabla: worklist
        """
        w_existe = meta.Session.query(Work).filter(Work.accessionNumber == self.raw.AccessionNumber)
        # tabla: Worklist
        if not w_existe.count():
            #crear
            self.create_work()
            self.create_cita()
        else:
            # actualizar
            self.update_work(w_existe.one())

            if self.tiene_expl:
                # tiene exploracion, por lo tanto 
                # no se hace nada.
                return False

            if self.tiene_cita:
                # quiere decir que el worklist a 
                # actualizar tiene una cita asociada, 
                # ahora hay que ver si esa cita queda o se va

                self.asignar_agenda()
                if not self.db_cita.agenda_id:
                    # si se hace un cambio el work que 
                    # desencadena que se quede sin cita
                    # entonces se tiene que eliminar la cita
                    self.eliminar_cita()
                    return False

                # se actualiza la cita, porque ha encontrado 
                # una agenda para ella
                self.update_cita()
            else:
                # si no tiene una cita asociada entonces la crea
                self.create_cita()

    def eliminar_cita(self):
        self.db_work.cita_id = None
        meta.Session.update(self.db_work)
        meta.Session.delete(self.db_cita)
        meta.Session.commit()

    def create_work(self):
        self.asignar_campos_worklist(crear=True)
        meta.Session.save(self.db_work)
        meta.Session.commit()

    def update_work(self, db_work):
        self.db_work = db_work
        self.asignar_campos_worklist()
        meta.Session.update(self.db_work)
        meta.Session.commit()

        # para hacer controles en caso de que
        # venga una actualizacion futura de la cita
        if self.db_work.cita_id:
            self.tiene_cita = True
            self.db_cita = self.db_work.cita

            if self.db_work.cita.exploracion_id:
                self.tiene_expl = True

    def asignar_campos_worklist(self, crear=False):
        
        if crear:
            self.db_work = Work()
            self.db_work.accessionNumber = self.raw.AccessionNumber

        scheduledSequence = self.raw.ScheduledProcedureStepSequence[0]

        self.db_work.patientSex = get_value_from_ds(self.raw,'PatientSex') 
        self.db_work.studyInstanceUID = get_value_from_ds(self.raw,'StudyInstanceUID')
        self.db_work.refPhysicianName = get_value_from_ds(self.raw,'ReferringPhysicianName')
        self.db_work.placerOrderNumber = get_value_from_ds(self.raw,'PlacerOrderNumber')
        self.db_work.admissionID = get_value_from_ds(self.raw,'AdmissionID')
        self.db_work.admDiagnosisDesc = get_value_from_ds(self.raw,'AdmittingDiagnosisDescription')

        self.db_work.patientWeight = get_value_from_ds(self.raw,'PatientWeight')
        self.db_work.patientLocation = get_value_from_ds(self.raw,'PatientLocation')
        self.db_work.patientID = self.raw.PatientID
        self.db_work.patientName = get_value_from_ds(self.raw,'PatientName')
        self.db_work.patientBirthDate = get_value_from_ds(self.raw,'PatientBirthDate')

        self.db_work.schStationAETitle = get_value_from_ds(scheduledSequence,'ScheduledStationAETitle')
        self.db_work.schProcStepDescription = get_value_from_ds(scheduledSequence,'ScheduledProcedureStepDescription')
        self.db_work.schProcStepID = get_value_from_ds(scheduledSequence,'ScheduledProcedureStepID')
        self.db_work.schProcStepLoc = get_value_from_ds(scheduledSequence,'ScheduledProcedureStepLocation')
        self.db_work.schStationName = get_value_from_ds(scheduledSequence,'ScheduledStationName')
        self.db_work.schPerfPhysicianName = get_value_from_ds(scheduledSequence,'ScheduledPerformingPhysicianName')
        self.db_work.schProcStepStartDate = get_value_from_ds(scheduledSequence,'ScheduledProcedureStepStartDate')
        self.db_work.schProcStepStartTime = get_value_from_ds(scheduledSequence,'ScheduledProcedureStepStartTime')
        self.db_work.modality = get_value_from_ds(scheduledSequence,'Modality')

        self.db_work.reqPhysician = get_value_from_ds(self.raw,'RequestingPhysician')
        self.db_work.reqService = get_value_from_ds(self.raw,'RequestingService')
        self.db_work.reqProcedureDesc = get_value_from_ds(self.raw,'RequestingProcedureDescription')
        self.db_work.reqProcedureID = get_value_from_ds(self.raw,'RequestingProcedureID')
        self.db_work.reqProcedurePriority = get_value_from_ds(self.raw,'RequestingProcedurePriority')

    def create_cita(self):
        # primero hay que obtener o crear el paciente
        self.procesar_paciente()        
        self.asignar_campos_cita(crear=True)
        self.asignar_agenda()

        if not self.db_cita.agenda_id:
            # si no se le encuentra una agenda asociada 
            # entonces la cita no se graba, y el paciente
            # si solo se creo para esta cita entonces tambien
            # tiene que eliminarse
            if not self.se_uso_paciente_existente:
                # lo tiene que eliminar. Por las dudas, 
                # checkeo que no tenga exploraciones,
                # ni otras citas
                pac_tiene_expl = meta.Session.query(Exploracion) \
                    .filter(Exploracion.paciente_id==self.db_paciente.id)
                
                pac_tiene_citas = meta.Session.query(Cita) \
                    .filter(Cita.paciente_id==self.db_paciente.id)
                
                if not pac_tiene_citas.count() and \
                   not pac_tiene_expl.count():
                   meta.Session.delete(self.db_paciente)
                   meta.Session.commit()

            return False

        # si llega aca es pq esa cita tiene una agenda
        # asignada y se puede crear la cita
        self.db_cita.paciente_id = self.db_paciente.id
        meta.Session.save(self.db_cita)
        meta.Session.commit()

        self.db_work.cita_id = self.db_cita.id
        meta.Session.update(self.db_work)
        meta.Session.commit()

    def update_cita(self):
        # paciente original de la cita, puede cambiarse si
        # viene otro id de paciente distinto
        db_paciente = self.db_cita.paciente
        cambiar_paciente = False
        
        # compara el paciente originar qe estaba
        # guardado en la cita relacionada con el 
        # worklist contra el id del paciente que 
        # recien llego desde el worklist. Esto se hace
        # para saber si es necesario cambiar el paciente
        if db_paciente.idunico != self.get_idpaciente():
            # si no son iguales entonces hay que cambiar el
            # paciente_id de la cita
            cambiar_paciente = True

        self.procesar_paciente()

        # una vez resuelto el paciente puedo actualizar la cita
        self.asignar_campos_cita()

        if cambiar_paciente:
            # cambia el paciente, porque es otro
            cita.paciente_id = self.db_paciente.id

        meta.Session.update(self.db_cita)
        meta.Session.commit()

    def asignar_campos_cita(self, crear=False):
        
        if crear:
            self.db_cita = Cita()

        # asignacion de campos
        cita_record = from_params(self.create_params_cita_from_worklist())

        try:
            set_cita(self.db_cita, cita_record)
        except Exception, e:
            log.error(e)
        
    def asignar_agenda(self):
        # buscar a agenda destino
        agenda_id = None
        if not 'destinations' in self.conf:
            raise Exception("MWL: Falta configurar el destino de la cita ('destination')")

        if self.conf['level'] == 3:
            # cuando level=3 no hace falta mirar el source para asignar la agenda
            agenda_id = self.conf['destinations'][0]['target']
            if agenda_id != self.conf['level_id']:
                raise Exception("MWL: destination>target y level_id tienen que ser iguales")
        else:
            # la decision de a que agenda va tiene 
            # que estar dada por los parametros del destination>source
            for dest in self.conf['destinations']:
                if agenda_id:
                    # si ya esta asignada, no evalua las proximas 
                    # configuraciones
                    continue

                try:
                    source = dest['source']
                    if source['inside_scheduled_secuence']:
                        # si esta dentro de scheduled
                        # entonces es necesario obtener ese DS
                        scheduledSequence = self.raw.ScheduledProcedureStepSequence[0]
                        valor = get_value_from_ds(scheduledSequence, source['key'])
                        if valor in source['values']:
                            # el valor del worklist se corresponde 
                            # con el valor de este mapeo.
                            agenda_id = int(dest['target'])
                except Exception, e:
                    raise Exception('MWL: Erronea configuracion de "destinations" (%s)' % str(e))

        # si encuentra una agenda quedara con el id
        # sino quedará con el None
        self.db_cita.agenda_id = agenda_id

    def create_params_cita_from_worklist(self, agenda_id=None):
        """ crea un diccionario que simula ser params de un request
            esto permite usar la funcion from_params
        """
        params = {}
        params['fecha'] = DICOM_to_date(self.db_work.schProcStepStartDate).strftime('%d/%m/%Y')
        params['hora'] = DICOM_to_datetime(self.db_work.schProcStepStartDate,\
                                           self.db_work.schProcStepStartTime) \
                                           .strftime('%H:%M')
        params['paciente_id'] = self.db_paciente.id
        return params

    def get_idpaciente(self):
        """ Obtiene el id del paciente,
            Este id puede ser directamente el PatientID del MWL
            o puede ser un procesamiento de alguna campo del MWL
            mediante un plugin
        """
        if "plugins" in self.conf and 'get_idpaciente' in self.conf["plugins"]:
            # - El id del paciente se obtiene por un plugin ya que no
            #   se puede extraer del PatientID o necesita un procesamiento
            #   especial
            try:
                nombre_funcion = self.conf['plugins']['get_idpaciente']
                plugin_get_idpaciente = getattr(self.plugins_module, nombre_funcion, None)
                idpaciente = plugin_get_idpaciente(self.raw)
            except Exception,e:
                msg = _('Ocurrio un error con el plugin de get_idpaciente')
                log.error(msg)
                log.error(e.message)
                raise Exception(msg)
        else:            
            idpaciente = str(self.raw.PatientID.strip())

        return idpaciente

    def get_paciente(self):

        idpaciente = self.get_idpaciente()

        # Solamente se usa el idunico con worklist. No esta implementado
        # para trabajar con idunico + nhc por centro
        p_existe = meta.Session.query(Paciente) \
                    .filter(Paciente.idunico==idpaciente) \
                    .filter(or_(Paciente.deshabilitado==False, \
                                Paciente.deshabilitado==None))
        if p_existe.count()>0:
            return p_existe.first()
        else:
            return None

    def procesar_paciente(self):
        p_existe = self.get_paciente()
        if p_existe:
            # se actualizan los datos del paciente
            self.db_paciente = p_existe
            self.update_paciente()
            self.se_uso_paciente_existente = True
        else:
            self.create_paciente()

    def update_paciente(self):
        self.asignar_campos_paciente()
        meta.Session.update(self.db_paciente)
        meta.Session.commit()

    def create_paciente(self):
        self.asignar_campos_paciente(crear=True)
        meta.Session.save(self.db_paciente)
        meta.Session.commit()
        
    def asignar_campos_paciente(self, crear=False):
        # TODO: permitir plugin para configurar el parseo
        #       de otra forma
        if crear:
            self.db_paciente = Paciente()
            self.db_paciente.idunico = self.get_idpaciente() 
        
        # Nombres
        nombre = ''
        apellido1 = ''
        apellido2 = ''
        if "plugins" in self.conf and 'parse_nombres' in self.conf["plugins"]:
            try:
                nombre_funcion = self.conf['plugins']['parse_nombres']
                plugin_parse_nombres = getattr(self.plugins_module, nombre_funcion, None)
                nombre, apellido1, apellido2 = plugin_parse_nombres(self.raw)
            except Exception,e:
                msg = _('Ocurrio un error con el plugin de parse_nombres')
                log.error(msg)
                log.error(e.message)
                raise Exception(msg)
        else:
            try:
                nombres = self.db_work.patientName.split('^')
                nombre = nombres[0]
                apellido1 = nombres[1]
                apellido2 = ''
            except:
                nombre = self.db_work.patientName

        self.db_paciente.nombre = nombre
        self.db_paciente.apellido1 = apellido1
        self.db_paciente.apellido2 = apellido2         

        # Sexo
        if "plugins" in self.conf and 'parse_sexo' in self.conf["plugins"]:
            self.db_paciente.sexo = None
            try:
                nombre_funcion = self.conf['plugins']['parse_sexo']
                plugin_parse_sexo = getattr(self.plugins_module, nombre_funcion, None)
                self.db_paciente.sexo = plugin_parse_sexo(self.raw)
            except Exception,e:
                msg = _('Ocurrio un error con el plugin de parse_sexo')
                log.error(msg)
                log.error(e.message)
                raise Exception(msg)
        else:
            if self.db_work.patientSex.strip() == 'M':
                self.db_paciente.sexo = 1
            else:
                self.db_paciente.sexo = 0
        
        self.db_paciente.fechaNacimiento = DICOM_to_date(self.db_work.patientBirthDate)
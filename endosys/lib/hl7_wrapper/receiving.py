from pylons.i18n import _
from xml.etree.ElementTree import Element, SubElement, tostring, XML
import logging
import hl7
import datetime
import endosys.lib.pacientes
import endosys.lib.citas
from endosys.model import meta
import endosys.model.prioridades
from endosys.model.motivosCancelacion import MotivoCancelacion
from endosys.lib.fusiones import FusionarPacientes, FusionarPacientesM2
from endosys.model.servicios import get_servicio_id, get_servicio_y_agenda_id
from endosys.model.agendas import get_agenda_id, get_agenda
from endosys.model.campos import Campo
from endosys.model.valores import ValorSelec
from endosys.lib.misc import *
from sqlalchemy.sql import and_, or_
from endosys.config.plugins import pluginHL7
from endosys.lib.informes import get_pdf
from base64 import b64encode
from endosys.lib.hl7_wrapper.log import nuevo_log_HL7
import endosys.lib.hl7_wrapper
import endosys.lib.registro as registro
from endosys.model.provincias import provincia_nombre_by_codigo
from endosys.model.poblaciones import poblacion_nombre_by_codigo
from endosys.model.pacientes import Rel_Pacientes_Centros
from endosys.model.centros import get_centro_id

log = logging.getLogger(__name__)

class Hl7Process:

    """
    (el modulo se iba a llamar "hl7" pero da problemas con la lib python-hl7, por
    lo tanto se llama "hl7_process")

    Integración actual usando Mirth Connect:

        LEER_TCP
            llp listener, reenvía a Adaptador

        ADAPTADOR
            transforma el mensaje y reenvía a Procesar Mensaje

        PROCESAR MENSAJE
            Distribuidor. Filtro por tipo de mensaje y reenvía a ModificarPaciente,
            FusionarPaciente o GestionarCitas. Finalmente también reenvía a Procesar_ack

        MODIFICARPACIENTE
            Obtiene config de conexión a EndoSys Web
            Se autentifica (CONEXION HTTP)
            Obtiene el paciente por NHC (CONEXION HTTP)
            Comprueba si ya existe
            si no existe
                Crea uno nuevo (CONEXION HTTP)
                obtiene el nuevo id
            si ya existía
                Modifica el existente (CONEXION HTTP)
            Si va todo bien devuelve el id del paciente

        GESTIONARCITAS
            reenvía a ModificarPaciente
            filtra por tipo de ORM y reenvía a Nueva Cita o Eliminar Cita.

        NUEVA CITA
            Obtiene config de conexión a EndoSys Web
            Se autentifica (CONEXION HTTP)
            Crea una nueva cita (CONEXION HTTP)

        ELIMINAR CITA
            Obtiene config de conexión a EndoSys Web
            Se autentifica (CONEXION HTTP)
            Elimina una cita por ORDERID (CONEXION HTTP)

        PROCESAR_ACK
            genera un ACK y lo devuelve


    NUEVA INTEGRACIÓN:
        Mantener la comunicación, filtrado y transformación en Mirth Connect, y
        hacer el procesado de los mensajes en EndoSys Web.

        SE MANTIENEN:
            LEER_TCP
            ADAPTADOR

        GESTIONA ENDOSYS WEB:
            PROCESAR MENSAJE
            MODIFICARPACIENTE
            GESTIONARCITAS
                NUEVA CITA
                ELIMINAR CITA

    VARIOS: XXX
    ·   Para evitar confusiones con los conceptos de petición, cita, etc... de HL7
        con el concepto de Cita de EndoSys, se tendría que renombrar este concepto
        en EndoSys. Propuestas: "Programación", "Lista de trabajo"...

    ·   Debido a que ahora se guardan los segmentos completos (PV1, OBR y ORC) de las
        peticiones en CITAS_EX, se tiene que permitir acceder a campos concretos
        (p.ej. PV1.19) para mostrar en el informe, o incluso para utilizar en
        búsquedas avanzadas.
        (aun se guardan algunos valores clave directamente en columnas de CITAS_EX)

    ·   Falta revisar en todas las funciones "asignar_campos" que se usen endosys.lib.hl7_wrapper.hl7absent()
        y hl7val()

    ·   De momento, a las citas creadas por mensajes HL7 ORM o SIU siempre se les
        asigna una sola agenda relacionada con el servicio correspondiente, como si
        la relación servicio:agenda fuera 1:1.
        Por lo tanto, en integraciones se requiere que cada servicio tenga una
        agenda.

    """
    # FUNCIONES VARIAS hl7
    # ==============================================================================
    VALID_MESSAGES = {  'ADT': ('A04', 'A08', 'A18', 'A34', 'A28', 'A31', 'A40', 'A47'),
                        'SIU': ('S12', 'S13', 'S14', 'S15'),
                        'ORM': ('O01'),
                        'RSP': ('K22'),
                        'SQR': ('S25')
                     }
    #   TIPOS DE MENSAJE
    #      ADT   Admit Discharge Transfer
    #       SIU     Scheduling Information Unsolicited
    #      ORM   Order Message

    #   EVENTOS (extraido de corepointhealth.com e interfaceware.com)
    #   ADT:
    #       ADT-A01 – patient admit
    #       ADT-A02 – patient transfer
    #       ADT-A03 – patient discharge
    #       ADT-A04 – patient registration        <--- Nuevo Paciente
    #       ADT-A05 – patient pre-admission
    #       ADT-A08 – patient information update    <--- Modificar Paciente
    #       ADT-A11 – cancel patient admit
    #       ADT-A12 – cancel patient transfer
    #       ADT-A13 – cancel patient discharge
    #   SIU:
    #       SIU-S12 – Notification of new appointment booking      <--- Nueva Cita
    #       SIU-S13 – Notification of appointment rescheduling    <--- Modificar Cita (reprogramación)
    #       SIU-S14 – Notification of appointment modification    <--- Modificar Cita
    #       SIU-S15 – Notification of appointment cancellation    <--- Eliminar Cita
    #       SIU-S16 – Notification of appointment discontinuation   <--- Eliminar Cita¿?
    #       SIU-S17 – Notification of appointment deletion      <--- Eliminar Cita¿?
    #       SIU-S18 – Notification of addition of service/resource on appointment
    #       SIU-S19 – Notification of modification of service/resource on appointment
    #       SIU-S20 – Notification of cancellation of service/resource on appointment
    #       SIU-S21 – Notification of discontinuation of service/resource on appointment
    #       SIU-S22 – Notification of deletion of service/resource on appointment
    #       SIU-S23 – Notification of blocked schedule time slot(s)
    #       SIU-S24 – Notification of opened ("un-blocked") schedule time slot(s)
    #       SIU-S26 – Notification that patient did not show up for scheduled appointment
    #   ORM:
    #       ORM-O01 – Order message     <--- Nueva Cita, Eliminar Cita
    #   ADR:
    #       ADR-A19 – Patient Query - Response

    #   TIPOS DE MENSAJE
    #      ADT   Admit Discharge Transfer
    #       SIU     Scheduling Information Unsolicited
    #      ORM   Order Message

    #   EVENTOS (extraido de manual drago)
    #   ADT:
    #       ADT-A28 – Creacion de historia clinica      <--- Nuevo Paciente
    #       ADT-A31 – Actualización de datos demograficos   <--- Modificar Paciente
    #       ADT-A34 – fusion de historicos        <--- fusionar Paciente
    #       ADT-A40 – cambio de numero de historia


    #   SEGMENTOS                                               ADT SIU ORM
    #      PID   Patient Identification Definition              X   X   X
    #      ORC   Common Order                                           X
    #      OBR   Observation Request                                    X
    #      PV1   Patient Visit                                      X   X
    #      TQ1   Timing/Quantity                                    X
    #      AIS   Appointment Information                            X
    #      SCH   Scheduling Activity Information                    X


    #   INFORMACIÓN DE VARIOS CAMPOS (extraida de Mirth, con comentarios de distintas fuentes)
    #
    #   OBR     Observation Request
    #   OBR.16      Ordering Provider           DOC DRAGO: Doctor Responsable de la petición.   INFO CANDELARIA: (nada)  ENDOBASE: GetReferringDoctorByReportKey DOCTOR_NO, solo en ORUs
    #   OBR.16.1        ID Number
    #   OBR.16.2        Family Name
    #   OBR.16.3        Given Name
    #   OBR.16.4        Middle or initial Name
    #
    #   ORC  Common Order
    #   ORC.16      Order Control Code Reason   DOC DRAGO: Motivo creación o cancelación de la petición. Normalmente va el diagnóstico de sospecha. INFO CANDELARIA: (nada)  ENDOBASE: Indication
    #   ORC.16.1        Identifier              DOC DRAGO: codigo
    #   ORC.16.2        Text                    DOC DRAGO: texto
    #   ORC.19      Action By               DOC DRAGO: Persona que solicita la petición o cancelación.  INFO CANDELARIA: Médico peticionario
    #   ORC.19.1        ID Number              DOC DRAGO: codigo
    #   ORC.19.2        Family Name          DOC DRAGO: apellido
    #   ORC.19.3        Given Name            DOC DRAGO: nombre
    #   ORC.19.4        Middle or initial Name      INFO CANDELARIA: apellido 2
    #
    #   PV1  Patient Visit
    #   PV1.7     Attending Doctor      DOC DRAGO: Doctor responsable del acto clínico.     INFO CANDELARIA: (nada) ENDOBASE: Doctor (solo para mensajes ADR)
    #   PV1.7.1     ID Number              DOC DRAGO: id
    #   PV1.7.2     Family Name          DOC DRAGO: apellido 1
    #   PV1.7.3     Given Name            DOC DRAGO: apellido 2 (no sería nombre?)
    #   PV1.7.4     Middle or initial Name  DOC DRAGO: nombre (no sería apellido 2?)
    #   PV1.8     Referring Doctor      DOC DRAGO: Doctor de referencia     INFO CANDELARIA: (nada) ENDOBASE: ReferredBy (ORM, SIU, ADR)
    #   PV1.8.1     ID Number                                                                   ENDOBASE: DOCTOR_NO
    #   PV1.8.2     Family Name                                                                 ENDOBASE: LAST NAME
    #   PV1.8.3     Given Name                                                                  ENDOBASE: FIRST NAME
    #   PV1.10    Hospital Service  DOC DRAGO: Servicio del Hospital    INFO CANDELARIA: Servicio peticionario  ENDOBASE: (nada)
    #   PV1.10.1        Value
    #   PV1.19      Visit Number        DOC DRAGO: ver debajo (llega hasta el PV1.19.9) INFO CANDELARIA: (nada?)    ENDOBASE: ver debajo
    #   PV1.19.1        ID            DOC DRAGO: Acto clinico                                                   ENDOBASE: Admission Nº
    #   PV1.19.2        Check Digit  DOC DRAGO: (nada)
    #   PV1.19.3        Code...      DOC DRAGO: (nada)
    #   PV1.19.4        Assigning authority DOC DRAGO: Centro
    #   PV1.19.5        Identifier Type Code    DOC DRAGO: id externo acto clínico
    #   PV1.19.6        Assigning facility  DOC DRAGO: id creador acto clínico
    #
    #   NTE     Notes and Comments
    #   NTE.3       Comment
    #   NTE.3.1      Value
    #
    #

    #   SCH.26.1    Placer order number (indica el número de petición asociada a una cita, en un SIU)
    def __init__(self, msg):
        log.info('nuevo mensaje hl7: %s', msg)
        self.id_hl7_log = None
        self.repetition_separator = '~'
        self.ipaddress = None

        self.msg_original = unicode(msg, 'utf-8') # el mensaje viene codificado en UTF8 desde Mirth
        self.msg = hl7.parse(self.msg_original)
        self.msh = self.msg.segment('MSH')

        # extraer el separador de repeticiones del MSH (normalmente "~")
        self.repetition_separator = self.msg.segment('MSH').get(1.2)[0]

        self.message_type = self.msh.get(8.1).upper()   #   ADT, SIU, etc...
        self.trigger_event = self.msh.get(8.2).upper()  #   A04, S12, etc...

        self.paciente_updating = None

    def procesar_mensaje(self):
        """
        Procesar un mensaje HL7. Mensajes que reconoce:
            ADT - A04   Nuevo paciente (DECIDIR SI SE PROCESA A PARTE O MIRTH LO ENVÍA COMO UN A08)
            ADT - A08   Modificar paciente
            ADT - A18   Fusionar pacientes
            ADT - A34   Fusionar pacientes (por NHC) (CONFIRMAR SI ES A34 Y SI PUEDEN HABER MAS)
            ORM - O01   Nueva cita (petición) o cancelación
            SIU - S12   Nueva cita
            SIU - S13   modificar cita
            SIU - S14   modificar cita (información administrativa, NO hora, prestación, etc...)
            SIU - S15   cancelar cita

        NO  msg es el mensaje HL7 en formato text/xml
        msg es el mensaje HL7 en formato text/plain (pipe)
        """
        #log.info('recibido mensaje HL7: %s' % msg)
        log.info('Procesando mensaje hl7')

        #   si es un tipo de mensaje correcto, llama a la funcion procesar_AAA_BBB(), donde
        #   AAA_BBB es el tipo de mensaje
        if self.message_type in self.VALID_MESSAGES and self.trigger_event in self.VALID_MESSAGES[self.message_type]:
            #temp ruben
            self.id_hl7_log = nuevo_log_HL7(self)
            return eval('self.procesar_%s_%s' % (self.message_type, self.trigger_event))()

        else:
            raise Exception('Mensaje HL7 desconocido: %s %s' % (self.message_type, self.trigger_event))


    def _patient_identifier_list(self, segmento, num_campo):
        """
        ************************************************************************
        DEPRECATED: usar get_patient_identifier_list()
        ************************************************************************
        
        El identifier list (PID.3 o MRG.1) es de tipo repetitivo, por lo que pueden haber
        varios campos. Como esto no lo implementa la liberia de python-hl7, se
        hace este "apaño" para reconstruir el campo y volverlo a parsear.

        segmento:   debe ser el pid o el mrg
        num_campo:  normalmente será 3 para pid, y 1 para mrg
        """


        #   extraer el separador de campos del mismo PID.3 / MRG.1
        field_separator = segmento[num_campo].separator

        #   reconstruir los campos PID.3 / MRG.1
    ##  pidlist = '^'.join(segmento[num_campo])
        pidlist = unicode(segmento[num_campo]) # el objeto hl7.Field ya tiene la funcion _unicode() que lo vuelve a reconstruir

        #   y separar las repeticiones en un list
        pidlist = pidlist.split(self.repetition_separator)

        # hemos determinado que Mirth siempre va a enviarlos en este orden:
        #   1º - CIP
        #   2º - DNI
        #   3º - PI (historia)
        #   4º - SS

        identificadores = {
            'JHN': None, # cip
            'NNESP': None, # dni
            'PI': [], #nhc's
            'SS': None, #ss
            'PN': None #id unico
        }


        for pl1 in pidlist:
            #print(pl1, len(pl1))
            identificador = hl7.Field(field_separator, pl1.split(field_separator))[4]
            if identificador != 'PI':
                identificadores[identificador] = hl7.Field(field_separator, pl1.split(field_separator))[0]
            else:
                #IMPORTANTE - EN ESTE PUNTO SE DEVERÍA CONTRASTAR SI VIENE VACIO EL CÓDIGO DEL CENTRO O EL NHC omitirlo
                nhc_centro = {
                    'nhc': hl7.Field(field_separator, pl1.split(field_separator))[0],
                    'codigo_centro': hl7.Field(field_separator, pl1.split(field_separator))[3]
                }

                identificadores['PI'].append(nhc_centro)

               # identificadores['PI'][0]['numero']

            '''
            if identificador == 'JHN':
                cip =   hl7.Field(field_separator, pl1.split(field_separator))  # CIP       (JHN)
            elif identificador == 'NNESP':
                dni =   hl7.Field(field_separator, pl1.split(field_separator))  # DNI      (NNESP)
            elif identificador == 'SS':
                ss =    hl7.Field(field_separator, pl1.split(field_separator))  # Num SS    (SS)
            elif identificador == 'PN':
                id_unico = hl7.Field(field_separator, pl1.split(field_separator))   # Identificador único   (PN)
            elif identificador == 'PI':
                nhc =   hl7.Field(field_separator, pl1.split(field_separator))  # NHC       (PI)
            '''
        '''
        import pdb
        pdb.set_trace()

        cip =   hl7.Field(field_separator, pidlist[0].split(field_separator))   # CIP       (JHN)
        dni =   hl7.Field(field_separator, pidlist[1].split(field_separator))   # DNI      (NNESP)
        nhc =   hl7.Field(field_separator, pidlist[2].split(field_separator))   # NHC       (PI)
        ss =    hl7.Field(field_separator, pidlist[3].split(field_separator))   # Num SS    (SS)'''

        return (identificadores)


    def procesar_paciente(self, crearlo=True, multiples_pacientes=False):
        """
        Procesa un paciente (segmento PID), actualizándolo si ya existe o creando
        uno nuevo si no existía. La identificación se hace por NHC. Devuelve el id
        del paciente. (antes en Mirth: MODIFICARPACIENTE)

        argumentos:

            crearlo  Indica si el paciente se crea en el caso de no existir. De esta
                        forma siempre se devuelve un Paciente. Si no, es posible que
                        devuelva None (si no existia)
            multiples_pacientes  Indica si esta función puede devolver una lista
                                    de pacientes, en caso contrario solo devolverá
                                    un paciente.
        """
        pacientes_result = []
        if self.msg.segment_count('PID') == 0:
            pids = []
        else:
            pids = self.msg.segments('PID')
        print "len(pids)", len(pids)
        for pid in pids:

            #pid = self.msg.segment('PID')
            #   extraer los campos
            #pid_id_list =      self._patient_identifier_list(pid, 3)   # (cip, dni, nhc, ss)
            identificadores =       self._patient_identifier_list(pid, 3)   # (cip, dni, nhc, ss)

            #import pdb
            #pdb.set_trace()

            pid2 =              pid.get(2.1)            #   ya no se usa... ahora el NHC va en PID.3
            cip =               identificadores['JHN']   #   cip
            dni =               identificadores['NNESP']   #   dni
            list_nhc_centro =       identificadores['PI']   #   nhc's centro
            id_unico =        identificadores['PN']   #   identificador único
            numss =             identificadores['SS']   #   num ss
            nombre =            pid.get(5.2)
            apellido1 =         pid.get(5.1)
            apellido2 =         pid.get(6.1)
            fecha_nacimiento =  endosys.lib.hl7_wrapper.hl7_to_date(pid.get(7.1), descartar_hora=True)
            sexo =              {'M': 1, 'F': 0, '': ''}.get(pid.get(8.1).upper(), None) # M -> 1, F -> 0
            direccion =         pid.get(11.1)
            poblacion =         pid.get(11.3)
            provincia =         pid.get(11.4)
            codigoPostal =      pid.get(11.5)
            # en realidad, el PID.13 debería ser el 1er telefono/fijo, y el PID.14 el 2º teéfono/movil.
            # además, de momento nunca se muestra el telefono2, aunque se guarda en BBDD...
            telefono1 =         pid.get(14.1)
            telefono2 =         pid.get(13.1)
            numero_expediente = pid.get(4.1) #nuevo campo pedido por candelaria, con prevision a que se utilice en mas sitios

            #si no viene el dato id_unico, no hacer nada, en caso contrario podrían crearse pacientees sin identificador
            print "id_unico", id_unico
            if not id_unico: return None


            def asignar_campos(paciente):
            
                # Comprobación, si se indica algún NHC para un centro que ya 
                # tenga, que coincida!
                for nhc_centro in list_nhc_centro:
                    centro_id = get_centro_id(codigo=nhc_centro['codigo_centro'])
                    if centro_id is None: continue
                    for p_centro in paciente.centros:
                        if p_centro.centro_id == centro_id:
                            if p_centro.nhc != nhc_centro['nhc']:
                                raise Exception("procesar_paciente(): Problema en la consistencia de datos. El NHC indicado ('%s') es distinto del ya existente ('%s') para el centro" % (nhc_centro['nhc'], p_centro.nhc))

            
                if not endosys.lib.hl7_wrapper.hl7absent(id_unico):        paciente.idunico =          endosys.lib.hl7_wrapper.hl7val(id_unico)
                if not endosys.lib.hl7_wrapper.hl7absent(dni):             paciente.DNI =              endosys.lib.hl7_wrapper.hl7val(dni)
                if not endosys.lib.hl7_wrapper.hl7absent(cip):             paciente.CIP =              endosys.lib.hl7_wrapper.hl7val(cip)
                if not endosys.lib.hl7_wrapper.hl7absent(numss):           paciente.numAfiliacion =    endosys.lib.hl7_wrapper.hl7val(numss)
                #
                if type(paciente.numAfiliacion) in (str, unicode): paciente.numAfiliacion = paciente.numAfiliacion[:50]
                #
                if not endosys.lib.hl7_wrapper.hl7absent(nombre):          paciente.nombre =           endosys.lib.hl7_wrapper.hl7val(nombre)
                if not endosys.lib.hl7_wrapper.hl7absent(apellido1):       paciente.apellido1 =        endosys.lib.hl7_wrapper.hl7val(apellido1)
                if not endosys.lib.hl7_wrapper.hl7absent(apellido2):       paciente.apellido2 =        endosys.lib.hl7_wrapper.hl7val(apellido2)
                if not endosys.lib.hl7_wrapper.hl7absent(sexo):                paciente.sexo =             endosys.lib.hl7_wrapper.hl7val(sexo)
                if not endosys.lib.hl7_wrapper.hl7absent(fecha_nacimiento): paciente.fechaNacimiento =     endosys.lib.hl7_wrapper.hl7val(fecha_nacimiento)
                if not endosys.lib.hl7_wrapper.hl7absent(direccion):       paciente.direccion =        endosys.lib.hl7_wrapper.hl7val(direccion)

                if not endosys.lib.hl7_wrapper.hl7absent(poblacion):
                    if config.get('INTEGRACION.POBLACIONES', '0') == '1':
                        paciente.poblacion =        poblacion_nombre_by_codigo(endosys.lib.hl7_wrapper.hl7val(poblacion))
                    else:
                        paciente.poblacion =        endosys.lib.hl7_wrapper.hl7val(poblacion)

                if not endosys.lib.hl7_wrapper.hl7absent(provincia):
                    if config.get('INTEGRACION.PROVINCIAS', '0') == '1':
                        paciente.provincia =        provincia_nombre_by_codigo(endosys.lib.hl7_wrapper.hl7val(provincia))
                    else:
                        paciente.provincia =        endosys.lib.hl7_wrapper.hl7val(provincia)

                if not endosys.lib.hl7_wrapper.hl7absent(codigoPostal):        paciente.codigoPostal =     endosys.lib.hl7_wrapper.hl7val(codigoPostal)
                if not endosys.lib.hl7_wrapper.hl7absent(telefono1):       paciente.telefono1 =        endosys.lib.hl7_wrapper.hl7val(telefono1)
                if not endosys.lib.hl7_wrapper.hl7absent(telefono2):       paciente.telefono2 =        endosys.lib.hl7_wrapper.hl7val(telefono2)
                if not endosys.lib.hl7_wrapper.hl7absent(numero_expediente): paciente.numero_expediente = endosys.lib.hl7_wrapper.hl7val(numero_expediente)

                #tratamiento del nhc centro en paciente
                #si el centro no existe en EndoSys NO damos de alta el nhc_centro

                #en caso de que se trate de una modificación, si el paciente en base de datos ya tiene registrado el nhc_centro que hemos recibido lo omitimos,
                #en caso de permitirlo estariamos realizando un cambio de número de historia y esto son palabras mayores

                for nhc_centro in list_nhc_centro:
                    centro_id = get_centro_id(codigo=nhc_centro['codigo_centro'])

                    if centro_id is None: continue

                    existe = False
                    for p_centro in paciente.centros:
                        if p_centro.centro_id == centro_id:
                            existe = True
                            break

                    if not existe:
                        rel =  Rel_Pacientes_Centros()
                        rel.nhc = nhc_centro['nhc']
                        rel.centro_id = centro_id
                        rel.paciente_id = paciente.id
                        #paciente.centros.append( rel )
                        meta.Session.save(rel)


            #   comprobar si ya existe, por NHC o por CIP (que es el NUHSA para Huelva)
            paciente = endosys.lib.pacientes.get_by_idunico(id_unico)

            #   si no existe y no se pasa el argumento 'crearlo', no hacer nada.
            if not paciente and not crearlo: return None

            #   recuperar los campos del paciente antes de ser modificado

            if paciente:
    ##          paciente_updating = Paciente()
    ##          for campo in paciente.c.keys():
    ##               paciente_updating.__setattr__(campo,paciente.__getattribute__(campo))

                # Mejor asi, porque:
                # - el objeto Paciente(), que es de sql alchemy, representa una fila de bbdd, y al
                #   instanciarlo se cree que quieres hacer un INSERT
                # - __setattr__ y __getattribute__ son métodos internos de python, y es mejor
                #   usar las funciones globales setattr() y getattr().
                params = {}

                params["centros"] = []
                for centro in paciente.centros:
                    params["centros"].append({'centro_id': centro.centro_id, 'nhc': centro.nhc})

                for campo in paciente.c.keys():
                    params[campo] = getattr(paciente, campo)
                paciente_updating = record(**params)
                # #############################################################

                self.paciente_updating = paciente_updating

            # si no existe, crearlo nuevo
            if not paciente:
                paciente = endosys.lib.pacientes.nuevo_paciente()
                meta.Session.save(paciente)
                meta.Session.flush()
            
            # actualizarlo
            asignar_campos(paciente)
            
            endosys.lib.pacientes.guardar_paciente(paciente, self)
            pacientes_result.append(paciente)

        if len(pacientes_result) == 0:
            return None

        if not multiples_pacientes:
            pacientes_result = pacientes_result[0]

        return pacientes_result

    
    def fusionar_paciente(self):
        """
        fusionar pacientes
        """
        modo = config.get('HL7.FUSIONES.MODO', '0')
        
        if modo == '0':
            # Backward compatibility. El mismo código que la v2.4.16, sin cambios.
            mrg = self.msg.segment('MRG')        
            paciente = self.procesar_paciente()

            identificadores = self._patient_identifier_list(mrg, 1)
            id_unico_origen = identificadores['PN']

            paciente_origen = endosys.lib.pacientes.get_by_idunico(id_unico_origen)
            FusionarPacientes(paciente_origen, id_unico_origen, paciente, self)

        elif modo == '1':
            # IDUNICO
            raise Exception("No implementado")
            #FusionarPacientesM1()
            
        elif modo == '2':
            # NHC + CENTRO
            
            # Obtener el código del centro del campo MSH.4 (Sending Facility)
            # (se obtiene de la posición 3, por las peculiaridades del MSH...)
            codigo_centro = self.msh.get(3.1)

            # Obtener NHC origen
            d = endosys.lib.hl7_wrapper.get_patient_identifier_list(self.msg.segment('MRG')[1])
            nhc_origen = endosys.lib.hl7_wrapper.get_nhc_centro(d, codigo_centro)
            idunico_origen = endosys.lib.hl7_wrapper.get_idunico(d)
            if nhc_origen == None:
                raise Exception("Hl7Process.fusionar_paciente(): [Modo 2] No se ha indicado el NHC de origen para el centro %s" % codigo_centro)
            if idunico_origen == None:
                raise Exception("Hl7Process.fusionar_paciente(): [Modo 2] No se ha indicado el IDUNICO de origen")

            # Obtener NHC destino
            d = endosys.lib.hl7_wrapper.get_patient_identifier_list(self.msg.segment('PID')[3])
            nhc_destino = endosys.lib.hl7_wrapper.get_nhc_centro(d, codigo_centro)
            idunico_destino = endosys.lib.hl7_wrapper.get_idunico(d)
            if nhc_destino == None:
                raise Exception("Hl7Process.fusionar_paciente(): [Modo 2] No se ha indicado el NHC de destino para el centro %s" % codigo_centro)
            if idunico_destino == None:
                raise Exception("Hl7Process.fusionar_paciente(): [Modo 2] No se ha indicado el IDUNICO de destino")

            pid = self.msg.segment('PID')
            FusionarPacientesM2(codigo_centro, nhc_origen, nhc_destino, idunico_origen, idunico_destino, pid)


    def _obtener_agenda_id(self, codigo_agenda=None, codigo_servicio=None):
        """
        Obtener el id de una agenda a partir del Código de Agenda y Codigo de
        Servicio obtenidos de un mensaje HL7.
        El funcionamiento dependerá de la clave del INI
        "HL7.CITAS.MODO_ASIGNACION_AGENDA".
        
        En modo AGENDA se utiliza el Código de Agenda para identificarla.
        
        En modo SERVICIO se utiliza el Código de Servicio para identificar el
        servicio, y se devuelve la primera agenda que tenga asignada.
        """
        modo = config.get('HL7.CITAS.MODO_ASIGNACION_AGENDA', 'AGENDA').upper()
        agenda_id = None

        if modo == 'AGENDA':
            if not endosys.lib.hl7_wrapper.hl7absent(codigo_agenda):
                agenda = get_agenda(codigo=codigo_agenda)
                if agenda:
                    agenda_id = agenda.id

        elif modo == 'SERVICIO':
            # asigna la primera agenda del servicio
            if not endosys.lib.hl7_wrapper.hl7absent(codigo_servicio):
                agenda_id = get_servicio_y_agenda_id(codigo=codigo_servicio)[1]

        return agenda_id


    def modificar_cita_ORM(self, paciente_id):
        """
        Modificar una cita de EndoSys Web a partir de un mensaje ORM^O01 de tipo XO.
        Se identifica la cita mediante el Número de Petición.
        
        Hasta la versión 2.4.16 se modificaban estos campos:
        
          cita.fecha                        OBR.7.1
          cita.hora                         OBR.7.1
          cita.ex.obr                       OBR
        
        A partir de la versión 2.4.17 se modifican estos campos:
          cita.fecha                        OBR.7.1
          cita.hora                         OBR.7.1
          cita.ex.obr                       OBR
          cita.prioridad_id                 obtenido a partir de ORC.7.6
          cita.observaciones                NTE.3.1
          cita.agenda_id                    obtenido a partir de OBR.21.1 o PV1.10.1, según el MODO_ASIGNACION_AGENDA
          cita.ex.idunico                   PID.3
          cita.ex.cip                       PID.3
          cita.ex.prestacion_cod            OBR.4.1
          cita.ex.prestacion_descr          OBR.4.2
          cita.ex.agenda_cod                OBR.21.1
          cita.ex.servicio_cod              PV1.10.1
          cita.ex.medico_peticionario_cod   ORC.19.1
          cita.ex.medico_peticionario_descr ORC.19.2, ORC.19.3

        Se omite la modificación de estos campos, para evitar posibles
        incompatibilidades en actualizaciones:
          cita.ex.pv1                       PV1
          cita.ex.orc                       ORC

        Y además se gestiona correctamente si un campo es NULL (ponerlo a null)
        o ABSENT (ignorarlo).
        
        Ahora se requiere que tenga los segmentos PID y PV1.
        
        En ningún caso se puede cambiar el paciente asignado a una cita.
        """
        #   extraer los campos
        pid = self.msg.segment('PID')
        obr = self.msg.segment('OBR')
        orc = self.msg.segment('ORC')
        pv1 = self.msg.segment('PV1')
        nte = self.msg.segment_optional('NTE')

        identificadores =           self._patient_identifier_list(pid, 3)                   #   (cip, dni, nhc, ss)
        cip =                       identificadores['JHN']                                  #   cip
        id_unico =                  identificadores['PN']                                   #   identificador único
        
        fecha_hora =                endosys.lib.hl7_wrapper.hl7val(obr.get(7.1))                  #   HL7: Observation Date/Time
        codigo_prestacion =         endosys.lib.hl7_wrapper.hl7val(obr.get(4.1))                  #   HL7: Universal Service ID (identifier)
        descr_prestacion =          endosys.lib.hl7_wrapper.hl7val(obr.get(4.2))                  #   HL7: Universal Service ID (text)
        codigo_agenda =             endosys.lib.hl7_wrapper.hl7val(obr.get(21.1))                 #   HL7: Filler Field (Candelaria: código de agenda)
        
        
        numero_peticion =           endosys.lib.hl7_wrapper.hl7val(orc.get(2.1))                  #   HL7: Placer Order Number
        codigo_prioridad =          endosys.lib.hl7_wrapper.hl7val(orc.get(7.6))                  #   HL7: Priority (implementado para candelaria. Valores( 1-normal, 2-preferente, 3-urgente )
        medico_peticionario_cod =   endosys.lib.hl7_wrapper.hl7val(orc.get(19.1))                 #   HL7: Action By (ID Number)
        medico_peticionario_descr = '%s, %s' % (orc.get(19.2), orc.get(19.3))               #   HL7: Action By (Family Name, Given Name)    XXX falta hl7val()

        codigo_servicio =           endosys.lib.hl7_wrapper.hl7val(pv1.get(10.1))                 #   HL7: Hospital Service
        numero_episodio =           endosys.lib.hl7_wrapper.hl7val(pv1.get(19.1))				    #   HL7: Visit Number
        
        observaciones =             endosys.lib.hl7_wrapper.hl7val(nte.get(3.1)) if nte else None #   HL7: Comment

        def asignar_campos(cita):
        
        
        
        
        
            # Valores del mensaje, en "cita"
            if not endosys.lib.hl7_wrapper.hl7absent(fecha_hora):
                cita.fecha =                endosys.lib.hl7_wrapper.hl7_to_date(fecha_hora, descartar_hora=True)
                cita.hora =                 endosys.lib.hl7_wrapper.hl7_to_datetime(fecha_hora)
                
            if not endosys.lib.hl7_wrapper.hl7absent(codigo_prioridad):
                cita.prioridad_id =         endosys.model.prioridades.prioridad_id_by_codigo(codigo_prioridad)
                
            if not endosys.lib.hl7_wrapper.hl7absent(observaciones):
                if observaciones is None:
                    cita.observaciones =    observaciones
                else:
                    # Se espera que pueda venir con saltos de linea (\n) sin retornos de carro (\r), y se han de convertir a (\n\r)
                    cita.observaciones =    observaciones.replace('\r', '').replace('\n', '\n\r')

            cita.agenda_id =                self._obtener_agenda_id(codigo_agenda, codigo_servicio)

            # Valores del mensaje, en "cita_ex"
            if not endosys.lib.hl7_wrapper.hl7absent(id_unico):
                cita.ex.idunico =           id_unico
            if not endosys.lib.hl7_wrapper.hl7absent(cip):
                cita.ex.cip =               cip
                
                
            if not endosys.lib.hl7_wrapper.hl7absent(numero_episodio):
                cita.ex.numero_episodio =   numero_episodio
            if not endosys.lib.hl7_wrapper.hl7absent(codigo_prestacion):
                cita.ex.prestacion_cod =    codigo_prestacion
            if not endosys.lib.hl7_wrapper.hl7absent(descr_prestacion):
                cita.ex.prestacion_descr =  descr_prestacion
            if not endosys.lib.hl7_wrapper.hl7absent(codigo_agenda):
                cita.ex.agenda_cod =        codigo_agenda
            if not endosys.lib.hl7_wrapper.hl7absent(codigo_servicio):
                cita.ex.servicio_cod =      codigo_servicio

            if not endosys.lib.hl7_wrapper.hl7absent(medico_peticionario_cod):
                cita.ex.medico_peticionario_cod = medico_peticionario_cod
            if not endosys.lib.hl7_wrapper.hl7absent(medico_peticionario_descr):
                cita.ex.medico_peticionario_descr = medico_peticionario_descr
                
                
                
            cita.ex.obr =                   unicode(obr)    # OJO se ha implementado este comando por Candelaria
                                                            # el motivo es que en el obr 10.2 tienen el numero de cita
                                                            # y al ser una reprogramación, cambia.

                                                            
        # Obtener la cita mediante el Número de Petición
        cita = endosys.lib.citas.get_by_id_ext(numero_peticion, 'numero_peticion')
        if cita:
            # Recoger la cita antes de ser modificada, para registrar
            cita_old = {}
            for campo in cita.c.keys():
                cita_old[campo] = getattr(cita, campo)
            cita_updating = record(**cita_old)

            # Modificar la cita
            asignar_campos(cita)
            endosys.lib.citas.guardar_cita(cita, "sysadmin", self.ipaddress, cita_updating, self.id_hl7_log)
        else:
            # Si no se ha encontrado la cita, logearlo y no hacer nada.
            log.info("modificar_cita_ORM() - No se ha encontrado la cita con NUMERO DE PETICION = %s. No se hace ningún cambio.", numero_peticion)

    
    def nueva_cita_ORM(self, paciente_id):
        """
        Crear una nueva cita de EndoSys Web a partir de un mensaje ORM^O01 de tipo NW.

        El paciente_id se ha tenido que obtener antes desde procesar_paciente().
        """
        #   extraer los campos
        pid = self.msg.segment('PID')
        obr = self.msg.segment('OBR')
        orc = self.msg.segment('ORC')
        pv1 = self.msg.segment('PV1')
        nte = self.msg.segment_optional('NTE')

        identificadores =           self._patient_identifier_list(pid, 3)                   #   (cip, dni, nhc, ss)
        cip =                       identificadores['JHN']                                  #   cip
        id_unico =                  identificadores['PN']                                   #   identificador único
            
        fecha_hora =                endosys.lib.hl7_wrapper.hl7val(obr.get(7.1))                  #   HL7: Observation Date/Time
        codigo_prestacion =         endosys.lib.hl7_wrapper.hl7val(obr.get(4.1))                  #   HL7: Universal Service ID (identifier)
        descr_prestacion =          endosys.lib.hl7_wrapper.hl7val(obr.get(4.2))                  #   HL7: Universal Service ID (text)
        codigo_agenda =             endosys.lib.hl7_wrapper.hl7val(obr.get(21.1))                 #   HL7: Filler Field (Candelaria: código de agenda)
    ##  descr_agenda = ...OBR.21.2¿?            
                
        numero_peticion =           endosys.lib.hl7_wrapper.hl7val(orc.get(2.1))                  #   HL7: Placer Order Number
        codigo_prioridad =          endosys.lib.hl7_wrapper.hl7val(orc.get(7.6))                  #   HL7: Priority (implementado para candelaria. Valores( 1-normal, 2-preferente, 3-urgente )
        medico_peticionario_cod =   endosys.lib.hl7_wrapper.hl7val(orc.get(19.1))                 #   HL7: Action By (ID Number)
        medico_peticionario_descr = '%s, %s' % (orc.get(19.2), orc.get(19.3))               #   HL7: Action By (Family Name, Given Name)    XXX falta hl7val()
                    
        codigo_servicio =           endosys.lib.hl7_wrapper.hl7val(pv1.get(10.1))                 #   HL7: Hospital Service
        numero_episodio =           endosys.lib.hl7_wrapper.hl7val(pv1.get(19.1))				    #   HL7: Visit Number
        
        observaciones =             endosys.lib.hl7_wrapper.hl7val(nte.get(3.1)) if nte else None #   HL7: Comment

        def asignar_campos(cita):
            # Valores fijos
            cita.duracion =                 10              # 10 minutos, por asignar algo...
            cita.paciente_id =              paciente_id
            cita.ex.estado =                0

            # Valores del mensaje, en "cita"
            if not endosys.lib.hl7_wrapper.hl7absent(fecha_hora):
                cita.fecha =                endosys.lib.hl7_wrapper.hl7_to_date(fecha_hora, descartar_hora=True)
                cita.hora =                 endosys.lib.hl7_wrapper.hl7_to_datetime(fecha_hora)
                
            if not endosys.lib.hl7_wrapper.hl7absent(codigo_prioridad):
                cita.prioridad_id =         endosys.model.prioridades.prioridad_id_by_codigo(codigo_prioridad)
                
            if not endosys.lib.hl7_wrapper.hl7absent(observaciones):
                if observaciones is None:
                    cita.observaciones =    observaciones
                else:
                    # Se espera que pueda venir con saltos de linea (\n) sin retornos de carro (\r), y se han de convertir a (\n\r)
                    cita.observaciones =    observaciones.replace('\r', '').replace('\n', '\n\r')

            cita.agenda_id =                self._obtener_agenda_id(codigo_agenda, codigo_servicio)

            # Valores del mensaje, en "cita_ex"
            if not endosys.lib.hl7_wrapper.hl7absent(id_unico):
                cita.ex.idunico =           id_unico
            if not endosys.lib.hl7_wrapper.hl7absent(cip):
                cita.ex.cip =               cip
            if not endosys.lib.hl7_wrapper.hl7absent(numero_peticion):
                cita.ex.numero_peticion =   numero_peticion
            if not endosys.lib.hl7_wrapper.hl7absent(numero_episodio):
                cita.ex.numero_episodio =   numero_episodio
            if not endosys.lib.hl7_wrapper.hl7absent(codigo_prestacion):
                cita.ex.prestacion_cod =    codigo_prestacion
            if not endosys.lib.hl7_wrapper.hl7absent(descr_prestacion):
                cita.ex.prestacion_descr =  descr_prestacion
            if not endosys.lib.hl7_wrapper.hl7absent(codigo_agenda):
                cita.ex.agenda_cod =        codigo_agenda
            if not endosys.lib.hl7_wrapper.hl7absent(codigo_servicio):
                cita.ex.servicio_cod =      codigo_servicio

            if not endosys.lib.hl7_wrapper.hl7absent(medico_peticionario_cod):
                cita.ex.medico_peticionario_cod = medico_peticionario_cod
            if not endosys.lib.hl7_wrapper.hl7absent(medico_peticionario_descr):
                cita.ex.medico_peticionario_descr = medico_peticionario_descr

            cita.ex.pv1 =   unicode(pv1)
            cita.ex.obr =   unicode(obr)
            cita.ex.orc =   unicode(orc)

        # Comprobar si ya existe, por Número de Petición. Si ya existe, la
        # modifica. Se hace así para que funcione en integraciones con ORMs y
        # SIUs vinculados.
        # Si no existe la crea, que es el comportamiento más normal.
        cita = endosys.lib.citas.get_by_id_ext(numero_peticion, 'numero_peticion')
        if cita:
            # Recoger la cita antes de ser modificada, para registrar
            cita_old = {}
            for campo in cita.c.keys():
                cita_old[campo] = getattr(cita, campo)
            cita_updating = record(**cita_old)

            # Modificar la cita
            asignar_campos(cita)
            endosys.lib.citas.guardar_cita(cita, "sysadmin", self.ipaddress, cita_updating, self.id_hl7_log)
        else:
            # No existe, crearla nueva
            cita = endosys.lib.citas.nueva_cita()
            asignar_campos(cita)
            endosys.lib.citas.guardar_cita(cita, "sysadmin", self.ipaddress, None, self.id_hl7_log)


    def cancelar_cita_ORM(self):
        """
        Cancelar una cita de EndoSys Web a partir de un mensaje
        de petición (ORM) con order_control=CA
        (Antes en Mirth: ELIMINAR CITA)
        """
        #   extraer los campos
        pid = self.msg.segment('PID')
        obr = self.msg.segment('OBR')
        orc = self.msg.segment('ORC')
        pv1 = self.msg.segment('PV1')
        numero_peticion =   orc.get(2.1)    #   HL7: Placer Order Number

        #   comprobar si existe, por ID EXT
        cita = endosys.lib.citas.get_by_id_ext(numero_peticion, 'numero_peticion') # XXX en este caso es el numero_peticion, pero en otras integraciones puede ser otro...
        if cita:
            #   existe, eliminarla
            endosys.lib.citas.eliminar_cita(cita, "sysadmin", self.ipaddress, self.id_hl7_log)
        else:
            #   no existe, error...
            pass


    def nueva_cita_SIU(self, paciente_id):
        """
        Crear una nueva cita de EndoSys Web a partir de un mensaje
        de cita (SIU)
        El paciente_id se ha tenido que obtener antes desde procesar_paciente()
        Devuelve el id de la cita.
        (El mapeo de campos se ha hecho igual a la integración del Gregorio Marañón)
        """
        #   extraer los campos
        pid = self.msg.segment('PID')
        #tq1 = msg.segment('TQ1')
        ais = self.msg.segment('AIS')
        pv1 = self.msg.segment('PV1')
        sch = self.msg.segment('SCH')
        nte = self.msg.segment_optional('NTE')

        #id_list =                  self._patient_identifier_list(pid, 3)
        #cip =                      endosys.lib.hl7_wrapper.hl7val(id_list[0].get(1))   #   cip
        #nhc =                      endosys.lib.hl7_wrapper.hl7val(id_list[2].get(1))   #   nhc
        identificadores =       self._patient_identifier_list(pid, 3)   # (cip, dni, nhc, ss)
        cip =               identificadores['JHN']   #   cip
        id_unico =        identificadores['PN']   #   identificador único

        fecha_hora =                endosys.lib.hl7_wrapper.hl7val(ais.get(4.1))
        #codigo_prestacion =    sch.get(6.1)    #   HL7: Universal Service ID (identifier)
        #descr_prestacion = sch.get(6.2)    #   HL7: Universal Service ID (text)
        codigo_prestacion =         endosys.lib.hl7_wrapper.hl7val(ais.get(3.1))   #   HL7: Universal Service ID (identifier)
        descr_prestacion =          endosys.lib.hl7_wrapper.hl7val(ais.get(3.2))   #   HL7: Universal Service ID (text)
        codigo_servicio =           endosys.lib.hl7_wrapper.hl7val(pv1.get(10.1))   #   HL7: Hospital Service
        numero_episodio =           endosys.lib.hl7_wrapper.hl7val(pv1.get(19.1))   #   HL7: Visit Number
        medico_peticionario_cod =   endosys.lib.hl7_wrapper.hl7val(pv1.get(8.1))   #   HL7: Referring Doctor
        medico_peticionario_descr = '%s, %s' % (pv1.get(8.2), pv1.get(8.3)) #   XXX falta hl7val()

        observaciones = None
        if nte:
            observaciones =             endosys.lib.hl7_wrapper.hl7val(nte.get(3.1))   #   HL7: Comment

        numero_cita =               endosys.lib.hl7_wrapper.hl7val(sch.get(1.1))   #   HL7: Placer Appointment ID
        codigo_agenda =             endosys.lib.hl7_wrapper.hl7val(sch.get(5.1))   #   HL7: Schedule ID (identifier)
        descr_agenda =              endosys.lib.hl7_wrapper.hl7val(sch.get(5.2))   #   HL7: Schedule ID (text)
        numero_peticion =           endosys.lib.hl7_wrapper.hl7val(sch.get(26.1))  #   Número de pedido/peticion asociado a la cita
        codigo_prioridad =          endosys.lib.hl7_wrapper.hl7val(sch.get(11.6))         # prioridad de la cita
        filler_status_code =        endosys.lib.hl7_wrapper.hl7val(sch.get(25.1))         # filler status code (booked, etc...)
        servicio_peticionario =     pv1.get(8.9).split("&")
        servicio_peticionario_cod = endosys.lib.hl7_wrapper.hl7val(servicio_peticionario[0])
        servicio_peticionario_descr =   None
        if  len(servicio_peticionario) > 1:
            servicio_peticionario_descr = endosys.lib.hl7_wrapper.hl7val(servicio_peticionario[1])

        #   XXX Mirth también enviaba: _resultado_enviado = 0. Ahora esto se almacena en cita_ex.estado

        def asignar_campos(cita):
            #   4-12-2014: Comprobar que si vienen vacios no sobrescriban los existentesm
            #   ya que la cita puede existir anteiormente, creada por un ORM, por ejemplo...

            #      Valores fijos
            cita.duracion =             10 # XXX    10 minutos, por asignar algo...
            cita.paciente_id =          paciente_id
            cita.ex.estado =            0   # xxx

            #      Valores del mensaje, en "cita"
            if not endosys.lib.hl7_wrapper.hl7absent(fecha_hora):
                cita.fecha =            endosys.lib.hl7_wrapper.hl7_to_date(fecha_hora, descartar_hora=True)
            if not endosys.lib.hl7_wrapper.hl7absent(fecha_hora):
                cita.hora =             endosys.lib.hl7_wrapper.hl7_to_datetime(fecha_hora)
            if not endosys.lib.hl7_wrapper.hl7absent(codigo_prioridad):
                cita.prioridad_id =     endosys.model.prioridades.prioridad_id_by_codigo(codigo_prioridad)

            if not endosys.lib.hl7_wrapper.hl7absent(observaciones) and observaciones is not None:
                cita.observaciones =    observaciones

            cita.agenda_id = self._obtener_agenda_id(codigo_agenda, codigo_servicio)

            #      Valores del mensaje, en "cita_ex"
            if not endosys.lib.hl7_wrapper.hl7absent(id_unico):
                cita.ex.idunico =                       id_unico
            if not endosys.lib.hl7_wrapper.hl7absent(cip):
                cita.ex.cip =                       cip
            if not endosys.lib.hl7_wrapper.hl7absent(numero_peticion):
                cita.ex.numero_peticion =           numero_peticion
            if not endosys.lib.hl7_wrapper.hl7absent(numero_cita):
                cita.ex.numero_cita =               numero_cita
            if not endosys.lib.hl7_wrapper.hl7absent(numero_episodio):
                cita.ex.numero_episodio =           numero_episodio
            if not endosys.lib.hl7_wrapper.hl7absent(codigo_prestacion):
                cita.ex.prestacion_cod =            codigo_prestacion
            if not endosys.lib.hl7_wrapper.hl7absent(descr_prestacion):
                cita.ex.prestacion_descr =          descr_prestacion
            if not endosys.lib.hl7_wrapper.hl7absent(codigo_agenda):
                cita.ex.agenda_cod =                codigo_agenda
            if not endosys.lib.hl7_wrapper.hl7absent(descr_agenda):
                cita.ex.agenda_descr =              descr_agenda
            if not endosys.lib.hl7_wrapper.hl7absent(codigo_servicio):
                cita.ex.servicio_cod =              codigo_servicio
            if not endosys.lib.hl7_wrapper.hl7absent(medico_peticionario_cod):
                cita.ex.medico_peticionario_cod =   medico_peticionario_cod
            if not endosys.lib.hl7_wrapper.hl7absent(medico_peticionario_descr):
                cita.ex.medico_peticionario_descr = medico_peticionario_descr
            if not endosys.lib.hl7_wrapper.hl7absent(servicio_peticionario_cod):
                cita.ex.servicio_peticionario_cod = servicio_peticionario_cod
            if not endosys.lib.hl7_wrapper.hl7absent(servicio_peticionario_descr):
                cita.ex.servicio_peticionario_descr = servicio_peticionario_descr
            if not endosys.lib.hl7_wrapper.hl7absent(filler_status_code):
                cita.ex.filler_status_code = filler_status_code

            # los objetos de tipo hl7.Segment (pv1, obr...) tienen la funcion _unicode() que los vuelve a reconstruir
            cita.ex.pv1 =   unicode(pv1)

    ##      cita.tipoExploracion_id =   get_tipoExploracion_id_from_prestacion(prestacion=codigo_prestacion, servicio=codigo_servicio)

    ##  #   comprobar si ya existe, por ID EXT (no debería)
    ##  cita = citas.get_by_id_ext(numero_cita, 'numero_cita') # XXX en este caso es el numero_cita, pero en otras integraciones puede ser otro...
    ##  if cita:
    ##      #   ya existe! dar un error
    ##      pass
    ##  else:
    ##      #   no existe, crearla nueva
    ##      cita = citas.nueva_cita()
    ##      asignar_campos(cita)
    ##      citas.guardar_cita(cita)

        #   4-12-2014: Para que funcione en integraciones con ORMs y SIUs vinculados.
        #    comprobar si ya existe, primero por nº de cita y luego por nº de petición
        cita = endosys.lib.citas.get_by_id_ext(numero_cita, 'numero_cita')
        if not cita:
            cita = endosys.lib.citas.get_by_id_ext(numero_peticion, 'numero_peticion')
        #    si no existia la cita, la crea.
        if not cita: cita = endosys.lib.citas.nueva_cita()
        #   si la cita existe recuperamos la cita antes de ser modificada par poder registrarla
        cita_updating = None
        if cita:
            cita_old = {}
            for campo in cita.c.keys():
                cita_old[campo] = getattr(cita, campo)

            cita_updating = record(**cita_old)

        #     Luego la actualiza (la existente o nueva) con los datos recibidos.
        asignar_campos(cita)

        endosys.lib.citas.guardar_cita(cita, "sysadmin", self.ipaddress, cita_updating, self.id_hl7_log)

        return cita.id


    def modificar_cita_SIU(self, paciente_id):
        """
        Modificar una cita de EndoSys Web a partir de un mensaje
        de cita (SIU S13 y S14)
        Devuelve el id de la cita.
        XXX si no existe, crearla nueva¿? por si acaso, se pasa el id del paciente también...

        (El mapeo de campos se ha hecho igual a la integración del Gregorio Marañón)

        XXX ATENCION: De momento modifica todos los campos de la cita excepto el
        paciente y el numero_cita. Este parece ser el comportamiento correcto para
        el S13 pero no para el S14. (Todo esto según integración del Gregorio)

        Segmentos con información correcta:

                PID TQ1 AIS PV1 SCH
        S13:    SI  SI  SI  SI  SI
        S14:    SI  NO  NO  ¿?  SI

        """
        #   extraer los campos
        pid = self.msg.segment('PID')
        #tq1 = self.msg.segment('TQ1')
        ais = self.msg.segment('AIS')
        pv1 = self.msg.segment('PV1')
        sch = self.msg.segment('SCH')
        nte = self.msg.segment_optional('NTE')

        #id_list =                  self._patient_identifier_list(pid, 3)
        #cip =                      endosys.lib.hl7_wrapper.hl7val(id_list[0].get(1))   #   cip
        #nhc =                      endosys.lib.hl7_wrapper.hl7val(id_list[2].get(1))   #   nhc

        identificadores =       self._patient_identifier_list(pid, 3)   # (cip, dni, nhc, ss)
        cip =               identificadores['JHN']   #   cip
        id_unico =        identificadores['PN']   #   identificador único


        fecha_hora =                endosys.lib.hl7_wrapper.hl7val(ais.get(4.1))
        #codigo_prestacion =    sch.get(6.1)    #   HL7: Universal Service ID (identifier)
        #descr_prestacion = sch.get(6.2)    #   HL7: Universal Service ID (text)
        codigo_prestacion =         endosys.lib.hl7_wrapper.hl7val(ais.get(3.1))   #   HL7: Universal Service ID (identifier)
        descr_prestacion =          endosys.lib.hl7_wrapper.hl7val(ais.get(3.2))   #   HL7: Universal Service ID (text)
        codigo_servicio =           endosys.lib.hl7_wrapper.hl7val(pv1.get(10.1))   #   HL7: Hospital Service
        numero_episodio =           endosys.lib.hl7_wrapper.hl7val(pv1.get(19.1))   #   HL7: Visit Number
        medico_peticionario_cod =   endosys.lib.hl7_wrapper.hl7val(pv1.get(8.1))   #   HL7: Referring Doctor
        medico_peticionario_descr = '%s, %s' % (pv1.get(8.2), pv1.get(8.3)) #   XXX falta hl7val()

        observaciones = None
        if nte:
            observaciones =             endosys.lib.hl7_wrapper.hl7val(nte.get(3.1))   #   HL7: Comment

        numero_cita =               endosys.lib.hl7_wrapper.hl7val(sch.get(1.1))   #   HL7: Placer Appointment ID
        codigo_agenda =             endosys.lib.hl7_wrapper.hl7val(sch.get(5.1))   #   HL7: Schedule ID (identifier)
        descr_agenda =              endosys.lib.hl7_wrapper.hl7val(sch.get(5.2))   #   HL7: Schedule ID (text)
        numero_peticion =           endosys.lib.hl7_wrapper.hl7val(sch.get(26.1))  #   Número de pedido/peticion asociado a la cita
        codigo_prioridad =          endosys.lib.hl7_wrapper.hl7val(sch.get(11.6))         # prioridad de la cita
        filler_status_code =        endosys.lib.hl7_wrapper.hl7val(sch.get(25.1))         # filler status code (booked, etc...)
        servicio_peticionario =     pv1.get(8.9).split("&")
        servicio_peticionario_cod = endosys.lib.hl7_wrapper.hl7val(servicio_peticionario[0])
        servicio_peticionario_descr =   None
        if  len(servicio_peticionario) > 1:
            servicio_peticionario_descr = endosys.lib.hl7_wrapper.hl7val(servicio_peticionario[1])

        #   XXX Mirth también enviaba: _resultado_enviado = 0. Ahora esto se almacena en cita_ex.estado

        def asignar_campos(cita):
            #   4-12-2014: Comprobar que si vienen vacios no sobrescriban los existentes

            #      Valores fijos
            cita.paciente_id =          paciente_id # XXX realmente es necesario asignarlo de nuevo?
            cita.ex.estado =            0   # xxx

            #      Valores del mensaje, en "cita"
            if not endosys.lib.hl7_wrapper.hl7absent(fecha_hora):
                cita.fecha =            endosys.lib.hl7_wrapper.hl7_to_date(fecha_hora, descartar_hora=True)
            if not endosys.lib.hl7_wrapper.hl7absent(fecha_hora):
                cita.hora =             endosys.lib.hl7_wrapper.hl7_to_datetime(fecha_hora)
            if not endosys.lib.hl7_wrapper.hl7absent(codigo_prioridad):
                cita.prioridad_id =     endosys.model.prioridades.prioridad_id_by_codigo(codigo_prioridad)

            if not endosys.lib.hl7_wrapper.hl7absent(observaciones) and observaciones is not None:
                cita.observaciones =    observaciones

            cita.agenda_id = self._obtener_agenda_id(codigo_agenda, codigo_servicio)

            #      Valores del mensaje, en "cita_ex"
            if not endosys.lib.hl7_wrapper.hl7absent(id_unico):
                cita.ex.idunico =                       id_unico
            if not endosys.lib.hl7_wrapper.hl7absent(cip):
                cita.ex.cip =                       cip
            if not endosys.lib.hl7_wrapper.hl7absent(numero_peticion):
                cita.ex.numero_peticion =           numero_peticion
            if not endosys.lib.hl7_wrapper.hl7absent(numero_cita):
                cita.ex.numero_cita =               numero_cita
            if not endosys.lib.hl7_wrapper.hl7absent(numero_episodio):
                cita.ex.numero_episodio =           numero_episodio
            if not endosys.lib.hl7_wrapper.hl7absent(codigo_prestacion):
                cita.ex.prestacion_cod =            codigo_prestacion
            if not endosys.lib.hl7_wrapper.hl7absent(descr_prestacion):
                cita.ex.prestacion_descr =          descr_prestacion
            if not endosys.lib.hl7_wrapper.hl7absent(codigo_agenda):
                cita.ex.agenda_cod =                codigo_agenda
            if not endosys.lib.hl7_wrapper.hl7absent(descr_agenda):
                cita.ex.agenda_descr =              descr_agenda
            if not endosys.lib.hl7_wrapper.hl7absent(codigo_servicio):
                cita.ex.servicio_cod =              codigo_servicio
            if not endosys.lib.hl7_wrapper.hl7absent(medico_peticionario_cod):
                cita.ex.medico_peticionario_cod =   medico_peticionario_cod
            if not endosys.lib.hl7_wrapper.hl7absent(medico_peticionario_descr):
                cita.ex.medico_peticionario_descr = medico_peticionario_descr
            if not endosys.lib.hl7_wrapper.hl7absent(servicio_peticionario_cod):
                cita.ex.servicio_peticionario_cod = servicio_peticionario_cod
            if not endosys.lib.hl7_wrapper.hl7absent(servicio_peticionario_descr):
                cita.ex.servicio_peticionario_descr = servicio_peticionario_descr
            if not endosys.lib.hl7_wrapper.hl7absent(filler_status_code):
                cita.ex.filler_status_code = filler_status_code

            # los objetos de tipo hl7.Segment (pv1, obr...) tienen la funcion _unicode() que los vuelve a reconstruir
            cita.ex.pv1 =   unicode(pv1)

    ##      cita.tipoExploracion_id =   get_tipoExploracion_id_from_prestacion(prestacion=codigo_prestacion, servicio=codigo_servicio)

        #   comprobar si ya existe, por ID EXT (no debería)
        cita = endosys.lib.citas.get_by_id_ext(numero_cita, 'numero_cita') # XXX en este caso es el numero_cita, pero en otras integraciones puede ser otro...
        if cita:
            #   existe, actualizarla

            #   si la cita existe recuperamos la cita antes de ser modificada par poder registrarla
            cita_old = {}
            for campo in cita.c.keys():
                cita_old[campo] = getattr(cita, campo)
            cita_updating = record(**cita_old)

            asignar_campos(cita)
            endosys.lib.citas.guardar_cita(cita, "sysadmin", self.ipaddress, cita_updating, self.id_hl7_log)
        else:
            #   no existe, crearla nueva (XXX seguro?)
            cita = endosys.lib.citas.nueva_cita()
            asignar_campos(cita)
            endosys.lib.citas.guardar_cita(cita, "sysadmin", self.ipaddress, None, self.id_hl7_log)
        return cita.id


    def cancelar_cita_SIU(self):
        """
        Cancelar una cita de EndoSys Web a partir de un mensaje
        de petición (SIU)
        (El mapeo de campos se ha hecho igual a la integración del Gregorio Marañón)
        """
        #   extraer los campos
        pid = self.msg.segment('PID')
        sch = self.msg.segment('SCH')
        numero_cita =       sch.get(1.1)    #   HL7: Placer Appointment ID
        log.debug('CANCELAR CITA %s', numero_cita)

        #   comprobar si existe, por ID EXT
        cita = endosys.lib.citas.get_by_id_ext(numero_cita, 'numero_cita') # XXX en este caso es el numero_cita, pero en otras integraciones puede ser otro...
        if cita:
            #   existe, eliminarla
            if not cita.exploracion_id: #verificar que la cita no esta vinculada a una exploración sino no se puede enviar
                endosys.lib.citas.eliminar_cita(cita, "sysadmin", self.ipaddress, self.id_hl7_log)
            else:
                raise Exception('No se ha podido eliminar la cita porque tiene asociada una exploración')
        else:
            #   no existe, error...
            pass


    def nuevas_citas_SQR(self, pacientes_ids):
        """
        Crear nuevas citas de EndoSys Web a partir de un mensaje
        de SQR, respuesta del SQM.
        
        Los pacientes_ids se han obtenido antes desde procesar_paciente().
        Se devuelven en el mismo orden que están los PIDs en el mensaje HL7,
        por lo que se puede usar el mismo indexado.
        
        Devuelve los ids de las citas.
        
        NOTA: El SQR puede tener varias citas, representadas por grupos de
        segmentos. Según he investigado, parece que es algo correcto en el estandar
        HL7. En este caso, la forma de identificar cada grupo es buscando el primer
        segmento de cada grupo, que es el SCH.
        Para EndoSys siempre tienen que llegar estos segmentos en cada
        grupo (y en el mismo orden):
            SCH
            PID
            PV1
            RGS
            AIS
            AIL
            
        Esta implementación se hace a partir de una integración en el CHUS, por
        lo que es posible que si en un futuro se quiere utilizar en otro hospital,
        debe adaptarse de forma adecuada.
        
        A tener en cuenta:
        -El mensaje no devuelve ni fecha ni hora de cita. Esto está mal, ya que
        la "query" permite un rango de fechas, y por lo tanto hace falta tambén el dia,
        además de la hora. Se espera en AIS.4
        
        -No viene codigo de servicio en PV1.10... creo que no afecta, vendrá agenda
        
        -El numero de cita viene en el SCH.2 en vez de en el SCH.1
        
        -El codigo de agenda viene en AIL.3.2, que no me parece muy correcto.
        No viene descripción.
        
        -No hay numero de peticion. No importará, ya viene episodio y cita (numicu y ncita)
        
        
        
        """
        #   extraer los campos
        schs = self.msg.segments('SCH')
        pids = self.msg.segments('PID')
        pv1s = self.msg.segments('PV1')
        rgss = self.msg.segments('RGS')
        aiss = self.msg.segments('AIS')
        ails = self.msg.segments('AIL')

        citas = []
        for idx, sch in enumerate(schs):

            paciente_id = pacientes_ids[idx]
            pid = pids[idx]
            pv1 = pv1s[idx]
            ais = aiss[idx]
            ail = ails[idx]
            nte = None
            
            identificadores = self._patient_identifier_list(pid, 3)
            cip =               identificadores['JHN']  #   cip
            id_unico =          identificadores['PN']   #   identificador único

            fecha_hora =                endosys.lib.hl7_wrapper.hl7val(ais.get(4.1))  #   XXX VACIO
            codigo_prestacion =         endosys.lib.hl7_wrapper.hl7val(ais.get(3.1))  #   HL7: Universal Service ID (identifier)
            descr_prestacion =          endosys.lib.hl7_wrapper.hl7val(ais.get(3.2))  #   HL7: Universal Service ID (text)
        
            codigo_servicio =           endosys.lib.hl7_wrapper.hl7val(pv1.get(10.1))   #   HL7: Hospital Service XXX VACIO
            numero_episodio =           endosys.lib.hl7_wrapper.hl7val(pv1.get(19.1))   #   HL7: Visit Number (NUMICU)
            medico_peticionario_cod =   endosys.lib.hl7_wrapper.hl7val(pv1.get(8.1))   #   HL7: Referring Doctor XXX VACIO
            medico_peticionario_descr = '%s, %s' % (pv1.get(8.2), pv1.get(8.3)) #   XXX VACIO

            # XXX NO VIENE NTE
            observaciones = None
            if nte:
                observaciones =         endosys.lib.hl7_wrapper.hl7val(nte.get(3.1))   #   HL7: Comment

            # El CHUS envía el ncita en SCH.2 (Filler), pero EndoSys normalmente lo espera
            # en SCH.1 (Placer). Para simplificar, de momento lo cogemos de SCH.2, pero por consistencia
            # sería mejor cogerlo de SCH.1 y hacer un mapeo en Mirth.
            numero_cita =               endosys.lib.hl7_wrapper.hl7val(sch.get(2.1))   #   HL7: Filler Appointment ID

            # El CHUS envía el codigo de agenda en AIL.3.2, lo cual es un poco raro,
            # pero igual que el caso anterior vamos a cogerlo de ahi para simplificar.
            # No viene descripción de agenda.
            codigo_agenda =             endosys.lib.hl7_wrapper.hl7val(ail.get(3.2))  #   HL7: Location Resource ID
            descr_agenda =              endosys.lib.hl7_wrapper.hl7val(endosys.lib.hl7_wrapper.HL7_ABSENT)    #   XXX NO VIENE
            
            numero_peticion =           endosys.lib.hl7_wrapper.hl7val(endosys.lib.hl7_wrapper.HL7_ABSENT)    #   XXX NO VIENE
            codigo_prioridad =          endosys.lib.hl7_wrapper.hl7val(endosys.lib.hl7_wrapper.HL7_ABSENT)    #   XXX NO VIENE
            filler_status_code =        endosys.lib.hl7_wrapper.hl7val(endosys.lib.hl7_wrapper.HL7_ABSENT)    #   XXX NO VIENE

            # No viene...
            servicio_peticionario_cod = endosys.lib.hl7_wrapper.hl7val(endosys.lib.hl7_wrapper.HL7_ABSENT)    #   XXX NO VIENE
            servicio_peticionario_descr =endosys.lib.hl7_wrapper.hl7val(endosys.lib.hl7_wrapper.HL7_ABSENT)   #   XXX NO VIENE
            
            print "paciente id:", paciente_id
            print "id_unico:", id_unico
            print "NCITA:", numero_cita

            def asignar_campos(cita):
                #      Valores fijos
                cita.duracion =             10
                cita.paciente_id =          paciente_id
                cita.ex.estado =            0

                #      Valores del mensaje, en "cita"
                if not endosys.lib.hl7_wrapper.hl7absent(fecha_hora):
                    cita.fecha =            endosys.lib.hl7_wrapper.hl7_to_date(fecha_hora, descartar_hora=True)
                if not endosys.lib.hl7_wrapper.hl7absent(fecha_hora):
                    cita.hora =             endosys.lib.hl7_wrapper.hl7_to_datetime(fecha_hora)
                if not endosys.lib.hl7_wrapper.hl7absent(codigo_prioridad):
                    cita.prioridad_id =     endosys.model.prioridades.prioridad_id_by_codigo(codigo_prioridad)

                if not endosys.lib.hl7_wrapper.hl7absent(observaciones) and observaciones is not None:
                    cita.observaciones =    observaciones

                cita.agenda_id = self._obtener_agenda_id(codigo_agenda, codigo_servicio)

                #      Valores del mensaje, en "cita_ex"
                if not endosys.lib.hl7_wrapper.hl7absent(id_unico):
                    cita.ex.idunico =                   id_unico
                if not endosys.lib.hl7_wrapper.hl7absent(cip):
                    cita.ex.cip =                       cip
                if not endosys.lib.hl7_wrapper.hl7absent(numero_peticion):
                    cita.ex.numero_peticion =           numero_peticion
                if not endosys.lib.hl7_wrapper.hl7absent(numero_cita):
                    cita.ex.numero_cita =               numero_cita
                if not endosys.lib.hl7_wrapper.hl7absent(numero_episodio):
                    cita.ex.numero_episodio =           numero_episodio
                if not endosys.lib.hl7_wrapper.hl7absent(codigo_prestacion):
                    cita.ex.prestacion_cod =            codigo_prestacion
                if not endosys.lib.hl7_wrapper.hl7absent(descr_prestacion):
                    cita.ex.prestacion_descr =          descr_prestacion
                if not endosys.lib.hl7_wrapper.hl7absent(codigo_agenda):
                    cita.ex.agenda_cod =                codigo_agenda
                if not endosys.lib.hl7_wrapper.hl7absent(descr_agenda):
                    cita.ex.agenda_descr =              descr_agenda
                if not endosys.lib.hl7_wrapper.hl7absent(codigo_servicio):
                    cita.ex.servicio_cod =              codigo_servicio
                if not endosys.lib.hl7_wrapper.hl7absent(medico_peticionario_cod):
                    cita.ex.medico_peticionario_cod =   medico_peticionario_cod
                if not endosys.lib.hl7_wrapper.hl7absent(medico_peticionario_descr):
                    cita.ex.medico_peticionario_descr = medico_peticionario_descr
                if not endosys.lib.hl7_wrapper.hl7absent(servicio_peticionario_cod):
                    cita.ex.servicio_peticionario_cod = servicio_peticionario_cod
                if not endosys.lib.hl7_wrapper.hl7absent(servicio_peticionario_descr):
                    cita.ex.servicio_peticionario_descr = servicio_peticionario_descr
                if not endosys.lib.hl7_wrapper.hl7absent(filler_status_code):
                    cita.ex.filler_status_code = filler_status_code

                # XXX: No se asigna nada a cita.ex.pv1, cita.ex.obr ni cita.ex.orc

            cita = endosys.lib.citas.get_by_id_ext(numero_cita, 'numero_cita')
            if not cita:
                cita = endosys.lib.citas.get_by_id_ext(numero_peticion, 'numero_peticion') # XXX: de momento nunca vendra nº peticion, siempre nº cita
            #    si no existia la cita, la crea.
            if not cita: cita = endosys.lib.citas.nueva_cita()
            #   si la cita existe recuperamos la cita antes de ser modificada par poder registrarla
            cita_updating = None
            if cita:
                cita_old = {}
                for campo in cita.c.keys():
                    cita_old[campo] = getattr(cita, campo)

                cita_updating = record(**cita_old)

            #     Luego la actualiza (la existente o nueva) con los datos recibidos.
            asignar_campos(cita)

            endosys.lib.citas.guardar_cita(cita, "sysadmin", self.ipaddress, cita_updating, self.id_hl7_log)

            citas.append(cita)

        return citas

            
    # EVENTOS HL7
    #   Estas funciones se ejecutan al recibir cada tipo un mensaje
    # ==============================================================================
    
    ######## ADT ########
    
    def procesar_ADT_A04(self):
        """
        Nuevo paciente.
        Funciona igual que el modificar paciente, como al consultarlo no lo
        encontrará siempre lo creará nuevo.
        """
        #paciente_id = self.procesar_paciente().id
        self.procesar_paciente()

    
    def procesar_ADT_A28(self):
        """
        Creación de historia clinica
        Lo tratamos como crear un paciente nuevo
        """
        #paciente_id = self.procesar_paciente().id
        self.procesar_paciente()

    
    def procesar_ADT_A08(self):
        """
        Modificar paciente.
        """
        self.procesar_paciente( config.get('HL7.MODIFICACION_PACIENTE.CREAR_SI_NO_EXISTE', '1') != '0' )

    
    def procesar_ADT_A31(self):
        """
        Actualizar datos demograficos
        lo tratamos como un modificar paciente
        """
        self.procesar_paciente( config.get('HL7.MODIFICACION_PACIENTE.CREAR_SI_NO_EXISTE', '1') != '0' )

    
    def procesar_ADT_A18(self):
        """
        Fusión de pacientes.
         Según interfaceware.com: Merge patient information
        """
        self.fusionar_paciente()

    
    def procesar_ADT_A34(self):
        """
        Fusión de pacientes por NHC.
         Según interfaceware.com: Merge patient information - patient ID only
        """
        self.fusionar_paciente()

    
    def procesar_ADT_A40(self):
        """
        Cambio de numero de historia.
        ojo, en algunos casos significa directamente FUSION (p.e. Huelva)
        se trata como un fusionar
        """
        self.fusionar_paciente()

    
    def procesar_ADT_A47(self):
        """
        Cambio de numero de NHC.
        para Huelva es este código (A47).
        (se trata como un fusionar)
        XXX ojo, tener en cuenta que SOLO se cambia el NHC, no el NUHSA/CIP!
        por lo tanto, revisar si el funcionamiento es correcto
        """
        self.fusionar_paciente()


    ######## SIU ########
    
    def procesar_SIU_S12(self):
        """
        nueva cita. procesar también el paciente.
        """
        #paciente_id = self.procesar_paciente().id
        #self.nueva_cita_SIU(paciente_id)
        paciente = self.procesar_paciente()
        if paciente:
            self.nueva_cita_SIU(paciente.id)


    def procesar_SIU_S13(self):
        """
        modificar cita. procesar también el paciente.
        Rebeca: el S13 sí que se podría tratar como [una cancelación y] una nueva cita.
        """
        #paciente_id = self.procesar_paciente().id
        #self.modificar_cita_SIU(paciente_id)

        paciente = self.procesar_paciente()
        if paciente:
            self.modificar_cita_SIU(paciente.id)


    def procesar_SIU_S14(self):
        """
        XXX falta implementar!
        Rebeca: El mensaje S14 sirve para modificar información administrativa o
                clínica de la cita. En ningún momento se modifica la prestación o
                servicio de la cita (incluido en el AIS) y la hora de la cita (TQ1).
                Entiendo que solamente tenéis que recuperar los valores de los otros
                segmentos que se pueden modificar.
        """
        #paciente_id = self.procesar_paciente().id
        #self.modificar_cita_SIU(paciente_id)   # XXX ojo, borrará algunos datos!
        paciente = self.procesar_paciente()
        if paciente:
            self.modificar_cita_SIU(paciente.id)

    
    def procesar_SIU_S15(self):
        """
        Cancelar cita
        """
        self.cancelar_cita_SIU()


    ######## ORM ########

    def procesar_ORM_O01(self):
        """
        Según el tipo de operación, crear una nueva cita o eliminarla.
        Si se crea una nueva cita, procesar también el paciente.
        (Hace la función del canal de Mirth: GESTIONARCITAS)
        """
    ##  orc = procesar_segmento_ORC( msg.segment('ORC') )
        orc = self.msg.segment('ORC')
        order_control = orc.get(1.1).upper()    # order_control es el tipo de operación
        if order_control == 'NW':
            # New order
            paciente = self.procesar_paciente()
            if paciente:
                self.nueva_cita_ORM(paciente.id)

        elif order_control == 'CA':
            # Cancel order
            self.cancelar_cita_ORM()
        elif order_control == 'XO':
            # update order
            paciente = self.procesar_paciente()
            if paciente:
                self.modificar_cita_ORM(paciente.id)

    
    ######## RSP ########

    def procesar_RSP_K22(self):
        return self.procesar_paciente(True, True)

    ######## SQR ########

    def procesar_SQR_S25(self):
        pacientes = self.procesar_paciente(True, True) # multiple pacientes = true
        print "pacientes:", pacientes
        if pacientes:        
            pacientes_ids = list(map(lambda p: p.id, pacientes))
            return self.nuevas_citas_SQR(pacientes_ids)
        else:
            return []

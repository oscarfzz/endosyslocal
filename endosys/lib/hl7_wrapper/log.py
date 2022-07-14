"""
"""

import logging
import datetime
from endosys.model.registro import Registro
from endosys.model import meta
from endosys.model.pacientes import Paciente
from endosys.model.hl7_logs import Hl7_log
import hl7
import socket
from pylons import config
from endosys.lib.misc import registro_by_id, formatea_valor
import endosys.lib.hl7_wrapper

log = logging.getLogger(__name__)


def nuevo_log_HL7(hl7Process):
    """
    (sender, tipo_mensaje, message_control_id, hl7_msg, nhc, cip, numero_cita, numero_peticion)
     id = identificador unico del registro
     fechahora = fecha en que se crea el registro
     sender = Sending aplication + sending facility
     tipo_mensaje =  tipo de mensaje HL7
     message_control_id = Identificador del mensaje HL7
    nhc
    cip
    numero_cita
    numero_peticion
    hl7_msg = MENSAJE HL7 completo
    """
    numero_cita = None
    numero_peticion = None

    #SI ES SIU
    if hl7Process.message_type == 'SIU':
        sch = hl7Process.msg.segment('SCH')
        numero_cita = endosys.lib.hl7_wrapper.hl7val(sch.get(1.1))
        numero_peticion = endosys.lib.hl7_wrapper.hl7val(sch.get(26.1))

    #SI ES ORM
    if hl7Process.message_type == 'ORM':
        orc = hl7Process.msg.segment('ORC')
        numero_peticion = endosys.lib.hl7_wrapper.hl7val(orc.get(2.1))

    count = hl7Process.msg.segment_count('PID')
    if count == 1:
        pid = hl7Process.msg.segment('PID')
        identificadores = hl7Process._patient_identifier_list(pid, 3)   # (cip, dni, nhc, ss)
        cip = identificadores['JHN']   #   cip
        id_unico = identificadores['PN']
        #nhc = pid_id_list[2].get(1)   #   nhc (es el valor que se asigna a "historia", antes era PID.2)
    elif count == 0:
        cip = '-'
        id_unico = '-'
    else:
        cip = '*'
        id_unico = '*'

    r = Hl7_log()
    r.fechahora = datetime.datetime.today()
    r.tipo_mensaje = hl7Process.message_type + hl7Process.trigger_event
    r.sender = hl7Process.msh.get(3.1).upper() + "-" + hl7Process.msh.get(4.1).upper()
    r.message_control_id = hl7Process.msh.get(9.1)
    r.hl7_msg = hl7Process.msg_original
    r.idunico = id_unico
    r.cip = cip
    r.numero_cita = numero_cita
    r.numero_peticion = numero_peticion
    r.canal = 'INPUT'

    meta.Session.save(r)
    meta.Session.commit()
    return r.id


def nuevo_log_HL7_output(msg_out, idunico = None, exploracion_id = None):
    msg = hl7.parse(msg_out)
    msh = msg.segment('MSH')
    message_type = msh.get(8.1).upper()
    trigger_event = msh.get(8.2).upper()
    fecha_hora = datetime.datetime.today()
    control_id = msh.get(9.1)
    sender =  msh.get(3.1).upper() + "-" + msh.get(4.1).upper()
    
    # Si es un ORUR01, comprobar si es incrustado. En ese caso truncarlo, pues puede
    # ocupar mucho e incluso dar error en algunos dbms.
    # La comprobación es mediante el campo OBX.2 (ED -> embeded).
    if (message_type + trigger_event) == "ORUR01":
        obx = msg.segment('OBX')
        if obx.get(2.1).upper() == "ED":
            msg_out = msg_out[:2048]

    r = Hl7_log()
    r.fechahora = fecha_hora
    r.tipo_mensaje = message_type + trigger_event
    r.sender = sender
    r.message_control_id =  control_id
    r.hl7_msg = msg_out
    #r.nhc = nhc
    r.idunico = idunico
    #r.cip = cip
    #r.numero_cita = numero_cita
    #r.numero_peticion = numero_peticion
    r.exploracion_id = exploracion_id
    r.canal = 'OUTPUT'
    r.estado_envio = 0

    meta.Session.save(r)
    meta.Session.commit()
    return r.id


def cambio_estado_log_HL7(id_log, estado):
    reg_log_hl7 = registro_by_id(Hl7_log, id_log)
    reg_log_hl7.estado_envio = estado
    meta.Session.update(reg_log_hl7)
    meta.Session.commit()

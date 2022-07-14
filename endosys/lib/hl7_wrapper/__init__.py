import extend_hl7
import logging
import datetime
from endosys.lib.misc import valid_date_range
import hl7

# "log" genera conflicto con el modulo endosys.lib.hl7_wrapper.log, por eso se renombra a "log_"
log_ = logging.getLogger(__name__)

FIELD_SEPARATOR =           "|"
FIELD_REPEAT_SEPARATOR =    "~"
COMPONENT_SEPARATOR =       "^"
ESCAPE_CHARACTER =          "\\"
SUBCOMPONENT_SEPARATOR =    "&"

HL7_NULL =                  '""'  # significa que el campo tiene valor NULL, y asi se tiene que procesar
HL7_ABSENT =                ''    # significa que no se indica ningún valor para ese campo, y por lo tanto no se tiene que procesar

def hl7absent(v):
    """
    indica si el valor pasado como parámetro (que se ha extraido de un mensaje
    HL7) es HL7_ABSENT
    """
    return v == HL7_ABSENT


def hl7val(v):
    """
    retorna el mismo valor pasado como parámetro (que se ha extraido de un mensaje
    HL7) excepto si es NULL (""), en ese caso devuelve None
    """
    if v == HL7_NULL:
        return None
    return v


def hl7_to_date(d, **kwargs):
    """
    devuelve un datetime.date, o HL7_ABSENT si no es válida.
    parámetros adicinales:
        descartar_hora  True/False  Si es True, en el caso de que la fecha pasada
                                    tenga también la hora, ésta se descartara. Si
                                    es False, en este caso devolverá HL7_ABSENT. (por
                                    defecto = False)
        check_range  True/False  Comprueba que la fecha esté en el rango permitido
                                    por EndoTools. Si no es asi, devuelve HL7_ABSENT.
                                    (por defecto = True)
    """
    if d in (HL7_NULL, HL7_ABSENT, None): return d
    try:
        if kwargs.get('descartar_hora', False):
            d = d[0:8]
        f = datetime.datetime.strptime(d, '%Y%m%d')
        if kwargs.get('check_range', True) and not valid_date_range(f):
            return HL7_ABSENT
        return f.date()
    except Exception as e:
        log_.error(e)
        return HL7_ABSENT

        
def hl7_to_datetime(d, **kwargs):
    """
    devuelve un datetime.datetime, o HL7_ABSENT si no es válida
    parámetros adicinales:
        check_range  True/False  Comprueba que la fecha esté en el rango permitido
                                    por EndoTools. Si no es asi, devuelve HL7_ABSENT.
                                    (por defecto = True)
    """
    if d in (HL7_NULL, HL7_ABSENT, None): return d
    try:
        d = d[0:14]   # descartamos lo que pueda venir a continuación (p.e. milisegundos)
        if len(d) == 14: # con horas, minutos y segundos
            f = datetime.datetime.strptime(d, '%Y%m%d%H%M%S')
        elif len(d) == 12: # solo horas y minutos
            f = datetime.datetime.strptime(d, '%Y%m%d%H%M')
        else: return HL7_ABSENT
        if kwargs.get('check_range', True) and not valid_date_range(f):
            return HL7_ABSENT
        return f
    except Exception as e:
        log_.error(e)
        return HL7_ABSENT        


def date_to_hl7(d):
    """
    Devuelve un str a partir de un datetime.date, solo con fecha.
    Si la fecha es nula, devuelve cadena vacía.
    """
    if d:
        return d.strftime('%Y%m%d')
    else:
        return ""


def datetime_to_hl7(d, ms=False):
    """
    devuelve un str a partir de un datetime.datetime, con fecha y hora.
    Si ms es True, se incluyen los microsegundos.
    """
    if d:
        if ms:
            return d.strftime('%Y%m%d%H%M%S%f')
        else:
            return d.strftime('%Y%m%d%H%M%S')
    else:
        return None

        
def to_sex(v):
    """
    Convierte el valor representando el Sexo tal como lo almacena EndoTools en
    el modelo al formato usado en HL7.
    
    Tabla 0001: Administrative Sex
        A   Ambiguous
        F   Female
        M   Male
        N   Not applicable
        O   Other
        U   Unknown
    
    En resumen:
        1 ->    M
        0 ->    F
        None -> U
        otro -> O
    """
    if v is None:   return "U"
    elif v == 1:    return "M"
    elif v == 0:    return "F"
    else:           return "O"

    
def from_sex(sex):
    """
    Al revés que to_sex(), convierte el formato de HL7 al usado por EndoTools
    en el modelo.

    En resumen:
    
        M ->    1
        F ->    0
        otro -> None
    """
    if sex == "M":      return 1
    elif sex == "F":    return 0
    else:               return None
    

def to_str(v):
    """
    Convierte un valor al formato usado en HL7. En el caso de que sea None,
    devuelve cadena vacía, y en otro caso devuelve str(v).
    
    En resumen:
        None -> ""
        otro -> str(v)
        
    NOTA: Cuidado al usarla, si v es Unicode puede dar error.
    """
    if v is None:   return ""
    else:           return str(v)


def CX(id_number, assigning_authority, id_type_code):
    """
    Devuelve una cadena representando un tipo CX (Extended Composite Id With
    Check Digit). Este es el tipo del campo repetido PID.3.
    
    id_number           Es el valor del identificador.
    assigning_authority Usado solo en el caso del PI (NHC), es el código del
                        centro.
    id_type_code        Es el código del tipo de identificador.
    
    
        SEQ  LENGTH DT  OPT TBL #   NAME
      * CX.1    0   ST  R           Id Number
        CX.2    0   ST  O           Identifier Check Digit
        CX.3    3   ID  O   0061    Check Digit Scheme
      * CX.4    0   HD  C   0363    Assigning Authority
      * CX.5    5   ID  R   0203    Identifier Type Code
        CX.6    0   HD  O           Assigning Facility    
        
    Table 0203: Identifier Type
    
        JHN     Jurisdictional health number (Canada)
        NNxxx   National Person Identifier where the xxx is the ISO table 3166
                3-character (alphabetic) country code (NNESP para España)
        PN      Person number
        SS      Social Security number
        
    El uso en EndoTools Web de los códigos de tipo de id es el siguiente:
    
        JHN     CIP del paciente.
        NNESP   DNI del paciente (o NIE).
        PN      id. único - puede ser el NHC o algún otro identificador único
                en el sistema.
        SS      número de afiliación de la SS.
        PI      NHC del paciente en un centro.
    
    Sobre Assigning Authority:  Es un campo del tipo HD (Hierarchic Designator),
    pero parece que puede constar sólo de un componente. En el caso de EndoTools
    Web, es el código del centro.
    """
    return "%s^^^%s^%s" % (to_str(id_number), to_str(assigning_authority), to_str(id_type_code))

    
def get_patient_identifier_list(field):
    """
    Devolver un dict con las keys y los valores del campo de tipo Listado de
    Identificadores de Paciente, como por ejemplo un PID.3 o un MRG.1.
    
    Cada key es uno de los "Identifier Type Code" soportados por EndoTools Web,
    y cada valor es el "Id Number" que tiene asignado.
    
    Se devuelven siempre todos los tipos de identificadores, con su
    correspodiente valor, o HL7_ABSENT / HL7_NULL.
    
    Los códigos de tipo de id en EndoTools Web son:
    
        JHN     CIP del paciente.
        NNESP   DNI del paciente (o NIE).
        PN      id. único - puede ser el NHC o algún otro identificador único
                en el sistema.
        SS      número de afiliación de la SS.
        PI      NHC del paciente en un centro.
        
    En el caso de PI, pueden haber varios, uno por cada centro. El código del
    centro se indica en el "Assigning Authority", y se devolverá concatenado
    en las keys, separado por un "_". Por ejemplo:

        {
            ...
            "PI_CENTROA": NHC del centro A,
            "PI_CENTROB": NHC del centro B,
            ...
        }
    
    El formato de cada repetición debería ser:

        Id Number^^^Assigning Authority^Identifier Type Code

        
    parámetros de la función:
        field   El campo, de tipo hl7.Field
        

    NOTAS:
    - El orden de recepción de cada identificador, y el de devolución en el dict
    no es relevante ni se debe tener en cuenta.
    - Esta función debería sustituir a Hl7Process._patient_identifier_list.
    """

    # Reconstruir el campo y separar las repeticiones en una lista.
    # El objeto hl7.Field ya tiene la funcion _unicode(), que lo vuelve a
    # reconstruir a una cadena.
    idlist = unicode(field).split(FIELD_REPEAT_SEPARATOR)
    result = {}
    for cx in idlist:
        id_number =             hl7.Field(COMPONENT_SEPARATOR, cx.split(COMPONENT_SEPARATOR))[0]
        assigning_authority =   hl7.Field(COMPONENT_SEPARATOR, cx.split(COMPONENT_SEPARATOR))[3]
        id_type_code =          hl7.Field(COMPONENT_SEPARATOR, cx.split(COMPONENT_SEPARATOR))[4]
        if id_type_code == 'PI':
            # Si es un NHC, concatenar el centro (en "Assigning Authority")
            result["%s_%s" % (id_type_code, assigning_authority)] = id_number
        else:
            result[id_type_code] = id_number

    return result


def get_nhc_centro(d, codigo_centro):
    """
    Obtiene el NHC para un centro concreto del dict devuelto por
    get_patient_identifier_list().
    Si no lo encuentra devuelve None.
    
    Usado por Hl7Process.fusionar_paciente()
    """
    nhc = None
    for item in d:
        if item[:2] == "PI":
            id_type_code, assigning_authority = item.split("_")
            if assigning_authority == codigo_centro:
                nhc = d[item]
                break
    return nhc


def get_idunico(d):
    """
    Obtiene el idunico del dict devuelto por get_patient_identifier_list().
    Si no lo encuentra devuelve None.
    
    Usado por Hl7Process.fusionar_paciente()
    """
    return d.get("PN", None)

    
def paciente_from_PID(paciente, pid):
    """
    Rellena un registro de Paciente a partir de la información de un segmento
    PID.

    NOTA: No rellena los NHCs de cada centro!!! pero sí el resto de ids, como
    el idunico, DNI, CIP y num SS.
    
    parámetros de la función:
        paciente    El registro de Paciente (nuevo o existente)
        pid         El segmento PID, de tipo hl7.Segment
    
    NOTA: Esta función deberí sustituir parte de Hl7Process.procesar_paciente(),
    la de la subfunción asignar_campos().
    """
    patient_identifier_list = get_patient_identifier_list(pid[3])
    id_unico =          patient_identifier_list.get('PN', None)
    cip =               patient_identifier_list.get('JHN', None)
    dni =               patient_identifier_list.get('NNESP', None)
    numss =             patient_identifier_list.get('SS', None)
    nombre =            pid.get(5.2)
    apellido1 =         pid.get(5.1)
    apellido2 =         pid.get(6.1)
    sexo =              from_sex( pid.get(8.1).upper() )
    fecha_nacimiento =  hl7_to_date(pid.get(7.1), descartar_hora=True)
    direccion =         pid.get(11.1)
    poblacion =         pid.get(11.3)
    provincia =         pid.get(11.4)
    codigoPostal =      pid.get(11.5)
    telefono1 =         pid.get(14.1)
    telefono2 =         pid.get(13.1)
    numero_expediente = pid.get(4.1) #nuevo campo pedido por candelaria, con prevision a que se utilice en mas sitios
            
    if not hl7absent(id_unico):        paciente.idunico =          hl7val(id_unico)
    if not hl7absent(cip):             paciente.CIP =              hl7val(cip)
    if not hl7absent(dni):             paciente.DNI =              hl7val(dni)
    if not hl7absent(numss):           paciente.numAfiliacion =    hl7val(numss)
    if not hl7absent(nombre):          paciente.nombre =           hl7val(nombre)
    if not hl7absent(apellido1):       paciente.apellido1 =        hl7val(apellido1)
    if not hl7absent(apellido2):       paciente.apellido2 =        hl7val(apellido2)
    if not hl7absent(sexo):            paciente.sexo =             hl7val(sexo)
    if not hl7absent(fecha_nacimiento): paciente.fechaNacimiento = hl7val(fecha_nacimiento)
    if not hl7absent(direccion):       paciente.direccion =        hl7val(direccion)

    if not hl7absent(poblacion):
        if config.get('INTEGRACION.POBLACIONES', '0') == '1':
            paciente.poblacion =        poblacion_nombre_by_codigo(hl7val(poblacion))
        else:
            paciente.poblacion =        hl7val(poblacion)

    if not hl7absent(provincia):
        if config.get('INTEGRACION.PROVINCIAS', '0') == '1':
            paciente.provincia =        provincia_nombre_by_codigo(hl7val(provincia))
        else:
            paciente.provincia =        hl7val(provincia)

    if not hl7absent(codigoPostal):    paciente.codigoPostal =      hl7val(codigoPostal)
    if not hl7absent(telefono1):       paciente.telefono1 =         hl7val(telefono1)
    if not hl7absent(telefono2):       paciente.telefono2 =         hl7val(telefono2)
    if not hl7absent(numero_expediente): paciente.numero_expediente =  hl7val(numero_expediente)

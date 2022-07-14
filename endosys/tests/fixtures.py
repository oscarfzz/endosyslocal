import string
import random
import datetime
import json
import os

from pylons import config

from endosys.model import meta
from endosys.model import Centro, Servicio, Sala, Agenda, HorarioAgenda, \
                            TipoExploracion, Formulario


""" Este archivo sirva para hacer un preload de data """

def random_names():
    
    string.ascii_letters=u'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
    string_generated = u''
    for r in range(3):
        string_generated += random.choice(string.ascii_letters)
    return string_generated

def create_facility_basic(random_facility):

    centro = Centro()
    centro.codigo = u'FAC_CODE_' + random_facility
    centro.nombre = u'Hospital ' + random_facility
    meta.Session.save(centro)
    meta.Session.flush()

    sala = Sala()
    sala.nombre = u'Sala 1 - ' + random_facility
    sala.centro_id = centro.id
    meta.Session.save(sala)
    meta.Session.flush()

    sala = Sala()
    sala.nombre = u'Sala 2 - ' + random_facility
    sala.centro_id = centro.id
    meta.Session.save(sala)
    meta.Session.flush()

    sala = Sala()
    sala.nombre = u'Sala 3 - ' + random_facility
    sala.centro_id = centro.id
    meta.Session.save(sala)
    meta.Session.flush()

    # Digestivo
    servicio = Servicio()
    servicio.codigo = u'DIG_' + random_facility
    servicio.nombre = u'Digestivo ' + random_facility
    servicio.centro_id = centro.id
    meta.Session.save(servicio)
    meta.Session.flush()

    agenda = Agenda()
    agenda.codigo = u'AG_DIG_' +  random_facility
    agenda.nombre = u'AG Digestivo ' + random_facility
    agenda.servicio_id = servicio.id
    meta.Session.save(agenda)
    meta.Session.flush()

    # horario 7/24
    for dia_semana in range(0, 7):
        horario = HorarioAgenda()
        horario.agenda_id = agenda.id
        horario.hora_ini = datetime.datetime.combine(datetime.date.today(), datetime.time(8, 0, 0))
        horario.hora_fin = datetime.datetime.combine(datetime.date.today(), datetime.time(20, 0, 0))
        horario.dia_semana = dia_semana
        meta.Session.save(horario)
        meta.Session.flush()

    # Neumologia
    servicio = Servicio()
    servicio.codigo = u'NML_' +  random_facility
    servicio.nombre = u'Neumologia ' +  random_facility
    servicio.centro_id = centro.id
    meta.Session.save(servicio)
    meta.Session.flush()

    agenda = Agenda()
    agenda.codigo = u'AG_NML_' +  random_facility
    agenda.nombre = u'Neumologia ' + random_facility
    agenda.servicio_id = servicio.id
    meta.Session.save(agenda)
    meta.Session.flush()

    # horario 7/24
    for dia_semana in range(0, 7):
        horario = HorarioAgenda()
        horario.agenda_id = agenda.id
        horario.hora_ini = datetime.datetime.combine(datetime.date.today(), datetime.time(0, 0, 0))
        horario.hora_fin = datetime.datetime.combine(datetime.date.today(), datetime.time(23, 59, 59))
        horario.dia_semana = dia_semana
        meta.Session.save(horario)
        meta.Session.flush()

def create_basic_data():
    # Crea dos centros con sus servicios
    create_facility_basic(random_names())
    create_facility_basic(random_names())

    """
    Para crear los archivos de fixture, simplemente ir al navegador y 
    hacer http://127.0.0.1:8081/rest/tiposExploracion.json
    y guardarlo en un archivo.
    """
    path_fixture_tipos_exploracion = os.path.join(config.paths['custom'], 'fixtures', 'tipos_exploracion.json')
    import_data_from_json(TipoExploracion, path_fixture_tipos_exploracion)

    path_fixture_formularios = os.path.join(config.paths['custom'], 'fixtures', 'formularios.json')
    import_data_from_json(Formulario, path_fixture_formularios)

def import_data_from_json(modelclass, path_json):
    
    if not os.path.exists(path_json):
        raise Exception("Ruta de JSON no existe" + path_json)

    data = None
    with open(path_json) as f:
        data = json.load(f)

    #from nose.tools import set_trace; set_trace()
    # recorre el dict que viene del json, 
    # crea el objecto del modelclass, ej: TipoExploracion
    # si el atributo del diccionario coincide con un atributo 
    # de la clase entonces lo agrega como valor
    # finalmente guarda el valor.
    for d in data:
        d_obj = modelclass()
        for key, value in d.iteritems():
            # recorre los keys, value del dict y lo agrega al obj tipoexpl
            if hasattr(d_obj, key):
                setattr(d_obj, key, value)
        meta.Session.save(d_obj)
        meta.Session.flush()

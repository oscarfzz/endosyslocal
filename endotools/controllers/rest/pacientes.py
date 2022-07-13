import logging

from xml.etree.ElementTree import Element, SubElement, tostring
from pylons import config
from pylons.i18n import _
from authkit.authorize.pylons_adaptors import authorize
from authkit.permissions import RemoteUser, ValidAuthKitUser, UserIn, HasAuthKitRole, And
from sqlalchemy.sql import and_, or_, not_

from endotools.model import meta
from endotools.model.pacientes import Paciente, Rel_Pacientes_Centros
from endotools.lib.genericREST import *
from endotools.lib.misc import *
from endotools.lib.usuarios.seguridad import roles
from endotools.lib.plugins.base import *
from endotools.config.plugins import pluginPacientes
from endotools.lib.pacientes import get_by_id
import endotools.lib.registro as registro
import endotools.lib.hl7_wrapper.sending

log = logging.getLogger(__name__)

class PacientesController(GenericRESTController):
    # To properly map this controller, ensure your config/routing.py file has
    # a resource setup:
    #    map.resource('paciente', 'pacientes', controller='rest/pacientes',
    #        path_prefix='/rest', name_prefix='rest_')

    def __init__(self, *args, **kwargs):
        GenericRESTController.__init__(self, *args, **kwargs)
        self.tabla = Paciente
        self.tabla_centros = Rel_Pacientes_Centros
        self.nombre_recurso = 'paciente'
        self.nombre_recursos = 'pacientes'
        self.campos_index = ('id', 'idunico', 'CIP', 'DNI', 'nombre', 'apellido1', 'apellido2', 'deshabilitado', 'aseguradora_id', 'aseguradora', 'fechaNacimiento', 'telefono1', 'telefono2')
        self.like_filter = ('dni', 'nombre', 'apellido1', 'apellido2', 'poblacion', 'provincia')
        self.paciente_updating = None

    def _construir_plugin_xml_show(self, paciente, root):
        SubElement(root, 'idunico').text = formatea_valor( paciente.idunico )
        SubElement(root, 'DNI').text = formatea_valor( paciente.DNI )
        SubElement(root, 'CIP').text = formatea_valor( paciente.CIP )
        SubElement(root, 'nombre').text = formatea_valor( paciente.nombre )
        SubElement(root, 'apellido1').text = formatea_valor( paciente.apellido1 )
        SubElement(root, 'apellido2').text = formatea_valor( paciente.apellido2 )
        SubElement(root, 'sexo').text = formatea_valor( paciente.sexo )
        SubElement(root, 'fechaNacimiento').text = formatea_valor( paciente.fechaNacimiento )
        SubElement(root, 'direccion').text = formatea_valor( paciente.direccion )
        SubElement(root, 'poblacion').text = formatea_valor( paciente.poblacion )
        SubElement(root, 'provincia').text = formatea_valor( paciente.provincia )
        SubElement(root, 'codigoPostal').text = formatea_valor( paciente.codigoPostal )
        if paciente.aseguradora != None:
            e = SubElement(root, 'aseguradora', {
                    'id': formatea_valor( paciente.aseguradora.id ) })
            SubElement(e, 'nombre').text = formatea_valor( paciente.aseguradora.nombre )
        SubElement(root, 'numAfiliacion').text = formatea_valor( paciente.numAfiliacion )
        SubElement(root, 'telefono1').text = formatea_valor( paciente.telefono1 )
        SubElement(root, 'telefono2').text = formatea_valor( paciente.telefono2 )
        SubElement(root, 'comentarios').text = formatea_valor( paciente.comentarios )
        SubElement(root, 'numero_expediente').text = formatea_valor( paciente.numero_expediente )
        SubElement(root, 'deshabilitado').text = formatea_valor( paciente.deshabilitado )

    def _filtrar_index(self, query, format= None):
        """
        el campo "deshabilitado" se trata asi:
            si no viene, no se filtra
            si viene como "0", se muestran los pacientes con deshabilitado=false o NULL
            si viene como "1", se muestran los pacientes con deshabilitado=true
        """

        deshabilitado = request.params.get('deshabilitado', None)
        if deshabilitado == '0':
            query = query.filter(or_(Paciente.deshabilitado == None, Paciente.deshabilitado == False))
        elif deshabilitado == '1':
            query = query.filter(Paciente.deshabilitado == True)

        centros = request.params.get('centros', None)
        if centros is not None:
            centro_id = centros.split(":")[0]
            nhc_centro = ":".join(centros.split(":")[1:])
            if nhc_centro:
                query = query.filter(and_(Rel_Pacientes_Centros.paciente_id == Paciente.id,
                                          Rel_Pacientes_Centros.centro_id == centro_id,
                                          Rel_Pacientes_Centros.nhc == nhc_centro))

        return query

    def _return_doIndex(self, pacientes, data, format):
        """
        amplia la info del paciente con los nhc de los centros
        """
        if pacientes is not None:
            for paciente in pacientes:
                a = filter(lambda i: str(i['id']) == str(paciente.id), data)
                if len(a) > 0:
                    paciente_el = a[0]
                    # AGENDAS
                    paciente_el['centros'] = []
                    for centro in paciente.centros:
                        paciente_el['centros'].append({
                                    'id': formatea_valor(centro.centro_id),
                                    'nhc': formatea_valor(centro.nhc)
                        })
        return data

    def _doIndex(self, params, format='xml'):
        if not pluginPacientes:
            if config.get('HL7.CONSULTA_PACIENTES.ACTIVO', '0') == '1':
                if(params.has_key('idunico')):
                    #consulta de paciente via HL7
                    pacientes =  endotools.lib.hl7_wrapper.sending.consulta_pacientes(params['idunico'])
                    data = []
                    for registro in pacientes:
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

                    return GenericRESTController.respuesta_doIndex(self, pacientes, data, format)
                else:
                    return GenericRESTController._doIndex(self, params, format)

            else:
                return GenericRESTController._doIndex(self, params, format)
        else:
            try:
                # ATENCION: Agregar el parametro deshabilitado en el index del plugin,
                #           sino fallara
                #           PARA QUE FILTRE LOS DESHABILITADOS SE TIENE QUE IMPLEMENTAR EN EL PLUGIN
                deshabilitado = request.params.get('deshabilitado', None)
                pacientes = pluginPacientes.index(params, deshabilitado)
            except PluginException, e:
                log.error(e)
                abort_xml(e.http_status, str(e))
            except Exception, e:
                log.error(e)
                abort_xml(500, _('Ha ocurrido un error cargando los pacientes (%s)') % e)#IDIOMAOK

            '''
            Este era el filtro anterior que filtraba cuando ya tenia los resultados y
            no con el filter del sqlalchemy.
            deshabilitado = request.params.get('deshabilitado', None)
            def _filtro(p):
                if deshabilitado == '0':
                    return (p.deshabilitado == False) or (p.deshabilitado == None)
                elif deshabilitado == '1':
                    return p.deshabilitado == True
                else:
                    return True
            pacientes = filter(_filtro, pacientes)
            '''

            # si no se encuentra ningun registro, devolver error 404
            if len(pacientes) == 0: abort_xml(404, _(u'No se ha encontrado ningún paciente'), 2)#IDIOMAOK

            # Convertir a formato compatible con GenericREST
            pacientes = self._crear_data(pacientes, format, valid_fields=self.campos_index)
            pacientes = self._return_doIndex(None, pacientes, format)
            return self.respuesta_doIndex(None, pacientes, format)

    @conditional_authorize(RemoteUser())
    def index(self, format='xml'):
        """ el campo "deshabilitado" se trata posteriormente en _filtrar_index()
        """
        p = request.params
        if 'deshabilitado' in p: del p['deshabilitado']
        if 'centros' in p: del p['centros']
        return self._doIndex(p, format)

    @authorize(RemoteUser())
    def show(self, id, format='xml'):
        if not pluginPacientes:
            # REGISTRAR: la consulta del paciente
            username = request.environ.get('REMOTE_USER', registro.DEFAULT_REMOTE_USER)
            ipaddress = obtener_request_ip(request)
            registro.nuevo_registro_paciente(username, ipaddress, get_by_id(id), registro.eventos.mostrar,
                                    registro.res.paciente, '', None, None)


            paciente = get_by_id(id)
            paciente = self._crear_data(paciente, format, valid_fields=self.campos_show)
            q = meta.Session.query(Rel_Pacientes_Centros).filter(Rel_Pacientes_Centros.paciente_id == id)
            paciente["centros"] = []
            centros = q.all()
            for centro in centros:
                paciente["centros"].append({
                    'id': formatea_valor(centro.centro_id),
                    'nhc': formatea_valor(centro.nhc)})
            self._return_show(None, paciente)
            return self.respuesta_show(None, paciente, format)

        else:
            try:
                paciente = pluginPacientes.show(id)
            except PluginException, e:
                log.error(e)
                abort_xml(e.http_status, str(e))
            except Exception, e:
                log.error(e)
                abort_xml(500, _('Ha ocurrido un error cargando el paciente (%s)') % e)#IDIOMAOK

            if not paciente: abort_xml(404, _('No se ha encontrado el paciente'), 2)#IDIOMAOK

            # Convertir a formato compatible con GenericREST
            paciente = self._crear_data(paciente, format, valid_fields=self.campos_show)
            self._return_show(None, paciente)
            return self.respuesta_show(None, paciente, format)

    def _updated(self, paciente_updated):
        # Creamos o modificamos el identificador del paciente para el centro
        if "centros" in request.params:
            centros = request.params["centros"]
            centro_id = centros.split(':')[0]
            nhc = ":".join(centros.split(':')[1:])
            found = False
            for centro in paciente_updated.centros:
                if centro.centro_id == int(centro_id):
                    centro.nhc = nhc
                    found = True
                    break
            if not found:
                centro = Rel_Pacientes_Centros()
                paciente_updated.centros.append(centro)
                centro.paciente_id = paciente_updated.id
                centro.centro_id = int(centro_id)
                centro.nhc = nhc
            meta.Session.commit()

        # REGISTRAR: la modificacion del paciente
        username = request.environ.get('REMOTE_USER', registro.DEFAULT_REMOTE_USER)
        ipaddress = obtener_request_ip(request)
        registro.nuevo_registro_paciente(username, ipaddress, self.paciente_updating, registro.eventos.modificar,
                                registro.res.paciente, 'Datos', self.paciente_updating, paciente_updated)

        return GenericRESTController._updated(self, paciente_updated)


    @authorize(HasAuthKitRole([roles.crear_modif_pacientes]))
    def update(self, id):
        if not pluginPacientes:

            if 'idunico' in request.params:
                if request.params['idunico'] == '':
                    error_msg = _(u'No se puede asignar un identificador')#IDIOMAOK
                    generic_abort("json", 400, error_msg)

            # no permitir modificar pacientes deshabilitados
            paciente = get_by_id(id)
            if paciente.deshabilitado:
                abort_json(400, _(u'El paciente indicado está deshabilitado. No se puede modificar'))#IDIOMAOK



            error_msg = self._check_identificador_existe(request.params,id)
            if error_msg:    
                abort_json(400,error_msg)

            # Mejor asi, porque:
            # - el objeto Paciente(), que es de sql alchemy, representa una fila de bbdd, y al
            #   instanciarlo se cree que quieres hacer un INSERT
            # - __setattr__ y __getattribute__ son métodos internos de python, y es mejor
            #   usar las funciones globales setattr() y getattr().
            params = {}
            for campo in paciente.c.keys():
                params[campo] = getattr(paciente, campo)
            #import pdb; pdb.set_trace()
            params.update({"centros": []})
            for centro in paciente.centros:
                params["centros"].append({'centro_id': centro.centro_id, 'nhc': centro.nhc})

            exclude = []
            if int(config.get('PACIENTE.NHC_AUTOMATICO', 0)):
                exclude.append("idunico")

            exclude.append("centros")

            self.paciente_updating = record(**params)

            return GenericRESTController.update(self, id, exclude)
        else:
            # si devuelve un codigo de error, devolver como error http
            # (de momento los plugins de pacientes devuelven los errores como codigos http, para facilitar la tarea)
            #r = pluginPacientes.update(id)
            #if r != 200: abort(r)
            # XXX falta generar el objeto Paciente con los parametros!
            try:
                pluginPacientes.update(id, None)
            except PluginException, e:
                log.error(e)
                abort_xml(e.http_status, str(e))
            except Exception, e:
                log.error(e)
                abort_xml(500, _('Ha ocurrido un error modificando el paciente (%s)') % e)#IDIOMAOK


    def _created(self, registro_paciente):
        # Funcionalidad NHC_AUTOMATICO
        # Si clave NHC_AUTOMATICO = 1, la historia es = id autoincremental. Solo funciona afecta al campo Historia
        if int(config.get('PACIENTE.NHC_AUTOMATICO', 0)):
            idunico = registro_paciente.id
            registro_paciente.idunico = idunico
            meta.Session.update(registro_paciente)
            meta.Session.commit()
            # Nota NHC_AUTOMATICO: no se controla que el numero de historia exista, por lo tanto
            # si se hizo mal la migracion de datos antiguos quedaran 2 registros con la misma historia.

        # Creamos el identificador del paciente para el centro
        if "centros" in request.params:
            centros = request.params["centros"]
            centro_id = centros.split(':')[0]
            nhc = ":".join(centros.split(':')[1:])
            centro = Rel_Pacientes_Centros()
            registro_paciente.centros.append(centro)
            centro.centro_id = int(centro_id)
            centro.nhc = nhc
            meta.Session.commit()


        # REGISTRAR: la creación del paciente
        username = request.environ.get('REMOTE_USER', registro.DEFAULT_REMOTE_USER)
        ipaddress = obtener_request_ip(request)
        registro.nuevo_registro_paciente(username, ipaddress, registro_paciente, registro.eventos.crear,
                                registro.res.paciente, 'Datos', None, registro_paciente)
        log.debug( 'Paciente creado en REST/pacientes')

        return GenericRESTController._created(self, registro_paciente)


    def _deleted(self, registro_paciente):

        # REGISTRAR: la eliminacio del paciente
        username = request.environ.get('REMOTE_USER', registro.DEFAULT_REMOTE_USER)
        ipaddress = obtener_request_ip(request)
        registro.nuevo_registro_paciente(username, ipaddress, registro_paciente, registro.eventos.eliminar,
                                registro.res.paciente, 'Datos', None, None)

        return GenericRESTController._deleted(self, registro_paciente)

    def _doCreate(self, params, format='xml'):
        if not pluginPacientes:

            # Comprobar que no exista el paciente, ya sea por Nº de idunico o por NHC
            # Excluye a los deshabilitados
            if not int(config.get('PACIENTE.NHC_AUTOMATICO', 0)): 
                # no hace la comprobacion si el nhc es automatico
                error_msg = self._check_identificador_existe(params)
                
                # Segun que formato se tenga que devolver, se envia el error en xml o json 
                if error_msg:
                    generic_abort(format, 400, error_msg)

                if 'idunico' in params:
                    if params['idunico'] == '':
                        error_msg = _(u'No se puede crear un paciente con identificador vacio')#IDIOMAOK
                        generic_abort(format, 400, error_msg)

            # NHC Automatico - Temporalmente asigna una cadena generica porque no es nulleable.
            # Luego en el _created le asigna el id autoincremental
            if int(config.get('PACIENTE.NHC_AUTOMATICO', 0)):
                params["idunico"] = "NHC_AUTOMATICO"

            # va al genericrest a crear el paciente.
            return GenericRESTController._doCreate(self, params, format)
        else:
            # uso de plugins
            try:
                paciente = pluginPacientes.create(params)
            except PluginException, e:
                log.error(e)
                abort_xml(e.http_status, str(e))
            except Exception, e:
                log.error(e)
                abort_xml(500, _('Ha ocurrido un error creando el paciente (%s)') % e)#IDIOMAOK

            # Devolver como xml o json
            data = { 'id': formatea_valor(paciente.id) }
            response.status_code = 201
            if format == 'xml':
                response.content_type = "text/xml"
                return tostring(obj_to_xml(data, self.nombre_recurso))
            elif format == 'json':
                response.content_type = 'application/json'
                return simplejson.dumps(data)

    def _check_identificador_existe(self, params, id_edit=None):
        error_msg = None                
        if ('IDUNICO' in config.get('IDENTIFICADORES_PACIENTE', 'idunico').upper()) and ('idunico' in params):
            q = meta.Session.query(self.tabla)
            q = q.filter(or_(self.tabla.deshabilitado == False, self.tabla.deshabilitado == None))
            q = q.filter( self.tabla.idunico == params['idunico'] )

            if id_edit:
                # Si es una edicion tiene que excluirse a si mismo
                q = q.filter( self.tabla.id != id_edit)

            if q.count() > 0:
                error_msg = _(u'Ya existe un paciente con el identificador: %s') % params['idunico']#IDIOMAOK
                
        if ('NHC' in config.get('IDENTIFICADORES_PACIENTE', 'idunico').upper()) and ('centros' in params):
            centros = request.params["centros"]
            centro_id = centros.split(':')[0]
            nhc = ":".join(centros.split(':')[1:])
            q = meta.Session.query(Rel_Pacientes_Centros)
            q = q.filter(and_(Rel_Pacientes_Centros.centro_id == centro_id,
                              Rel_Pacientes_Centros.nhc == nhc))

            if id_edit:
                # Si es una edicion tiene que excluirse a si mismo
                q = q.filter( Rel_Pacientes_Centros.paciente_id != id_edit)

            if q.count() > 0:
                error_msg = _(u'Ya existe un paciente con el NHC: %s para el centro: %s') % (params['idunico'], centro_id)# IDIOMAOK
        return error_msg


    @authorize(HasAuthKitRole([roles.crear_modif_pacientes]))
    def create(self, format='xml'):
        return GenericRESTController.create(self, format)

    @authorize(HasAuthKitRole([roles.crear_modif_pacientes]))
    def delete(self, id):
        if not pluginPacientes:
            registro = self._registro_by_id(id)
            for centro in registro.centros:
                meta.Session.delete(centro)
            meta.Session.delete(registro)
            meta.Session.commit()
            self._deleted(registro)  # XXX   probar bien... aun será valido "registro" si se acaba de eliminar???
        else:
            # XXX no funciona porque siempre dará IntegrityError, por la tabla "Registro"
            try:
                pluginPacientes.delete(id)
            except PluginException, e:
                log.error(e)
                abort_xml(e.http_status, str(e))
            except Exception, e:
                log.error(e)
                abort_xml(500, _('Ha ocurrido un error eliminando el paciente (%s)') % e)#IDIOMAOK

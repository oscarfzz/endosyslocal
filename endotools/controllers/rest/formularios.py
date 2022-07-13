import logging
from pylons.i18n import _
from xml.etree.ElementTree import Element, SubElement, tostring
from authkit.authorize.pylons_adaptors import authorized, authorize, authorize_request, NotAuthorizedError
from authkit.permissions import RemoteUser, ValidAuthKitUser, UserIn, HasAuthKitRole, And

from endotools.model import meta
from endotools.model.formularios import Formulario, Rel_Campos_Formularios, Rel_GruposCampos_Formularios, ValorPorDefecto
from endotools.model.exploraciones import Exploracion, Rel_Formularios_Exploraciones
from endotools.model.tiposExploracion import TipoExploracion, Rel_Formularios_TiposExploracion,Rel_Servicios_TiposExploracion
from endotools.lib.genericREST import *
from endotools.lib.usuarios.seguridad import roles
from endotools.lib.plugins.base import *
from endotools.lib.formularios import FormExplData, CampoData, nuevo_valor, formulario_from_xml, CampoObligatorioError
from endotools.lib.misc import *
import endotools.lib.registro as registro
from endotools.lib.elementos import get_elementos_by_campo_id
log = logging.getLogger(__name__)

class FormulariosController(GenericRESTController):

    def __init__(self, *args, **kwargs):
        GenericRESTController.__init__(self, *args, **kwargs)
        self.tabla = Formulario
        self.nombre_recurso = 'formulario'
        self.nombre_recursos = 'formularios'
        self.campos_index = ('id', 'titulo')
        self.campos_show = ('gruposCampos', 'titulo')
        self.campo_orderby = Formulario.titulo

    @authorize(RemoteUser())
    def create(self, exploracion_id=None, format='xml'):
        # AÑADIR A EXPLORACION
        # si se indica un exploracion_id es que se esta asignando un formulario a una exploracion, no que se esta creando un nuevo formulario
        if (exploracion_id) and ('formulario_id' in request.params):
            #hemos puesto un abort xq aunque este implenteado el codigo la funcionalidad no esta disponible
            #de esta manera nos aseguramos que el código no se ejecutas
            abort(403, _(u'El usuario actual no puede modificar la exploración'))#IDIOMAOK
            try:
                formulario_id = request.params['formulario_id']
                exploracion = registro_by_id(Exploracion, exploracion_id)
                if not exploracion:
                    abort_xml(400, _(u'No existe ninguna exploración con id=%s') % (exploracion_id))#IDIOMAOK
                rel = Rel_Formularios_Exploraciones()
                rel.formulario_id = formulario_id

                username = request.environ['REMOTE_USER']
                ipaddress = obtener_request_ip(request)
                try:
                    self._set_valorescampos_from_params(username, ipaddress, request.params, rel)
                except Exception, e:
                    log.error(e)
                    abort_xml(400, _(u'Error asignando los valores de los campos de la exploración: %s') % e.message)#IDIOMAOK

                exploracion.formularios.append(rel)
                meta.Session.commit()
            except IntegrityError as e:
                log.error(e)
                meta.Session.close()
                if not registro_by_id(Formulario, formulario_id):
                    abort_xml(400, _(u'No existe ningún formulario con id=%s') % (formulario_id))#IDIOMAOK
                else:
                    abort_xml(400, _(u'La exploración ya contiene el formulario indicado'))#IDIOMAOK
        else:
            #security
            if not authorized( HasAuthKitRole(roles.admin_tipos_exploracion) ):
                abort(403, _(u'El usuario no puede editar exploraciones'))#IDIOMAOK

            if ('webob._parsed_post_vars' in request.environ) and\
                        ('archivo' in request.environ['webob._parsed_post_vars'][0]):
                #print 'multipart'
                # Usando multipart, importar el formulario de un archivo XML
                params = request.environ['webob._parsed_post_vars'][0]
                fieldstorage = params['archivo']
                s = fieldstorage.file.read()
                #print 'contenido del archivo:', s
                formulario = formulario_from_xml(s)
                #   devolver como xml
                response.status_code = 201
                response.content_type = "text/xml"
                root = Element(self.nombre_recurso)
                root.attrib['id'] = formatea_valor(formulario.id)
                return tostring(self._return_doCreate(formulario, root))
            else:
                # si no, hacer el create generico
                return GenericRESTController.create(self, format)

    @authorize(RemoteUser())
    def update(self, id, exploracion_id=None):
        # MODIFICAR LOS VALORES DE LOS CAMPOS DE UN FORMULARIO DE UNA EXPL.
        # si se indica un exploracion_id es que se esta modificando un formulario de una exploracion
        # (los valores de los campos), no que se esta modificando un formulario (la plantilla)
        #   sacar exploracion_id también de params
        if not exploracion_id:
            exploracion_id = request.params.get('exploracion_id', None)

        if (exploracion_id):
            exploracion = registro_by_id(Exploracion, exploracion_id)
            username = request.environ['REMOTE_USER']
            ipaddress = obtener_request_ip(request)

            # 2.4.10 - Comprueba que la exploracion no este eliminada logicamente.
            if exploracion.borrado:
                abort(400, _(u'La exploración se encuentra borrada'))#IDIOMAOK

            #normativa de seguridad
            #para poder modificar una exploración ha de corresponder al usuario conectado o
            #tener el permiso de modificar todas
            medico_conect = medico_from_user(username)
            autorizado = ( exploracion.medico_id == medico_conect.id) \
            or (authorized( HasAuthKitRole(roles.modificar_exploraciones_todas) ))

            if not autorizado:
                abort(403, _(u'El usuario actual no puede modificar la exploración'))#IDIOMAOK
            #fin normativa
            if not exploracion:
                abort_xml(400, _(u'No existe ninguna exploración con id=%s') % (exploracion_id))#IDIOMAOK

            rels = filter(lambda rel: rel.formulario_id == int(id), exploracion.formularios)
            if not rels:
                abort_xml(400, _(u'La exploración no contiene el formulario indicado'))#IDIOMAOK


            try:
                self._set_valorescampos_from_params(username, ipaddress, request.params, rels[0])
            except Exception, e:
                log.error(e)
                raise # XXX
                abort_xml(400, _(u'Error asignando los valores de los campos de la exploración: %s') % e.message)#IDIOMAOK

            meta.Session.commit()
        else:
            #security
            if not authorized( HasAuthKitRole(roles.admin_tipos_exploracion) ):
                abort(403, _(u'El usuario actual no puede editar exploraciones'))#IDIOMAOK

            formulario = self._registro_by_id(id)
            # atencion: se puede modificar el titulo o la relacion de campos
            # pero no los dos a la vez
            if 'titulo' in request.params:
                # modificar el titulo
                self._update_registro_from_params(formulario, {'titulo': request.params['titulo']})
                meta.Session.commit()
            else:
                # o los campos
                #   NUEVO: si se pasa el param "_modo=VALORESPORDEFECTO" se indica
                #   que solo se van a modificar los valores por defecto.
                #   XXX determinar que se hace si no se pasa el param _modo (o si
                #   se pasa "_modo=CAMPOS")
                modo = 'CAMPOS'
                if '_modo' in request.params:
                    modo = request.params['_modo'].upper()

                if modo == 'VALORESPORDEFECTO':
                    if not self._set_valorespordefecto_from_params(request.params, formulario):
                        abort_xml(400, _(u'ERROR: campo/s incorrecto/s'))#IDIOMAOK
                    meta.Session.commit()
                else:   # o sea, modo == 'CAMPOS'
                    if not self._set_campos_from_params(request.params, formulario):
                        abort_xml(400, _(u'ERROR: campo/s incorrecto/s'))#IDIOMAOK
                    meta.Session.commit()
                    self._set_gruposcampos_from_params(request.params, formulario)



#XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
#XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
#XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
    def _set_gruposcampos_from_params(self, params, formulario):
        # indica el orden de los gruposcampos utilizados
        # el parametro es: gruposcampos=id,id,id... (los ids de los gruposcampos en el orden)
        if not('gruposcampos' in params): return
        ids = params['gruposcampos'].split(',')
        # eliminar los actuales
        for rel in formulario.gruposCampos:
            meta.Session.delete(rel)
        meta.Session.commit()
        # y añadir los indicados
        n = 1
        for id in ids:
            rel = Rel_GruposCampos_Formularios()
            rel.grupoCampos_id = int(id)
            rel.formulario_id = formulario.id
            rel.orden = n
            meta.Session.save(rel)
            n = n + 1
        meta.Session.commit()


    def _set_valorespordefecto_from_params(self, params, formulario):
        # obtener una lista de los campos actuales y la nueva configuracion de valores
        # por defecto segun los parametros.
        # solo se deberia entrar aqui si se pasa el parametro "_modo=VALORESPORDEFECTO"
        # en este caso, solo procesar los campos enviados por parametros, si un campo
        # no se envia, no se quita su valor por defecto
        #print params
        for param in params:
            if param.startswith('_'): continue
            if param in ('titulo', 'gruposcampos'): continue
            campo_id = int(param)   # XXX   ojo, que a lo mejor envian un param incorrecto que no es un int
        valorespordefecto_form = list(rel_campo.campo_id for rel_campo in formulario.valoresPorDefecto)
        valorespordefecto_form.sort()
        #print valorespordefecto_form

        # asignar los indicados como parametros
        # se envian como idcampo=valorpordefecto
        for param in params:
            if param.startswith('_'): continue
            if param in ('titulo', 'gruposcampos'): continue
            campo_id = int(param)   # XXX   ojo, que a lo mejor envian un param incorrecto que no es un int

            valorpordefecto = params[param] if params[param] != '' else None

            # si el valor por defecto indicado es una cadena vacia (convertido ya a None),
            # quitar el valor por defecto si existia
            if valorpordefecto == None:
                if campo_id in valorespordefecto_form:
                    rel = filter(lambda rel: rel.campo_id == campo_id, formulario.valoresPorDefecto)[0]
                    meta.Session.delete(rel)
            else:
                # si ya existe el valor por defecto del campo para este formulario, modificarlo
                if campo_id in valorespordefecto_form:
                    rel = filter(lambda rel: rel.campo_id == campo_id, formulario.valoresPorDefecto)[0]
                    rel.valor = valorpordefecto
                    meta.Session.update(rel)
                # y si no, añadirlo
                else:
                    rel = ValorPorDefecto()
                    rel.campo_id = campo_id
                    rel.formulario_id = formulario.id
                    rel.valor = valorpordefecto
                    meta.Session.save(rel)

        return True


    def _set_campos_from_params(self, params, formulario):
        #   identificar el resto de parametros si son ids de campos correctos
        #   XXX seria mejor usar excepciones, mas que un valor bool de retorno...

        #   XXX para permitir cambiar el orden y grupoCampos de los campos pero sin
        #   anadir ni quitar ninguno (para el caso de que tengan ya exploraciones realizadas)
        #   tendria que primero comprobar que se hayan pasado como parametros los mismos
        #   campos.

        #   XXX ojo, repasar el comportamiento de los valores por defecto...

        # obtener una lista de los campos actuales y la nueva configuracion segun los parametros
        campos_params = []
        #print params
        for param in params:
            if param.startswith('_'): continue
            if param in ('titulo', 'gruposcampos'): continue
            campo_id = int(param)   # XXX   ojo, que a lo mejor envian un param incorrecto que no es un int
            campos_params.append(campo_id)
        campos_form = list(rel_campo.campo_id for rel_campo in formulario.campos)
        valorespordefecto_form = list(rel_campo.campo_id for rel_campo in formulario.valoresPorDefecto)
        campos_params.sort()
        #print campos_params
        campos_form.sort()
        #print 'CAMPOS - FORM: ', campos_form
        valorespordefecto_form.sort()
        #print 'VALORESPORDEFECTO - FORM: ', valorespordefecto_form

        tiene_exploraciones = self._hay_exploraciones_dependientes(formulario)
        #tiene_exploraciones = False    # XXX   descomentar esta linea para no hacer nunca el chequeo... usar solo si se sabe lo que se hace!!!
        if tiene_exploraciones:
            #   comprobar que todos los campos pasados como parametros ya esten
            #   asignados a formulario, y que haya el mismo numero.
            #   si es un nuevo formulario nunca entrara aqui
            if campos_params != campos_form:
                abort(403, _(u'ERROR: No se pueden añadir o quitar campos, ya existen exploraciones realizadas que utilizan este formulario'))#IDIOMAOK

##      try:
        # asignar los indicados como parametros
        # se envian como idcampo=idgrupocampos,posx,posy,ancho,alto,[valorpordefecto]
        # NUEVO: añadido el parametro "valorpordefecto". Además, si se envia una cadena
        # vacia en un parametro, no se actualiza (solo válido en updates!). p.e:
        #       100=,,,,,blabla
        # solo modificará el valor por defecto, el resto de parametros seguiran igual.
        for param in params:
            if param.startswith('_'): continue
            if param in ('titulo', 'gruposcampos'): continue
            campo_id = int(param)   # XXX   ojo, que a lo mejor envian un param incorrecto que no es un int

            s = params[param].split(',')

            grupoCampos_id = s[0] if s[0] != '' else None
##              orden = s[1]
            posx = s[1] if s[1] != '' else None
            posy = s[2] if s[2] != '' else None
            ancho = s[3] if s[3] != '' else None
            alto = s[4] if s[4] != '' else None

            # tratar el 6º parametro (valor por defecto) como opcional, ya que se
            # ha añadido posteriormente
            if len(s) > 5:
                valorpordefecto = s[5] if s[5] != '' else None
            else:
                valorpordefecto = None

            # si ya existe el campo en el formulario, modificar el orden y grupoCampos_id
            if campo_id in campos_form:
                rel = filter(lambda rel: rel.campo_id == campo_id, formulario.campos)[0]
                rel.orden = 1 #xxx
                if posx != None: rel.posx = posx
                if posy != None: rel.posy = posy
                if ancho != None: rel.ancho = ancho
                if alto != None: rel.alto = alto
                if grupoCampos_id != None: rel.grupoCampos_id = grupoCampos_id
                meta.Session.update(rel)

            # si no existe, anadirlo
            else:
                rel = Rel_Campos_Formularios()
                rel.campo_id = campo_id
                rel.formulario_id = formulario.id
                rel.orden = 1   # xxx
                rel.posx = posx
                rel.posy = posy
                rel.ancho = ancho
                rel.alto = alto
                rel.grupoCampos_id = grupoCampos_id
                meta.Session.save(rel)

            # y para los valores por defecto igual...
            if campo_id in valorespordefecto_form:
                if valorpordefecto != None:
                    rel = filter(lambda rel: rel.campo_id == campo_id, formulario.valoresPorDefecto)[0]
                    rel.valor = valorpordefecto
                    meta.Session.update(rel)
            else:
                if valorpordefecto != None:
                    rel = ValorPorDefecto()
                    rel.campo_id = campo_id
                    rel.formulario_id = formulario.id
                    rel.valor = valorpordefecto
                    meta.Session.save(rel)

            # quitar el campo de las listas (si esta), porque luego la usare para eliminar los sobrantes...
            if campo_id in campos_form:
                campos_form.remove(campo_id)

            if campo_id in valorespordefecto_form:
                valorespordefecto_form.remove(campo_id)


        # por ultimo, eliminar las relaciones que se han quitado
        for rel_campo in formulario.campos:
            if rel_campo.campo_id in campos_form:
                meta.Session.delete(rel_campo)

        #print 'VALORESPORDEFECTO - FORM: ', valorespordefecto_form
        for rel_campo in formulario.valoresPorDefecto:
            #print 'formulario.valoresPorDefecto', formulario.valoresPorDefecto
            if rel_campo.campo_id in valorespordefecto_form:
                #print 'rel_campo.campo_id', rel_campo.campo_id
                meta.Session.delete(rel_campo)

##      except:
##          return False

        return True

#XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
#XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
#XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX


    @authorize(RemoteUser())
    def delete(self, id, exploracion_id=None):
        # QUITAR DE EXPLORACION
        # si se indica un exploracion_id es que se esta quitando un formulario de una exploracion, no que se esta eliminando un formulario
        if (exploracion_id):
            #hemos puesto un abort xq aunque este implenteado el codigo la funcionalidad no esta disponible
            #de esta manera nos aseguramos que el código no se ejecutas
            abort(403, _(u'El usuario actual no puede modificar la exploración'))#IDIOMAOK

            exploracion = registro_by_id(Exploracion, exploracion_id)

            if not exploracion:
                abort_xml(400, _(u'No existe ninguna exploración con id=%s') % (exploracion_id))#IDIOMAOK

            # 2.4.10 - Comprueba que la exploracion no este eliminada logicamente.
            if exploracion.borrado:
                abort(400, _(u'La exploración se encuentra borrada'))#IDIOMAOK

            forms = filter(lambda rel: rel.formulario_id == int(id), exploracion.formularios)
            if forms:
                meta.Session.delete(forms[0])
            else:
                abort_xml(400, _(u'La exploración no contiene el formulario indicado'))#IDIOMAOK
            meta.Session.commit()
        else:
            #security
            if not authorized( HasAuthKitRole(roles.admin_tipos_exploracion) ):
                abort(403, _(u'El usuario actual no puede editar tipos de exploración'))#IDIOMAOK

            #TODO: Verificar que no esta asignado a algun tipo de exploracion.
            #       - Si esta en algun tipo de exploracion: NO dejar borrar
            #       - Si no tiene tipo de exploracion entonces, primero borrar la relación de campos:
            #           Rel_campos_formularios. SOLO LA RELACION
            #       - Luego dejar que el generic rest se encargue de todo
            return GenericRESTController.delete(self, id)


    def _doIndex(self, params, format='xml'):
        if self.rel_Formularios_Exploraciones != None:
            data = []
            for rel in self.rel_Formularios_Exploraciones:
                o = {
                    'id': formatea_valor(rel.formulario.id)
                }
                self._anadir_campo_obj(o, rel.formulario, 'titulo')
                data.append(o)
            return self.respuesta_doIndex(None, data, format)
        elif self.rel_Formularios_TiposExploracion != None:
            data = []
            for rel in self.rel_Formularios_TiposExploracion:
                o = {
                    'id': formatea_valor(rel.formulario.id)
                }
                self._anadir_campo_obj(o, rel, 'orden')
                self._anadir_campo_obj(o, rel.formulario, 'titulo')
                data.append(o)
            return self.respuesta_doIndex(None, data, format)
        else:

            if not self.mostrar_todos:
                data = []
                medico = medico_from_user(request.environ['REMOTE_USER'])
                if len(medico.servicios) > 0:

                    # filtra los formularios por los servicios que tiene ese medico
                    cond = []

                    #obtiene todo los tipos de exploracion
                    query = meta.Session.query(TipoExploracion)
                    query = query.join(TipoExploracion.servicios)
                    
                    #por cada servicio se fija si tiene permisos y arma el filtro
                    for rel in medico.servicios:
                        cond.append( (Rel_Servicios_TiposExploracion.servicio_id == rel.servicio_id) )
                    query = query.filter( or_(*cond) )
                    tipos_exploracion = query.all()
                    
                    for texp in tipos_exploracion:

                        activo  = texp.activo
                        #por cada tipo de exploracion busca los formularios.
                        for rel in texp.formularios:
                            
                            # arma el objeto de la respuesta
                            o = {
                                'id': formatea_valor(rel.formulario.id),
                                'activo': activo,
                            }
                            self._anadir_campo_obj(o, rel.formulario, 'titulo')
                            data.append(o)
                        
                    # retorna los formularios disponibles para ese medico de acuerdo a sus servicios.
                    return self.respuesta_doIndex(None, data, format)

            # si viene parametro _all muestra todos los formularios
            # si el medico no tiene servicios muestra todos los formularios
            return GenericRESTController._doIndex(self, params, format)

    @authorize(RemoteUser())
    def index(self, exploracion_id=None, tipoexploracion_id=None, format='xml'):
        self.rel_Formularios_Exploraciones = None
        self.rel_Formularios_TiposExploracion = None

        # si no es del route, intentar sacarlo como params
        if not exploracion_id:
            exploracion_id = request.params.get('exploracion_id', None)
        if not tipoexploracion_id:
            tipoexploracion_id = request.params.get('tipoexploracion_id', None)

        if (exploracion_id):
            exploracion = registro_by_id(Exploracion, exploracion_id)
            if not exploracion:
                abort_xml(400, _(u'No existe ninguna exploración con id=%s') % (exploracion_id))#IDIOMAOK

            #2.4.10 no deja ver los formularios de una expl borrada salvo q tenga permisos
            if exploracion.borrado and not authorized(HasAuthKitRole(roles.borrado_logico)):
                abort(403, _(u'No se pueden visualizar los formularios de una exploración borrada'))#IDIOMAOK

            self.rel_Formularios_Exploraciones = exploracion.formularios
        if (tipoexploracion_id):
            tipoexploracion = registro_by_id(TipoExploracion, tipoexploracion_id)
            if not tipoexploracion:
                abort_xml(400, _(u'No existe ningún tipo de exploración con id=%s') % (tipoexploracion_id))#IDIOMAOK
            self.rel_Formularios_TiposExploracion = tipoexploracion.formularios

        #si viene el parametro _all, entonces muestra todos los tipos de exploracion
        self.mostrar_todos = False
        if "_all" in request.params:
            self.mostrar_todos = True
            del request.params["_all"]

        return GenericRESTController.index(self, format)

    def _return_doIndex(self, formularios, data, format=None):
        #   Añadir "activo", que será true/1 si el formulario está asignado a algún
        #   tipo de exploración habilitado.
        for formulario in formularios:

            a = filter(lambda i: str(i['id']) == str(formulario.id), data)
            if len(a) > 0:
                formulario_el = a[0]
                # añadir "activo"
                formulario_el['activo'] = False
                for rel in formulario.tiposExploracion:
                    if rel.tipoExploracion.activo:
                        formulario_el['activo'] = True
                        break
        return data


    def _return_show(self, formulario, data):
        if self.rel_Formularios_Exploraciones:
            formExpl = FormExplData(self.rel_Formularios_Exploraciones)
        else:
            formExpl = FormExplData(formulario)

        data['gruposCampos'] = []
        # los campos estan ordenados por el grupocampos_id, asi que basta con crear
        # el elemento grupocampos la primera vez que aparece un nuevo grupocampos_id
        for grupoCampos in formExpl.gruposCampos:

            grupo_campos = {
                'id': formatea_valor(grupoCampos.id),
                'titulo': formatea_valor(grupoCampos.nombre),
                'orden': formatea_valor(grupoCampos.orden),
                'columnas': formatea_valor(grupoCampos.columnas)
            }
            data['gruposCampos'].append(grupo_campos)

            if self.showmode == '1':
                grupo_campos['campos'] = []
            else:
                grupo_campos['campos'] = {}



            for campo in grupoCampos.campos:

                #pdb.set_trace()
                if self.showmode == '1':
                    c = { 'nombre': formatea_valor(campo.nombre) }
                    grupo_campos['campos'].append(c)
                else:
                    grupo_campos['campos'][formatea_valor(campo.nombre)] = {}
                    c = grupo_campos['campos'][formatea_valor(campo.nombre)]

                c['id'] = formatea_valor(campo.id)
                c['orden'] = formatea_valor(campo.orden)
                c['posx'] = formatea_valor(campo.posx)
                c['posy'] = formatea_valor(campo.posy)
                c['titulo'] = formatea_valor(campo.titulo)
                c['tipo'] = formatea_valor(campo.tipo)
                c['ancho'] = formatea_valor(campo.ancho)
                c['alto'] = formatea_valor(campo.alto)
                c['solo_lectura'] = formatea_valor(campo.solo_lectura or False)
                c['script'] = formatea_valor(campo.script or None)
                c['tipo_control'] = formatea_valor(campo.tipo_control)
                c['ambito'] = formatea_valor(campo.ambito)
                c['obligatorio'] = formatea_valor(campo.obligatorio or False)
                c['campo_rel_id'] = formatea_valor(campo.campo_rel_id or None)

                if self.rel_Formularios_Exploraciones:
                    c['valor'] = campo.valor.to_obj()
                    # el_valor = SubElement(el_campo, 'valor')
                    # campo.valor.to_elem(el_valor)

            if self.showmode == '1':
                #orden de los campos por titulo
                grupo_campos['campos'] = sorted(grupo_campos['campos'], key=lambda campo: campo['titulo'])

        if self.rel_Formularios_Exploraciones:
            # REGISTRAR: Consulta del formulario (exploracion)
            username = request.environ.get('REMOTE_USER', registro.DEFAULT_REMOTE_USER)
            ipaddress = obtener_request_ip(request)
            registro.nuevo_registro(username, ipaddress, self.rel_Formularios_Exploraciones.exploracion, registro.eventos.mostrar,
                                    registro.res.exploracion, 'FORMULARIO', str(formulario.titulo), None)
            



    @authorize(RemoteUser())
    def show(self, id, exploracion_id=None, format='xml'):
        #   _showmode=0|1 , indica si en el xml los nodos de los campos seran el nombre del campo (0)
        #   o seran nodos genericos "campo" y el nombre del campo sera un child "nombre"
        if '_showmode' in request.params:
            self.showmode = request.params['_showmode']
        else:
            self.showmode = '0'

        self.rel_Formularios_Exploraciones = None

        # si no es del route, intentar sacarlo como un param
        if not exploracion_id:
            exploracion_id = request.params.get('exploracion_id', None)

        if (exploracion_id):
            exploracion = registro_by_id(Exploracion, exploracion_id)
            if not exploracion:
                abort_xml(400, _(u'No existe ninguna exploración con id=%s') % (exploracion_id))#IDIOMAOK

            #2.4.10 no deja ver los formularios de una expl borrada salvo q tenga permisos
            if exploracion.borrado and not authorized(HasAuthKitRole(roles.borrado_logico)):
                abort_xml(400, _(u'No se puede visualizar un formulario de una exploración borrada'))#IDIOMAOK

            forms = filter(lambda rel: rel.formulario_id == int(id), exploracion.formularios)
            if forms:
                self.rel_Formularios_Exploraciones = forms[0]
            else:
                abort_xml(400, _(u'La exploración no contiene el formulario indicado'))#IDIOMAOK

        return GenericRESTController.show(self, id, format)



    def _set_valorescampos_from_params(self, username, ipaddress, params, rel_formularios_exploraciones):
        #   REGISTRAR
        #   identificar el resto de parametros si son ids de campos correctos
        #   cada parametro tendria que ser: formulario_id,campo_id=valor

        for param in params:
            if param in ('_rand', '_'): continue
            if param in ('exploracion_id', 'formulario_id'): continue
            if param in ('agenda_id',): continue # XXX tengo que mirar si es correcto que ivan envie esto aqui!

            if not isint(param): continue

            # es un int, por lo tanto es un valor de un campo normal (no de plugin)

            campo_id = int(param)
            valor = params[param]
            try:
                nuevo_valor(username, ipaddress, rel_formularios_exploraciones, campo_id, valor)
            except CampoObligatorioError, e:
                log.error(e)
                abort_xml(400, _(u'El campo %s es obligatorio, debe de rellenarlo') % e.message)#IDIOMAOK


    def _hay_exploraciones_dependientes(self, formulario):
        for rel in formulario.tiposExploracion:
            if len(rel.tipoExploracion.exploraciones) > 0:
                return True
        return False
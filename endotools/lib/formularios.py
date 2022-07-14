""" clases y funciones para facilitar la gestion de formularios """

##tipos de campos:
##1: texto
##2: selec
##3: multi
##4: bool
##5: memo
##6: separador/titulo


import types
import logging
from pylons.i18n import _
from endotools.model import meta
from endotools.model.exploraciones import Exploracion, Rel_Formularios_Exploraciones
from endotools.model.formularios import Formulario, Rel_GruposCampos_Formularios, Rel_Campos_Formularios
from endotools.model.campos import Campo
from endotools.model.valores import ValorTexto, ValorSelec, ValorMulti, ValorBool
from endotools.model.elementos import Elemento
from endotools.model.gruposCampos import GrupoCampos
from xml.etree.ElementTree import Element, SubElement, tostring

from endotools.lib.plugins.base import *
from endotools.config.plugins import pluginCampos

from endotools.lib.misc import formatea_valor, record, isint, isiter, registro_by_id
from sqlalchemy.sql import and_
import cgi

import endotools.lib.registro as registro
from endotools.lib.elementos import *


TIPO_TEXTO = 1
TIPO_SELEC = 2
TIPO_MULTI = 3
TIPO_BOOL = 4
TIPO_MEMO = 5
TIPO_SEPARADOR = 6

class CampoObligatorioError(Exception):
    def __init__(self, message):
        self.message = message

class TipoCampo:
    """ clase base de ayuda para asignar y obtener el valor de un campo
    de un tipo determinado. implementar en descendientes segun el tipo de campo.
    """

    tipo_id = None

    def __init__(self):
        """ inicializar en descendiente:
        nombre_valores  nombre de la relacion con los valores en el reg. del formulario
        ClaseValor    clase orm de sqlalchemy que representa un registro del valor
        """
        self.nombre_valores = None
        self.ClaseValor = None

    def __valor_existente(self, campo_id, valores):
        for valor in valores:
            if valor.campo_id == campo_id:
                return valor
        return None

    def nuevo_valor(self, username, ipaddress, rel_formularios_exploraciones, campo, valor):
        """ asigna un valor a un campo, pasandolo con un str.
        (se implementa en _asignar_valor, en descendientes)

        username                           necesario para el registro de acceso
        rel_formularios_exploraciones      registro de sqlalchemy
        campo_id                            id del campo
        valor                              str
        """
        exploracion = rel_formularios_exploraciones.exploracion
        valores = getattr(rel_formularios_exploraciones, self.nombre_valores)
        valor_reg = self.__valor_existente(campo.id, valores)
        if not valor_reg:
            valor_reg = self.ClaseValor()
            valor_reg.campo_id = campo.id
            valores.append(valor_reg)

        # REGISTRAR
        #   XXX ojo, estar al tanto de esta comparación, ya que puede ser que el tipo de dato
        #   de "valor" no coincida con el almacenado en BBDD, en "valor_reg", pero que
        #   realmente sea el mismo. p.ej. que a un campo de tipo Int se le pase un valor
        #   como un String, aunque luego SQLAlchemy lo convertirá a Int...
##      #   XXX además, lo correcto sería poner también dentro de la condición
##      #   la llamada a _asignar_valor(), pero hasta que no esté bien probado
##      #   no se hará, ya que afectaría al funcionamiento de la aplicación.

        # XXX   apaño, mejorarlo.
        #      es algo asi como la inversa de _asignar_valor(), por lo que seria mejor
        #      pasarlo tambien a metodos de cada clase.
        if (self.tipo_id == TIPO_TEXTO) or (self.tipo_id == TIPO_MEMO):
            valor_anterior = valor_reg.valor
        elif self.tipo_id == TIPO_SELEC:
            valor_anterior = str(valor_reg.elemento_id) if valor_reg.elemento_id else ''
            valor_anterior_descr = elemento_by_id(valor_reg.elemento_id)
        elif self.tipo_id == TIPO_BOOL: # viene '0' o '1'
            valor_anterior = {True: '1', False: '0'}.get(valor_reg.valor, None)
        # #####

        #print valor, valor_anterior, valor != valor_anterior

        if valor != valor_anterior:
            self._asignar_valor(valor_reg, valor) # XXX comprobar que funcione todo bien!!!!! que si no fallará el guardado

            # si valor_reg se ha creado ahora, el orm aun no ha asignado el .campo, asi que obtenerlo "a mano"
#           campo = valor_reg.campo
#           if not campo:
#               campo = registro_by_id(Campo, campo_id)

            # XXX   apaño... segun el tipo de campo en vez de registrar el valor basico,
            #      formatearlo para que quede mejor
            if self.tipo_id == TIPO_SELEC:
                valor = elemento_by_id(valor_reg.elemento_id)
                valor_anterior = valor_anterior_descr
            # #####

            # XXX   por alguna extraña razon ahora no se puede acceder a valor_reg.exploracion, aunque antes si....
            #       asi que se ha extraido exploracion de rel_formularios_exploraciones al principio, y es lo que se usa
            #       en esta llamada
            registro.nuevo_registro(username, ipaddress, exploracion, registro.eventos.modificar, registro.res.exploracion, campo.nombre, valor_anterior, valor)
        # #################################



    def _asignar_valor(self, valor_reg, valor):
        """ implementar en descendiente. asignar un nuevo valor.
        valor      es un str
        valor_reg   es un registro de sqlalchemy
        """

    def valor(self, valores):
        """ implementar en descendiente. devuelve el valor en el tipo de python correspondiente al tipo de campo.
        valores  list de registros de sqlalchemy, lista de valores en un formato especifico segun el tipo
        """
        pass

    def valor_to_html(self, valores):
        """ implementar en descendiente. muestra el valor en formato html.
        valores  list de registros de sqlalchemy, lista de valores en un formato especifico segun el tipo
        """
        pass

    def valor_to_text(self, valores):
        """ implementar en descendiente. muestra el valor en formato texto normal. Se usa al generar
        un informe en Word.
        valores  list de registros de sqlalchemy, lista de valores en un formato especifico segun el tipo
        """
        pass

    def valor_to_elem(self, valores, elem):
        """ implementar en descendiente. asigna el valor en formato xml al elem.
        valores  list de registros de sqlalchemy, lista de valores en un formato especifico segun el tipo
        """
        pass

    def valor_to_obj(self, valores):
        """ implementar en descendiente. devuelve el valor como objeto de Python, tipo JSON.
        valores  list de registros de sqlalchemy, lista de valores en un formato especifico segun el tipo
        """
        pass


class TipoCampoMulti(TipoCampo):
    """ clase base para campos que pueden tener multiples valores.
    implementar en descendientes segun el tipo de campo.
    """
    tipo_id = None

    def __init__(self):
        self.nombre_valores = None
        self.ClaseValor = None

    def nuevo_valor(self, username, ipaddress, rel_formularios_exploraciones, campo, valor):
        """ asigna un valor o varios a un campo, pasandolos con un str.
        (se implementa en _asignar_valor, en descendientes)

        rel_formularios_exploraciones   registro de sqlalchemy
        campo_id                        id del campo
        valor                           str
        """

        exploracion = rel_formularios_exploraciones.exploracion
        valores = getattr(rel_formularios_exploraciones, self.nombre_valores)
        # Para escribir en el registro si fuera necesario
        registro_valores_anteriores = self.valor_to_html( filter(lambda v: v.campo_id == campo.id, valores) ) # guarda el valor anterior de este campo, para el registro # XXX ! (usar valor_to_text()???

        #nuevos_valores = list( [v.split(":") for v in self._extrae_valores(valor) ] )
        nuevos_valores = list( self._extrae_valores(valor) )
        if campo.tipo_control==2:
            nuevos_valores_id = list(map((lambda k: k[0]),nuevos_valores))
        else:
            nuevos_valores_id = nuevos_valores

        # eliminar los anteriores que ya no esten en los nuevos valores
        for v in list(valores):
            if (v.campo.id == campo.id) and (not v.elemento_id in nuevos_valores_id):
                meta.Session.delete(v)
                valores.remove(v)

        # anadir los nuevos valores que no esten en los anteriores
        # tener en cuenta el orden en nuevos_valores!
        # el filter filtra cualquier valor nulo ('', ', False, None...)
        for i, v in enumerate(filter(None, nuevos_valores)):

            # si ya estaba anteriormente también, solo se le cambia el orden
            ya_estaba = False
            for x in valores:

                # checkea el tipo de dato de "v" para saber si es una actualizacion
                # con cantidades o sin cantidades
                nuevo_valor_id = None
                nuevo_valor_cantidad = 1
                if isinstance(v, int):
                    nuevo_valor_id = v
                else:
                    # si es con cantidades 2.4.10
                    nuevo_valor_id = v[0]
                    nuevo_valor_cantidad = v[1]

                if (nuevo_valor_id == x.elemento_id) and (campo.id == x.campo_id):# XXX !
                    x.orden = i
                    x.cantidad = nuevo_valor_cantidad
                    ya_estaba = True
                    break

            if ya_estaba: continue

            # añadirlo si no estaba antes
            valor_reg = self.ClaseValor()
            valor_reg.orden = i
            valor_reg.campo_id = campo.id
            self._asignar_valor(valor_reg, v)
            valores.append(valor_reg)


        # REGISTRAR
        registro_nuevos_valores = self.valor_to_html( filter(lambda v: v.campo_id == campo.id, valores) ) # el valor de este campo ahora, para el registro XXX ! usar valor_to_text() ???
        if registro_nuevos_valores != registro_valores_anteriores:
            campo = registro_by_id(Campo, campo.id)
            registro.nuevo_registro(username, ipaddress, exploracion, registro.eventos.modificar, registro.res.exploracion, campo.nombre, registro_valores_anteriores, registro_nuevos_valores)
        # #################################


    def _asignar_valor(self, valor_reg, valor):
        """ implementar en descendiente """
        pass

    def _extrae_valores(self, valor):
        """ extrae los valores de un str. ha de devolver una lista de valores.
        implementar en desc.
        """
        pass


class TipoCampo_texto(TipoCampo):
    tipo_id = TIPO_TEXTO

    def __init__(self):
        self.nombre_valores = 'valoresTexto'
        self.ClaseValor = ValorTexto

    def _asignar_valor(self, valor_reg, valor):
        # el valor es directamente la cadena de texto
        valor_reg.valor = valor

    def valor(self, valores):
        if len(valores) > 0:
            if isinstance(valores[0], ValorTexto):
                return valores[0].valor
            else:
                return valores[0]
        return None

    def valor_to_html(self, valores):
        # devolver el campo valor del registro
#       return formatea_valor(self.valor(valores))

        v = self.valor(valores)
        if isinstance(v, str):
            v = v.split('\n')
            return '<br>'.join( formatea_valor(cgi.escape(linea)) for linea in v )
        else:
            return formatea_valor(self.valor(valores))

    def valor_to_text(self, valores):
        v = self.valor(valores)
        return formatea_valor(self.valor(valores))

    def valor_to_elem(self, valores, elem):
        elem.text = formatea_valor(self.valor(valores))

    def valor_to_obj(self, valores):
        return formatea_valor(self.valor(valores))


# De momento es igual que el tipo texto. Esta limitado a 4000 caracteres
class TipoCampo_memo(TipoCampo_texto):
    tipo_id = TIPO_MEMO

class TipoCampo_selec(TipoCampo):
    tipo_id = TIPO_SELEC

    def __init__(self):
        self.nombre_valores = 'valoresSelec'
        self.ClaseValor = ValorSelec

    def nuevo_valor(self, username, ipaddress, rel_formularios_exploraciones, campo, valor):
        if campo.tipo_control == 1 and valor.strip():
            # si es autocomplete
            # consultamos si el valor (el texto) recibido existe como elemento
            # si el campo tiene ambito "por servicio", filtrar el elemento para
            # el servicio de la exploración.
            servicio_id = None
            if campo.ambito == 1:
                servicio_id = rel_formularios_exploraciones.exploracion.servicio_id
            elemento_id = elemento_by_valor(valor, campo.id, servicio_id)
            
            if not elemento_id:
                #sino existe lo creamos
                elemento = nuevo_elemento()
                elemento.campo_id = campo.id
                elemento.nombre =  valor
                elemento.activo =  True

                # además, si el campo tiene ambito "por servicio", asignar al
                # elemento el servicio de la exploracion.
                if campo.ambito == 1:
                    elemento.servicio_id = rel_formularios_exploraciones.exploracion.servicio_id
                #
                
                meta.Session.save(elemento)
                meta.Session.commit()

                elemento_id = elemento.id


            valor = elemento_id

        TipoCampo.nuevo_valor(self,username, ipaddress, rel_formularios_exploraciones, campo, valor)

    def _asignar_valor(self, valor_reg, valor):
        # el valor es el id del elemento seleccionado
        #   XXX hacer que se pueda pasar el texto en vez del id? y que lo busque autom.
        #   si se pasa un valor vacio (cadena vacia) asignarle null
        
        # #916: Estas dos lineas se agregaron para que se pueda grabar la exploracion si ocurre el problema
        #       que esta descripto en la peticion 916. Si se arregla la 916 se tendria que quitar. 
        if valor == "_NUEVO_VALOR_" or valor == "_SIN_VALOR_":
            valor = ''
            
        valor_reg.elemento_id = int(valor) if valor else None

    def valor(self, valores):
        # valores ademas de contener el registro, puede contener el valor con el formato: [(id, nombre)]
        # devuelve el id y el nombre
        if len(valores) > 0:
            if isinstance(valores[0], ValorSelec):
                if valores[0].elemento:
                    return valores[0].elemento.id, valores[0].elemento.nombre, valores[0].elemento.codigo
            else:
                return valores[0], valores[0]
        return None

    def valor_to_html(self, valores):
        # devolver el nombre del elemento al que hace referencia el registro
        # valores ademas de contener el registro, puede contener el valor con el formato: [(id, nombre)]
        v = self.valor(valores)
        if v:

            return formatea_valor( cgi.escape(v[1]) )
        else:
            return ''

    def valor_to_text(self, valores):
        # devolver el nombre del elemento al que hace referencia el registro
        # valores ademas de contener el registro, puede contener el valor con el formato: [(id, nombre)]
        v = self.valor(valores)
        if v:
            return formatea_valor(v[1])
        else:
            return ''

    def valor_to_elem(self, valores, elem):
        v = self.valor(valores)
        if v:
            elemento = SubElement( elem, 'elemento', {'id': formatea_valor(v[0])} )
            SubElement(elemento, 'nombre').text = formatea_valor(v[1])

    def valor_to_obj(self, valores):
        v = self.valor(valores)
        if v:
            return {
                'elemento': {
                    'id': formatea_valor(v[0]),
                    'nombre': formatea_valor(v[1]),
                    'codigo': formatea_valor(v[2])
                }
            }
        else:
            return None


class TipoCampo_bool(TipoCampo):
    tipo_id = TIPO_BOOL

    def __init__(self):
        self.nombre_valores = 'valoresBool'
        self.ClaseValor = ValorBool

    def _asignar_valor(self, valor_reg, valor):
        # el valor es '0' o '1'
        #   si se pasa un valor vacio (cadena vacia) asignarle null
        valor_reg.valor = bool(int(valor)) if valor else None

    def valor(self, valores):
        if len(valores) > 0:
            if isinstance(valores[0], ValorBool):
                return valores[0].valor
            else:
                return valores[0]
        return None

    def valor_to_html(self, valores):
        # devolver 'si' o 'no'
        return formatea_valor(self.valor(valores))

    def valor_to_text(self, valores):
        # devolver 'si' o 'no' (igual que to_html)
        return formatea_valor(self.valor(valores))

    def valor_to_elem(self, valores, elem):
        elem.text = formatea_valor(self.valor(valores))

    def valor_to_obj(self, valores):
        return formatea_valor(self.valor(valores))


class TipoCampo_multi(TipoCampoMulti):
    tipo_id = TIPO_MULTI

    def __init__(self):
        self.nombre_valores = 'valoresMulti'
        self.ClaseValor = ValorMulti

    def _asignar_valor(self, valor_reg, valor):
        # el valor es el id del elemento seleccionado
        #   XXX hacer que se pueda pasar el texto en vez del id? y que lo busque autom.
        if isinstance(valor, int):
            valor_reg.elemento_id = int(valor)
            valor_reg.cantidad = 1
        else:
            # 2.4.10
            # si no es de tipo int, entonces es lista.
            # Si es lista entoncee es pq viene con la cantidad.
            valor_reg.elemento_id = int(valor[0])
            valor_reg.cantidad = int(valor[1])

    def _extrae_valores(self, valor):
        # el valor es una lista de ids de elementos separados por comas.
        # además, el orden de estos elementos se tiene en cuenta.
        # devolverlo como int!

        for v in filter( lambda v: v != '', valor.split(',') ):
            if ":" in v:
                #si viene un ":" es pq viene con cantidades 2.4.10
                yield [ int(x) for x in v.split(":") ]
            else:
                yield int(v)

    def valor(self, valores):
        # devuelve los valores en este formato: [(id, nombre), (id, nombre), ...]
        # valores ademas de contener registros, puede contener valores con el formato: [(id, nombre), (id, nombre), ...]
        # los ordena por el campo "orden"
        # !!!(tener en cuenta que se ordena directamente la lista "valores")
        r = []

        # atencion, si el contenido de "valores" no son todo registros (con la propiedad
        # orden), el orden final será indeterminado
        # tambien puede fallar si algún campo orden tiene valor None

        #print 'TipoCampo_multi.valor():'
        ##for v in valores:
        ##  print '   ', v.orden, v.elemento_id, v.elemento
        try:
            valores.sort(lambda a,b: a.orden - b.orden)
        except Exception as e:
            log.error(e)
        #import pdb
        #pdb.set_trace()
        for v in valores:
            if isinstance(v, ValorMulti):
                elemento = v.elemento
                if not elemento:
                    elemento = registro_by_id(Elemento, v.elemento_id)
                r.append( (elemento.id, elemento.nombre, v.cantidad, elemento.codigo) )
            else:
                r.append( (v[0], v[1]) )
        return r

    def valor_to_html(self, valores):
        # devolver los nombre de los elementos a los que hacen referencia cada uno de los registros, separados por <br>s
        # valores ademas de contener registros, puede contener valores con el formato: [(id, nombre), (id, nombre), ...]
        r = self.valor(valores)
        #" Cant:" + formatea_valor(cgi.escape(str(cantidad) or "0"))
        return '<br>'.join( formatea_valor(cgi.escape(nombre)) for id, nombre, cantidad, codigo in r )

    def valor_to_text(self, valores):

        def mostrar_cantidad(cantidad,tipo_control):
            if tipo_control==2:
                return " (" + formatea_valor(cantidad or "1") +")"
            else:
                return ""

        # devolver los nombre de los elementos a los que hacen referencia cada uno de los registros, separados por saltos de linea
        # valores ademas de contener registros, puede contener valores con el formato: [(id, nombre), (id, nombre), ...]
        r = self.valor(valores)

        # verifica si el campo es de tipo cantidad. Si lo es, entonces muestra entre parentesis la cantidad.
        tipo_control = None
        if len(valores)>0:
            tipo_control = valores[0].campo.tipo_control

        return '\n'.join( formatea_valor(nombre) + mostrar_cantidad(cantidad,tipo_control) for id, nombre,cantidad, codigo in r )

    def valor_to_elem(self, valores, elem):
        r = self.valor(valores)
        for id, nombre, cantidad, codigo in r:
            elemento = SubElement(elem, 'elemento', {'id': formatea_valor(id)})
            SubElement(elemento, 'nombre').text = formatea_valor(nombre)
            SubElement(elemento, 'cantidad').text = formatea_valor(cantidad or "O")
            SubElement(elemento, 'codigo').text = formatea_valor(codigo)

##      r = []
##      for v in valores:
##          if isinstance(v, ValorMulti):
##              SubElement(elem, 'elemento', {'id': formatea_valor(v.elemento.id)}).text = v.elemento.nombre
##          else:
##              SubElement(elem, 'elemento', {'id': formatea_valor(v[0])}).text = v[1]

    def valor_to_obj(self, valores):
        r = self.valor(valores)
        data = []
        for id, nombre, cantidad, codigo in r:
            data.append({
                'id': formatea_valor(id),
                'nombre': formatea_valor(nombre),
                'cantidad': formatea_valor(cantidad or "0"),
                'codigo': formatea_valor(codigo)
            })
        return data


class TipoCampo_separador(TipoCampo):
    tipo_id = TIPO_SEPARADOR

    def nuevo_valor(self, username, ipaddress, rel_formularios_exploraciones, campo, valor):
        # no hace nada, ya que el separador no tiene valor
        pass

    def valor(self, valor_regs):
        return None

    def valor_to_html(self, valor_regs):
        return ''

    def valor_to_text(self, valor_regs):
        return ''

    def valor_to_elem(self, valor_regs, elem):
        return ''

    def valor_to_obj(self, valores):
        return ''


_tipos_campos = {}
for n, o in globals().items():
    if isinstance(o, (type, types.ClassType)) and \
        issubclass(o, TipoCampo) and \
        o.tipo_id:
        _tipos_campos[o.tipo_id] = o

def _tipoCampo(tipo_id):
    return _tipos_campos[tipo_id]()

def validar_obligatorio(campo, valor):
    #TIPO_TEXTO = 1
    #TIPO_SELEC = 2
    #TIPO_MULTI = 3
    #TIPO_BOOL = 4
    #TIPO_MEMO = 5
    #TIPO_SEPARADOR = 6
    #print ("campo obligatorio",campo.titulo)
    if(campo.tipo in (1,2,3,5)):
        if not valor.strip():
            #print "ERROR obligatorio"
            raise CampoObligatorioError(campo.titulo)
    elif(campo.tipo == 4):
        if bool(int(valor)) is not True:
            raise CampoObligatorioError(campo.titulo)

def nuevo_valor(username, ipaddress, rel_formularios_exploraciones, campo_id, valor, por_defecto=False):
    """ asigna un nuevo valor a un campo de un formulario de una exploracion """
    # si el campo_id es un int, es un campo normal. Si no, es un campo de plugin

    if isint(campo_id):
        #   identificar el tipo de campo
        campo = meta.Session.query(Campo).filter(Campo.id == campo_id).one()

##      #   y si se puede anadir a este formulario
##      if not filter(lambda form: form.id == rel_formularios_exploraciones.formulario.id,
##                      campo.formularios):
##          raise Exception('El campo es incorrecto')
        if(campo.obligatorio and por_defecto == False):
            validar_obligatorio(campo, valor)

        _tipoCampo(campo.tipo).nuevo_valor(username, ipaddress, rel_formularios_exploraciones, campo, valor)
    else:
        pass
##      # es de plugin
##      if pluginCampos:
##          pluginCampos.set_valor_campo(rel_formularios_exploraciones, campo_id, valor)



class GrupoCamposData:
    """
    contiene informacion sobre un grupocampos (nombre, columnas...)
    """
    def __init__(self, **kargs):
        self.id = kargs.get("id")
        self.nombre = kargs.get("nombre")
        self.columnas = kargs.get("columnas")

class CampoData:
    """
    contiene informacion sobre un campo (nombre, tipo, etc...)
    """

    class _ValorCampo:
        """ contiene el valor de un campo y lo formatea como html o como un elemento de xml """
        def __init__(self, campodata):
            self.valores = []
            self.campodata = campodata

        def get(self):
            return _tipoCampo(self.campodata.tipo).valor(self.valores)

        def to_html(self):
            return _tipoCampo(self.campodata.tipo).valor_to_html(self.valores)

        def to_text(self):
            return _tipoCampo(self.campodata.tipo).valor_to_text(self.valores)

        def to_elem(self, elem):
            return _tipoCampo(self.campodata.tipo).valor_to_elem(self.valores, elem)

        def to_obj(self):
            return _tipoCampo(self.campodata.tipo).valor_to_obj(self.valores)

        def add_valor(self, valor):
            self.valores += [valor]

    def __init__(self, **kargs):
        """
        parametros:
        id, nombre, titulo, tipo, columnas, orden, grupoCampos_id, grupoCampos_nombre, grupoCampos_columnas, posx, posy, campo_rel_id
        """
        self.id = kargs.get("id")
        self.nombre = kargs.get("nombre")
        self.titulo = kargs.get("titulo")
        self.tipo = kargs.get("tipo")
        self.ancho = kargs.get("ancho")
        self.alto = kargs.get("alto")
        self.orden = kargs.get("orden")
        self.posx = kargs.get("posx")
        self.posy = kargs.get("posy")
        self.solo_lectura = kargs.get("solo_lectura")
        self.obligatorio = kargs.get("obligatorio")
        self.tipo_control = kargs.get("tipo_control")
        self.ambito = kargs.get("ambito")
        self.script = kargs.get("script")
        self.campo_rel_id = kargs.get("campo_rel_id")
        self.grupoCampos = GrupoCamposData( id = kargs.get("grupoCampos_id"),
                                            nombre = kargs.get("grupoCampos_nombre"),
                                            columnas = kargs.get("grupoCampos_columnas"))
        self.valor = self._ValorCampo(self)


class FormExplData:
    """ facilita el acceso a la lectura de los campos de un formulario de una exploración.

    a partir de una exploracion y un formulario obtiene la informacion:

    gruposCampos -> lista de grupos de campos, conteniendo los campos del mismo asi como el titulo y el id
        informacion del campo (id, nombre, titulo, valor, columnas, grupoCampos...)

    """

    def _add_valor(self, valor):
        """ anade un valor mas al Valor del campo (un campo puede tener multiples valores, aunque lo llame Valor) """
        for grupoCampos in self.gruposCampos:
            for campo in grupoCampos.campos:
                if campo.id == valor.campo.id:
                    campo.valor.add_valor(valor)
                    break

    def __init__(self, param):
        """
        si se pasa como paramatro un registro de rel_Formularios_Exploraciones, es un formulario de una exploracion, con datos
        si se pasa como paramatro un registro de formularios, es solo el formulario sin datos de un exploracion (la plantilla)
        """
        if isinstance(param, Rel_Formularios_Exploraciones):
            formulario = param.formulario
            valores_iter = param.valores()
        elif isinstance(param, Formulario):
            formulario = param
            valores_iter = None
        else:
            raise Exception(_('El tipo del parámetro "param" es incorrecto (%s)') % type(param))#IDIOMAOK

        self.id = formulario.id
        self.titulo = formulario.titulo
        self.gruposCampos = []

        # crear los grupos de campos y los campos, sin valores
        # los campos estan ordenados por el grupocampos_id y por el orden, asi que basta con crear
        # el elemento grupocampos la primera vez que aparece un nuevo grupocampos_id
        grupoCampos = None
        grupocampos_id_actual = None
        for c in formulario.campos:
            if c.grupoCampos_id != grupocampos_id_actual:
                grupocampos_id_actual = c.grupoCampos_id
                grupoCampos = record()
                grupoCampos.id = c.grupoCampos.id
                grupoCampos.nombre = c.grupoCampos.nombre
                grupoCampos.columnas = c.grupoCampos.columnas
                grupoCampos.campos = []
                # obtener el orden del grupocampos
                formulario.gruposCampos
                rel = filter(lambda rel: rel.grupoCampos_id == grupocampos_id_actual, formulario.gruposCampos)
                if rel:
                    rel = rel[0]
                    grupoCampos.orden = int(rel.orden)
                else:
                    grupoCampos.orden = len(self.gruposCampos) + 1
                #
                self.gruposCampos += [grupoCampos]

            # crear un objeto que representa el campo y anadirlo a la lista de campos
            cols = c.ancho or c.campo.columnas # XXX mas adelante quitare el campo "columnas" de la tabla "campos" por lo tanto bastara con 'cols = c.ancho'
            campo = CampoData(  id = c.campo.id,
                                nombre = c.campo.nombre,
                                titulo = c.campo.titulo,
                                tipo = c.campo.tipo,
                                ancho = cols,
                                alto = c.alto,
                                orden = c.orden,
                                posx = c.posx,
                                posy = c.posy,
                                solo_lectura = c.campo.solo_lectura,
                                obligatorio = c.campo.obligatorio,
                                tipo_control = c.campo.tipo_control,
                                ambito = c.campo.ambito,
                                script = c.campo.script,
                                campo_rel_id = c.campo_rel_id
                                )
            grupoCampos.campos += [campo]

        # ordenar los gruposcampos por el orden
        self.gruposCampos.sort(lambda x, y: x.orden - y.orden)

        # asignar los valores que contiene la exploración (los campos ya estan creados)
        if valores_iter:
            for valor in valores_iter:
                self._add_valor(valor)


# ######################################


from xml.etree.ElementTree import Element, SubElement, tostring, XML

def formulario_from_xml(xml):
    """
    Crea un nuevo formulario en la bbdd a partir del xml, tal como lo devuelve el show()
    """
    xml = xml.encode('utf_8')
    xml = XML(xml)

    formulario = Formulario()
    formulario.titulo = xml.find('titulo').text
    meta.Session.save(formulario)

    for grupocampos_el in xml.find('gruposCampos').findall('grupoCampos'):
        # GRUPOCAMPOS
        # si existe un grupoCampos identico utilizarlo, si no crearlo nuevo
        titulo =    grupocampos_el.find('titulo').text
        orden =     int( grupocampos_el.find('orden').text )
        columnas =  int(grupocampos_el.find('columnas').text )
        q = meta.Session.query(GrupoCampos).filter(and_(
                            GrupoCampos.nombre.like(titulo),
##                          GrupoCampos.nombre == titulo,
                            GrupoCampos.columnas == columnas
            ))
        if q.count() > 0:
            grupocampos = q.one()
        else:
            grupocampos = GrupoCampos()
            grupocampos.nombre = titulo
            grupocampos.columnas = columnas
            meta.Session.save(grupocampos)
            meta.Session.commit()    # XXX   si no, grupocampos.id es NULL

        rel = Rel_GruposCampos_Formularios()
        rel.grupoCampos_id = grupocampos.id
        rel.orden = orden
        formulario.gruposCampos.append(rel)
        meta.Session.save(rel)

        for campo_el in grupocampos_el.find('campos'):
            # CAMPO
            # si existe un campo identico (de momento solo comprueba nombre y tipo)
            # lo utiliza. Si no, lo crea nuevo.
            nombre =    campo_el.tag
            tipo =      campo_el.find('tipo').text
            titulo =    campo_el.find('titulo').text
            posx =      int( campo_el.find('posx').text )
            posy =      int( campo_el.find('posy').text )
            ancho =     int( campo_el.find('ancho').text )
            alto =      int( campo_el.find('alto').text )
            obligatorio = 0
##          solo_lectura = campo_el.find('solo_lectura').text
            solo_lectura = 0 # XXX de momento no lo coge
            ambito = None # XXX de momento no lo coge
            script = None # XXX de momento no lo coge
            tipo_control = campo_el.find('tipo_control').text
            q = meta.Session.query(Campo).filter(and_(
                                Campo.nombre == nombre,
                                Campo.tipo == tipo
                ))
            if q.count() > 0:
                campo = q.one()
            else:
                campo = Campo()
                campo.nombre = nombre
                campo.titulo = titulo
                campo.tipo = tipo
                campo.solo_lectura = solo_lectura
                campo.obligatorio = obligatorio
                campo.tipo_control = tipo_control
                campo.columnas = 1
                campo.script = script
                campo.ambito = ambito
                meta.Session.save(campo)
                meta.Session.commit()    # XXX   si no, campo.id es NULL

            rel = Rel_Campos_Formularios()
##          rel.campo = campo
            rel.campo_id = campo.id
            rel.orden = 0   # no se usa, pero no permite NULL
            rel.grupoCampos = grupocampos
            rel.posx = posx
            rel.posy = posy
            rel.ancho = ancho
            rel.alto = alto
            formulario.campos.append(rel)
            meta.Session.save(rel)

    meta.Session.commit()
    return formulario
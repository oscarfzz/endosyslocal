'''
debido a que las primitivas predefinidas de la soaplib (en soaplib.serializers.primitive)
incluyen siempre un atributo "xmlns" vacio que puede causar errores,
aqui las redefino de manera que se elimine dicho atributo.
Es necesario para la conexion con los webservices del SIHGA.
creo que tiene que ver con el atributo del elemento "schema" del wsdl:
elementFormDefault="qualified"

ademas creo el tipo Short, que no esta en las predefinidas de la soaplib
y el Char, que es un unsignedShort
'''

from soaplib.serializers.primitive import _element_to_integer, _element_to_unicode, _generic_to_xml
import soaplib.serializers.primitive
import soaplib.serializers.clazz


class Short:

    @classmethod
    def to_xml(cls,value,name='retval'):
        e = _generic_to_xml(str(value),name,cls.get_datatype(True))
##        e.set('xmlns','')
        return e

    @classmethod
    def from_xml(cls,element):
        return _element_to_integer(element)

    @classmethod
    def get_datatype(cls,withNamespace=False):
        if withNamespace:
            return 'xs:short'
        return 'short'

    @classmethod
    def add_to_schema(cls,added_params):
        pass


class UnsignedShort(Short):

    @classmethod
    def get_datatype(cls,withNamespace=False):
        if withNamespace:
            return 'xs:unsignedShort'
        return 'unsignedShort'


class Char(UnsignedShort):

    @classmethod
    def from_xml(cls,element):
        return _element_to_unicode(element)

    @classmethod
    def get_datatype(cls,withNamespace=False):
        if withNamespace:
            return 'xs:char'
        return 'char'



def oldstyle_super(oldstyle_class):
    '''
    funcion que devuelve la superclass de una clase tipo old-style (o None si no tiene)
    '''
    if len(oldstyle_class.__bases__):
##        print oldstyle_class, oldstyle_class.__bases__[0]
        return oldstyle_class.__bases__[0]
    else:
        return None


# el metodo que "overrideara" al de la clase padre (para los old-style)
def _to_xml(f, value, name='retval'):
    # comprobar si el primer parametro es una instancia o una clase
    if hasattr(f, '__class__'):
        # es una instancia (es un metodo normal)
        e = oldstyle_super(f.__class__).to_xml(f, value, name)
    else:
        # es una clase (es un classmethod)
        e = oldstyle_super(f).to_xml(value, name)

    if 'xmlns' in e.attrib:
        del e.attrib['xmlns']   # elimino el atributo "xmlns"
    return e


# redefino las clases. Usar estas en vez de las de soaplib.serializers.primitive
from new import classobj
Any = classobj('Any', (soaplib.serializers.primitive.Any,), {'to_xml': classmethod(_to_xml)})
String = classobj('String', (soaplib.serializers.primitive.String,), {'to_xml': classmethod(_to_xml)})
Integer = classobj('Integer', (soaplib.serializers.primitive.Integer,), {'to_xml': classmethod(_to_xml)})
DateTime = classobj('DateTime', (soaplib.serializers.primitive.DateTime,), {'to_xml': classmethod(_to_xml)})
Float = classobj('Float', (soaplib.serializers.primitive.Float,), {'to_xml': classmethod(_to_xml)})
Null = classobj('Null', (soaplib.serializers.primitive.Null,), {'to_xml': classmethod(_to_xml)})
Boolean = classobj('Boolean', (soaplib.serializers.primitive.Boolean,), {'to_xml': classmethod(_to_xml)})
Array = classobj('Array', (soaplib.serializers.primitive.Array,), {'to_xml': _to_xml})

##ClassSerializer = soaplib.serializers.clazz.ClassSerializer
##ClassSerializer = type('ClassSerializer', (soaplib.serializers.clazz.ClassSerializer,), {'to_xml': classmethod(_to_xml)})
class ClassSerializer(soaplib.serializers.clazz.ClassSerializer):

##    __metaclass__ = soaplib.serializers.clazz.ClassSerializerMeta

    @classmethod
    def to_xml(cls, value, name='retval'):
        e = super(ClassSerializer, cls).to_xml(value, name)
        if 'xmlns' in e.attrib:
            del e.attrib['xmlns']   # elimino el atributo "xmlns"

        # XXX   los elementos vacios (que son los null) los elimino
        temp = []
        for sub in e:
            if not sub.text:
                temp.append(sub)
        for sub in temp:
            e.remove(sub)
        # ######################################################

        return e

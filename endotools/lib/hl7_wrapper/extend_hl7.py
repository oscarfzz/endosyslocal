import hl7
import logging

log = logging.getLogger(__name__)

# Ampliar las clases de la libreria hl7.

# Ampliar la clase hl7.Segment:
#   poder obtener un campo, p.e. PID.3.1, sin preocuparse
#   de si los indices se salen. Además si se pasa solo el indice
#   del campo se devuelve un hl7.Field
def _segment_get(self, i):
    """
    i:  es un float en que la parte entera es el field
        y la parte decimal es el componente.
        si la parte decimal es 0 (o i es tipo int) se
        devuelve el field.
        (los componentes empiezan en 1, como en Mirth)
    """
    f = int(i)
    c = int(str(float(i)).split('.')[1])

    if f >= len(self):
        return ''
    if c == 0:
        return self[f]
    c -= 1
    if c >= len(self[f]):
        return ''
    return self[f][c]


def _field_get(self, i):
    i -= 1
    if i >= len(self):
        return ''
    return self[i]


def _message_segment_optional(self, segment_id):
    """
    Ampliar hl7.Segment con la función segment_optional().
    Hace lo mismo que segment(), pero sirve para segmentos opcionales, ya que
    si no existe devuelve None en lugar de lanzar una excepción.
    """
    try:
        return self.segment(segment_id)
    except Exception as e:
        return None


def _message_segment_count(self, segment_id):
    """
    Ampliar hl7.Segment con la función segment_count().
    Devuelve el total de veces que aparece un segmento en un mensaje.
    Si no aparece devuelve 0, no lanza una excepción.
    Sirve por ejemplo para saber cuántos PIDs hay en un mensaje.
    
    devuelve un int
    """
    try:
        return len(self.segments(segment_id))
    except Exception as e:
        return 0

hl7.Segment.get = _segment_get
hl7.Field.get = _field_get
hl7.Message.segment_optional = _message_segment_optional
hl7.Message.segment_count = _message_segment_count
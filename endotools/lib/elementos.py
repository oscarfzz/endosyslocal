import logging
import time

from sqlalchemy.sql import and_, or_

from endotools.model.elementos import Elemento
from endotools.model import meta
from misc import *

log = logging.getLogger(__name__)

def elemento_by_id(id):
	""" obtiene el nombre de un elemento a partir de su Id
		si el id es None o no se encuentra, devuelve None
	"""
	q = meta.Session.query(Elemento).filter(Elemento.id == id)
	if q.count():
		return q.one().nombre
	else:
		return None

def elemento_by_valor(valor, campo_id, servicio_id=None):
	""" Obtiene el id de un elemento a partir de su valor
		si el valor es None o no se encuentra, devuelve None.
		
		servicio_id  -  para obtener elementos de campos con ambito "por
						servicio". En caso de ser None, se omite este filtro.
	"""
	if servicio_id is None:
		filtro = and_(Elemento.nombre == valor, Elemento.campo_id == campo_id, Elemento.activo == True)
	else:
		filtro = and_(Elemento.nombre == valor, Elemento.campo_id == campo_id, Elemento.servicio_id == servicio_id, Elemento.activo == True)
	
	q = meta.Session.query(Elemento).filter(filtro)
	if q.count():
		# coge el primero... podria ser que hayan 2 elementos identicos, 
		# en ese caso el .one() fallaría
		return q.all()[0].id 
	else:
		return None

def get_by_id(id):
    return registro_by_id(Elemento, id)

def get_elementos_by_campo_id(campo_id):
	""" obtiene todos los elementos del campo_id enviado por 
		parametro que esten activos
	"""
	q = meta.Session.query(Elemento).filter(and_(Elemento.campo_id == campo_id, \
											Elemento.activo == True))
	if q.count():
		return q.all()
	else:
		return None


def nuevo_elemento():
	# aun no utilizado <- TODO: Revisar este comment si es realmente cierto [IC]
	return Elemento()

def guardar_elemento(elemento):
	# aun no utilizado <- TODO: Revisar este comment si es realmente cierto [IC]
	# XXX utiliza "id" para saber si es un nuevo elemento (id=None) o
	# un elemento existente que se está 
	# modificando (id!=None) <--- NO SE PUEDEN MODIFICAR!
	if elemento.id:
		# modificando, update
		meta.Session.update(elemento)
	else:
		# nuevo, insert
		meta.Session.save(elemento)
	meta.Session.commit()
	# en elemento.id está el nuevo id (en el caso de que fuera un nuevo elemento)

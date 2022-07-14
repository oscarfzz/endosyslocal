#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import time
import endosys.lib.registro as registro
from endosys.model.notificaciones import Notificacion
from endosys.model import meta
from sqlalchemy.sql import and_, or_, not_
from datetime import datetime
import threading
log = logging.getLogger(__name__)
import json

TIPOS_NOTIFICACION = ['TAREA', 'SYS']

def nueva_notificacion(username_destino,tipo_notificacion,contenido,meta_informacion=None,importante=False,username_origen=None):
	
	if not (tipo_notificacion in TIPOS_NOTIFICACION):
		raise Exception("Tipo de notificacion no soportado. Soportados: "+str(TIPOS_NOTIFICACION))

	notificacion = Notificacion()
	notificacion.fecha = datetime.now()
	notificacion.hora = datetime.now()
	
	if username_origen:
		notificacion.username_origen = username_origen
	notificacion.username_destino = username_destino
	
	if importante:
		notificacion.importante = True
	
	notificacion.contenido = contenido
	notificacion.tipo_notificacion = tipo_notificacion

	if meta_informacion:
		notificacion.meta_informacion = json.dumps(meta_informacion)
	
	meta.Session.save(notificacion)
	meta.Session.commit()
	meta.Session.close()
	return notificacion

#ACtualiza la notificacion para marcarla como leida
def marcar_como_leida(id):
	q = meta.Session.query(Notificacion).filter(id == id)
	total = q.count()
	if total == 1:
		notificacion = q.one()
		notificacion.leida = True
		meta.Session.update(notificacion)
		meta.Session.commit()
		return True
	else:
		raise Exception("Notificacion no existe o existen 2 con el mismo ID")

#ACtualiza la notificacion para marcarla como leida
def marcar_como_leida_por_tipo(tipo):
	pass
	'''
	q = Session.query(Noficicacion).filter(id == id)
	total = q.count()
	if total == 1:
		notificacion = q.one()
		notificacion.leida = True
		Session.update(notificacion)
		Session.commit()
		return True
	else:
		raise Exception("Notificacion no existe o existen 2 con el mismo ID")
	'''

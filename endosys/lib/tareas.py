import logging
import time
from pylons.i18n import _
import endosys.lib.registro as registro
from endosys.lib.notificaciones import nueva_notificacion
from endosys.model.tareas import Tarea
from endosys.model.pacientes import Paciente
from endosys.model.medicos import Medico
from endosys.model import meta
from endosys.lib.misc import registro_by_id
from endosys.lib.capturas import _mover_capturas_ruta_correcta
from endosys.lib.informes import _mover_informes_ruta_correcta

from sqlalchemy.sql import and_, or_, not_
from datetime import datetime
import threading
log = logging.getLogger(__name__)
from endosys.controllers.rest.exploraciones import ExploracionesController
import endosys.lib.exploraciones as exploraciones
import gc

TIPOS_TAREA = ['EXP', 'ORG_CAP', 'ORG_INF']
#Sirve para poder usar traducciones adentro de los Hilos porque
#sino sale una excepcion de la libreria de i18n porque no esta
#siendo usada en el hilo principal
STR_HILOS = {}
STR_HILOS["exportar_csv"] = _("Exportar CSV de ")#IDIOMAOK
STR_HILOS["tarea_finalizada"] = _("Tarea finalizada!")#IDIOMAOK
STR_HILOS["ocurrio_error"] = _("Ocurrio un error y no se ha podido finalizar la tarea!")#IDIOMAOK
#Claves para reorganizacion de tareas
STR_HILOS["texto_reorganizacion_descripcion"] = _(u'Reorganización de carpeta de')#IDIOMAOK
STR_HILOS["texto_reorganizacion_resultado"] = _(u'Se han reorganizado: ')#IDIOMAOK
STR_HILOS["capturas"] = _(u"capturas")#IDIOMAOK
STR_HILOS["informes"] = _(u"informes")#IDIOMAOK

#Diccionario para generar una mejor descripcion de la tarea. 
#Por ahora solo se usa la clave str.
KEY_DICT = {}
KEY_DICT["paciente_id"] = {'str':_("Paciente"),'model':Paciente}#IDIOMAOK
KEY_DICT["fecha_min"] = {'str':_("Fecha Inicio")}#IDIOMAOK
KEY_DICT["fecha_max"] = {'str':_("Fecha Fin")}#IDIOMAOK
KEY_DICT["estado"] = {'str':_("Estado")}#IDIOMAOK
KEY_DICT["medico_id"] = {'str':_(u"Médico"),'model':Medico,'campos':['nombre']}#IDIOMAOK
KEY_DICT["_busqueda"] = {'str':_(u"Búsqueda personalizada Nº")}#IDIOMAOK
KEY_DICT["servicio_activo"] = {'str':_("Servicio")}#IDIOMAOK



#crea una nueva tarea con los datos basicos necesarios.
def nueva_tarea(username,tipo_tarea):
	#todo: validar username
	#if username == None:
	#	username = request.environ.get('REMOTE_USER', None)

	if not (tipo_tarea in TIPOS_TAREA):
		raise Exception("Tipo de tarea no soportado. Soportados: "+str(TIPOS_TAREA))

	tarea = Tarea()
	tarea.fecha_comienzo = datetime.now().date()
	tarea.hora_comienzo = datetime.now()
	tarea.username = username
	tarea.estado = 0
	tarea.eliminado = 0
	tarea.descargable = 0
	tarea.tipo_tarea = tipo_tarea

	#Cierra session por si quedo abierta.
	#session = Session()
	meta.Session.save(tarea)
	meta.Session.commit()
	meta.Session.close()
	return tarea


#actualiza una tarea
def update_tarea(tarea):
	#session = Session()
	#actualiza la tarea
	meta.Session.update(tarea)
	meta.Session.commit()
	meta.Session.close()
	return tarea

from multiprocessing import Process, Queue

def crear_hilo(tarea,params):
	#procesar_tarea(tarea, params)
	d = threading.Thread(target=procesar_tarea, name=str(tarea.id), args=(tarea,params))
	d.setDaemon(True)
	d.start()

def procesar_tarea(tarea,params):
	#import pdb; pdb.set_trace()
	#este codigo es necesario para poder usar el h.url_for sin
	#que de errores.
	from endosys.config.routing import make_map
	mapper = make_map()
	t = threading.current_thread()
	t._local = threading.local()

	#tarea en proceso
	tarea.estado = 1
	tarea = update_tarea(tarea)

	try:

		resultado = None
		#procesamiento
		if tarea.tipo_tarea == "EXP":
			resultado = exportar_recurso(tarea,params["recurso"], params, params["format"])
			tarea.descargable = 1
		elif tarea.tipo_tarea == "ORG_CAP":
			resultado = organizar_carpeta_capturas(tarea)
			tarea.descargable = 0
		elif tarea.tipo_tarea == "ORG_INF":
			resultado = organizar_carpeta_informes(tarea)
			tarea.descargable = 0



		tarea.resultado = resultado
		tarea = update_tarea(tarea)

		#tarea finalizada
		tarea.estado = 2
		tarea.fecha_fin = datetime.now().date()
		tarea.hora_fin = datetime.now()
		tarea = update_tarea(tarea)


		#crear notificacion
		contenido_mensaje = '<strong>'+STR_HILOS["tarea_finalizada"]+'</strong><br />'#IDIOMAOK
		contenido_mensaje += tarea.descripcion
		#informacion adicional para la notificacion
		meta_informacion = {}
		meta_informacion = {'recurso': 'tareas', 'id': tarea.id}
		notificacion = nueva_notificacion(tarea.username,"TAREA", contenido_mensaje, meta_informacion)

	except Exception,e:
		#tarea finalizada erroneamente.
		
		log.error(e.message)
		tarea.estado = 3
		tarea.descripcion = STR_HILOS["ocurrio_error"]
		tarea.fecha_fin = datetime.now().date()
		tarea.hora_fin = datetime.now()
		tarea = update_tarea(tarea)

	gc.collect()
	#threading.current_thread().exit()

def exportar_recurso(tarea,recurso,params,format):

	#borra los parametros recurso y params
	#para que no genere conflicto con los controllers
	#que voy a invocar para realizar la exploracion
	if params["recurso"]: del params['recurso']
	if params["format"]: del params['format']
	if params["tipo_tarea"]: del params['tipo_tarea']
	if params["_pagina"]: del params['_pagina']

	if recurso == "exploraciones":
		#grabar descripcion de la tarea
		tarea.descripcion = STR_HILOS["exportar_csv"]+recurso+" - "#IDIOMAOK
		for key, value in params.iteritems():
			try:

				metadatos = KEY_DICT[str(key)]
				
				tarea.descripcion += metadatos['str'] + ": "
				#el caso de que venga un xml en el parametro busqueda para que no falle
				log.debug(type(value))
				if str(key)=="_busqueda" and isinstance(value,unicode):
					tarea.descripcion += "0 - "
					
				else:
					tarea.descripcion += str(value) + " - "

			#	reg = registro_by_id(metadatos['model'],value)
			#	tarea.descripcion += reg[metadatos['campos'][0]]
			
			except Exception,e:
				log.error(e)
				tarea.descripcion += str(key) + ": "
				tarea.descripcion += str(value) + " - "
			
		
		tarea = update_tarea(tarea)

		#enviarle esto a exploraciones
		exploracion_controller = ExploracionesController()
		#session = Session()

		resultado = exploraciones.exportar(exploracion_controller, params, format,meta.Session, str(tarea.id), tarea.username)
		#if meta.Session:
			#meta.Session.close()

		#del resultado

		return resultado

	else:
		raise NotImplementedError("No se puede exportar ese recurso")

def organizar_carpeta_capturas(tarea):
	#import pdb; pdb.set_trace()
	tarea.descripcion = STR_HILOS["texto_reorganizacion_descripcion"] + u' ' + \
						STR_HILOS["capturas"]
	resultado = _mover_capturas_ruta_correcta()
	resultado_str = STR_HILOS["texto_reorganizacion_resultado"] + \
					str(resultado) + u" " + \
					STR_HILOS["capturas"]
	return resultado_str


def organizar_carpeta_informes(tarea):
	#import pdb; pdb.set_trace()
	tarea.descripcion = STR_HILOS["texto_reorganizacion_descripcion"] + u' ' + \
						STR_HILOS["informes"]
	resultado = _mover_informes_ruta_correcta()
	resultado_str = STR_HILOS["texto_reorganizacion_resultado"] + \
					str(resultado) + u" " + \
					STR_HILOS["informes"]
	return resultado_str
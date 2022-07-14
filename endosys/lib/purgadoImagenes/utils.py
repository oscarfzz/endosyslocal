import logging, os, shutil, uuid, time, threading
try:
    import Image
except ImportError:
    from PIL import Image
import endosys.lib.chunks.chunks_process as chunks_process
import endosys.lib.capturas
from endosys.model.capturas import Captura
import datetime
from pylons import config

log = logging.getLogger(__name__)

# SObre Locks http://effbot.org/zone/thread-synchronization.htm
import re


def purgado_imagenes_pacs():
	dummy_datetime = datetime.datetime.strptime('20110101','%Y%m%d')
	time_pattern = re.compile(r'^(?:(?:([01]?\d|2[0-3]):)?([0-5]?\d))$')

	# Tiempo configurado en el que se ejecuta la tarea
	# crea un array de tiempos con la informacion configurada en el ini
	time_schedules = config.get('PURGADO.PROCESO_HORA', '')	
	times_array = []
	match = time_pattern.match(time_schedules)
	for times in time_schedules.split(","):
		if time_pattern.match(time_schedules):
			try:
				hora = int(times.split(":")[0])
				minuto = int(times.split(":")[1])
				if hora >= 0 and hora <= 23 and minuto >=0 and minuto <= 59:
					times_array.append({'hour': int(times.split(":")[0]) , 'minute': int(times.split(":")[1])})
			except Exception as e:
				log.error(e) #mal formato no se toma en cuenta.

	# ciclo que recorre y se ejecuta cuando es la hora indicada en el ini
	while True and len(times_array)>0:
		# Hora actual, es comparada con la hora programada
		time_now = datetime.datetime.now()

		# Busca en todos los horarios disponibles configurados, si el tiempo actual es igual
		# a alguno de ellos
		purgar_imagenes = False
		for times in times_array:
			if time_now.hour==times["hour"] and time_now.minute==times["minute"]:
				purgar_imagenes = True

		from endosys.lib.capturas import _purgar_capturas_pacs
		if purgar_imagenes:
			_purgar_capturas_pacs()
			time.sleep(60)
		
		# Espera 10 segundos hasta intentar de nuevo para saber si ya es la hora de ejecurse
		time.sleep(10)

def comenzar_hilo_purgado():
	d = threading.Thread(target=purgado_imagenes_pacs)
	d.setDaemon(True)
	d.start()
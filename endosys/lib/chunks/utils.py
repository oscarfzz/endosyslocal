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
import re

log = logging.getLogger(__name__)

# SObre Locks http://effbot.org/zone/thread-synchronization.htm
def try_join_chunk_and_set_disponible(archivo):
	# queda frenado hasta que este disponible.
	# el with lock_chunk hace un adquire y espera hasta que este disponible y 
	# hace un release cuando sale del lock
	error = False

	# Rutas
	ruta_chunks = config['pylons.paths']['chunks']
	ruta_capturas = config['pylons.paths']['capturas']

	# Crea la carpeta donde se guardan los ficheros unidos si no existe
	ruta_chunks_ficheros =os.path.join(ruta_chunks, 'ficheros')
	if not os.path.isdir(ruta_chunks_ficheros):
		os.mkdir(ruta_chunks_ficheros)

	# Intenta regenerar el archivo, en (carpeta_chunks)/ficheros/nombre_archivo_original.ext
	chunks_uuid = archivo.split('.')[0]

	path_chunk = os.path.join(ruta_chunks, archivo)
	
	if not os.path.isfile(path_chunk):
		# La ruta es invalida
		raise Exception('Ruta no existe')

	try:
		chunk = open(path_chunk, 'rb')

		#obtiene informacion del header
		chunk_header = chunks_process._read_chunk_header(chunk)
		chunk.close()
		
		# Une los chunks
		chunks_process.join_chunks(ruta_chunks, chunks_uuid, os.path.join(ruta_chunks_ficheros), chunks_uuid)

		# Busca la captura no disponible relacionada con ese uuidasdad
		id = endosys.lib.capturas._get_captura_by_uuid(Captura, chunks_uuid)	
		
		# obtiene el origen y el destino
		origen = os.path.join(ruta_chunks_ficheros, chunks_uuid)
		filename_dst = str(id) + "." + chunk_header["filename"].split(".")[1]

		# Copia los archivos a la ruta de las capturas
		ruta_capturas = endosys.lib.capturas._construir_ruta(ruta_capturas, None, chunk_header['exploracion_id'])
		destino = os.path.join(ruta_capturas, filename_dst)
		
		#print ruta_capturas
		copy_error = False
		try:
			shutil.copy2(origen, destino)
		except Exception as e:
			log.error(e)
			# no se pudo copiar, seguramente porque el destino no esta disponible
			copy_error = True

		if not copy_error:
			# si no hay error entonces no borra el archivo
			os.remove(origen)
			endosys.lib.capturas._set_disponible(Captura, chunks_uuid)
			endosys.lib.capturas._create_thumbnail( endosys.lib.capturas._archivo(id) )

			# Si no hay ningun fallo entonces borro los chunks.
			chunks_process.delete_chunks(ruta_chunks, chunks_uuid)

	except chunks_process.ChunkErrorMissing as e:
		log.error(e) # si falta alguno no pasa nada, aqui solo lo esta intentando
	except Exception as e:
		log.error(e)


def buscar_chunks_no_generados():
	dummy_datetime = datetime.datetime.strptime('20110101','%Y%m%d')
	time_pattern = re.compile(r'^(?:(?:([01]?\d|2[0-3]):)?([0-5]?\d))$')


	# Tiempo configurado en el que se ejecuta la tarea
	# crea un array de tiempos con la informacion configurada en el ini
	time_schedules = config.get('EWC_MODO.PROCESO_CHUNKS.TIEMPOS', '')	
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
		process_chunks = False
		for times in times_array:
			if time_now.hour==times["hour"] and time_now.minute==times["minute"]:
				process_chunks = True

		# si process_chunk es True es porque el horario coincide con alguno configurado en el ini
		if process_chunks:
			log.debug("Realizando tarea de proceso de chunks") 
			# Espera hasta que no este bloqueado el recurso de tratar de unir.
			with config['pylons.g'].lock_chunks:
				
				ruta_chunks = config['pylons.paths']['chunks']
				
				#todos los archivos del directorio chunks
				dir_files = os.listdir(ruta_chunks)

				#se queda con los archivos que terminan en "1.chunk" para tratar de reconstruir
				files_chunks = [elem for elem in dir_files if elem[-8:] == ".1.chunk"]
				while len(files_chunks) > 0 and not config['pylons.g'].event_chunks.is_set():
					
					# extrae un archivo en intenta procesarlo
					archivo = files_chunks.pop()
					try_join_chunk_and_set_disponible(archivo)
				
			# termina de ejecutarse, para que no se ejecute 2 veces en el mismo minuto
			# hace pasar 60 segundos para que si o si en el proximo while no entre porque esta en el mismo minuto 
			time.sleep(60) 
		
		# Espera 10 segundos hasta intentar de nuevo para saber si ya es la hora de ejecurse
		time.sleep(10)

def comenzar_hilo_chunks():
	d = threading.Thread(target=buscar_chunks_no_generados)
	d.setDaemon(True)
	d.start()

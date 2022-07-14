"""
EndoTools Web 2.4.10

Procesado de Chunks.

IMPORTANTE:
	Este fichero es compartido entre los proyectos:
		EndoTools Web
		Cliente EndoTools Web

	De esta manera las dos aplicaciones comparten la misma implementación para
	procesar los chunks.

TODO:
	qué ocurre si se interrumpe un split_file() quedando a medias, con algunos chunks creados, al reiniciar el split?

	al reconstruir chunks, ir eliminandolos a medida que se va creando y escribiendo
	el fichero destino... si hay algun problema luego que se pueda reanudar la reconstruccion
	con el fichero a medias y los chunks restantes. Asi se ocupa menos espacio de disco.
"""
import os
import time
import uuid
import portalocker

#   (int) version del formato de los ficheros chunk. Se debe incrementar si
#           se modifica el formato (cabecera, etc...). Siempre se tiene que mantener
#           el formato en la cabecera de la version ("ver" + 5 caracteres + #13#10)
CURRENT_CHUNK_VERSION = 3

#   Tipos de chunks
class CHUNKTYPES:
	DESCONOCIDO =				'DESCONOCIDO'
	CAPTURA_DE_EXPLORACION =	'CAPTURA_DE_EXPLORACION'

chunk_size =        1024*1024*4 # 4 MB (en bytes)


class ChunkError(Exception):
	pass

class ChunkErrorMissing(ChunkError):
	"""
	Se lanza cuando falta algún fichero chunk para poder regenerar el archivo original
	"""
	pass

class ChunkErrorIncorrect(ChunkError):
	"""
	Se lanza si un fichero chunk es incorrecto
	"""
	pass


def _write_chunk_header(chunk_version, fdest, filename, num, chunkscount, exploracion_id, paciente_id, chunks_uuid, chunk_type):
	"""
	escribir la cabecera del chunk. Se controla la versión del formato a emplear.
	se escribe directamente en el fichero destino.

		chunk_version   int     version de formato de fichero del chunk que se quiere generar
		fdest           file    archivo donde se escribe el chunk (abiero como "rw", normalmente en posicion 0)
		filename        str     nombre del archivo a partir, para escribir en el header (sin ruta)
		num             int     número del chunk
		chunkscount     int     total de chunks (se ha calculado previamente)
		exploracion_id  int/str el id de la exploracion. Es opcional.
		paciente_id     int/str el id del paciente. Es opcional.
		chunks_uuid     str     UUID del archivo a partir, representado como un string hex de 32 caracteres
		chunk_type      str     indica el tipo de archivo. Debe ser uno de los valores de CHUNKTYPES
	"""

	# funciones reutilizables entre versiones. El sufijo _v1, _v2, etc...
	# indica en que version se introdujo la funcion, pero se puede reutilizar
	# en versiones posteriores si no cambia la implementacion.
	class funcs:
		@staticmethod
		def write_chunk_version():
			"""
			todas las versiones tienen que escribir el nº de version de la misma manera.
			"""
			fdest.write( 'ver%s\r\n' %	str(chunk_version).ljust(5) )

		@staticmethod
		def write_blank_line():
			fdest.write( '\r\n' )

		# v1
		@staticmethod
		def test_v1():
			assert len(str(exploracion_id)) <= 12
			assert len(str(paciente_id)) <= 12
			assert chunkscount <= 99999999
			assert num <= 99999999

		@staticmethod
		def write_chunk_num_total_v1():
			fdest.write( '%s/%s \r\n' %	(str(num).rjust(8), str(chunkscount).ljust(8)) )

		@staticmethod
		def write_filename_v1():
			fdest.write( '%s\r\n' %		os.path.basename(filename).ljust(120)[:120] )

		@staticmethod
		def write_creation_time_v1():
			fdest.write( '%s\r\n' %		time.strftime('%d/%m/%Y  %H:%M:%S', time.localtime(os.path.getctime(filename))) )

		@staticmethod
		def write_paciente_exploracion_ids_v1():
			if paciente_id:
				p = str(paciente_id)
			else:
				p = ''
			if exploracion_id:
				e = str(exploracion_id)
			else:
				e = ''
			fdest.write( '%s/%s \r\n' %	(p.rjust(12), e.ljust(12)) )

		# v2
		@staticmethod
		def write_uuid_v2():
			fdest.write( '%s\r\n' %	chunks_uuid.ljust(32)[:32])

		@staticmethod
		def write_type_v2():
			fdest.write( '%s\r\n' %	chunk_type.ljust(60)[:60])


	def write_v1():
		"""
		FORMATO CABECERA (204 bytes):
			version del formato de chunk	8 bytes + #13#10            ver99999
		   	Nº chunk / total chunks			18 bytes + #13#10           99999999/99999999_
			nombre archivo					120 bytes + #13#10			xxxx[...]xxxx.xxx
			fecha y hora creacion archivo	20 bytes + #13#10   		dd/mm/aaaa  hh:mm:ss
			paciente_id / exploracion_id	26 bytes + #13#10           999999999999/999999999999_ (son opcionales, puede ser todo espacios)
			salto de linea					#13#10
		"""
		# comprobaciones
		funcs.test_v1()
		# escribir la cabecera
		funcs.write_chunk_version()
		funcs.write_chunk_num_total_v1()
		funcs.write_filename_v1()
		funcs.write_creation_time_v1()
		funcs.write_paciente_exploracion_ids_v1()
		funcs.write_blank_line()

	def write_v2():
		"""
		Se añade:
			UUID de los chunks  Identificador único de todos los chunks que
								componen un archivo.
			TIPO de chunk		un identificador que indica qué es este archivo
								para que el servidor de EndoTools sepa cómo procesarlo.

		FORMATO CABECERA (300 bytes):
			version del formato de chunk
			UUID de los chunks              32 bytes + #13#10           f32d54c3186d43f085f8eec606c96352 (p.ej.)
			Tipo del chunk                  60 bytes + #13#10           CAPTURA_DE_EXPLORACION______________________________________ (p.ej.)
			Nº chunk / total chunks
			nombre archivo
			fecha y hora creacion archivo
			paciente_id / exploracion_id
			salto de linea
		"""
		# comprobaciones
		funcs.test_v1()
		# escribir la cabecera
		funcs.write_chunk_version()
		funcs.write_uuid_v2()
		funcs.write_type_v2()
		funcs.write_chunk_num_total_v1()
		funcs.write_filename_v1()
		funcs.write_creation_time_v1()
		funcs.write_paciente_exploracion_ids_v1()
		funcs.write_blank_line()

	def write_v3():
		"""
		Se cambia el orden de los campos, agrupando los que contienen información
		del archivo original, y por lo tanto son iguales entre todos los chunks.
		(realmente solo se ha movido el "nº/total chunks" arriba, asi todos los
		siguientes son ya la info del archivo original)

		FORMATO CABECERA (300 bytes):
			version del formato de chunk
			Nº chunk / total chunks
			UUID de los chunks
			Tipo del chunk
			nombre archivo
			fecha y hora creacion archivo
			paciente_id / exploracion_id
			salto de linea
		"""
		# comprobaciones
		funcs.test_v1()
		# escribir la cabecera
		funcs.write_chunk_version()
		funcs.write_chunk_num_total_v1()
		funcs.write_uuid_v2()
		funcs.write_type_v2()
		funcs.write_filename_v1()
		funcs.write_creation_time_v1()
		funcs.write_paciente_exploracion_ids_v1()
		funcs.write_blank_line()


	#   ejecutar la funcion correspondiente a la version indicada
	if chunk_version > CURRENT_CHUNK_VERSION:
		raise Exception('No se puede generar un "chunk" con version de formato de fichero %s. Esta implementacion solo es compatible hasta la version %s.' % (str(chunk_version), str(CURRENT_CHUNK_VERSION)))
	eval('write_v%s' % chunk_version)()


def _write_chunk_content(fsrc, fdest, chunksize):
	"""
	escribir el contenido de un chunk. No se controla la versión, en principio siempre es igual.
	se lee directamente del fichero fuente y se escribe en el destino.
	Se tiene que haber escrito antes la cabecera.

		fsrc            file    archivo a partir (abierto como "rb", y en la posición de inicio de este chunk)
		fdest           file    archivo donde se escribe el chunk (abiero como "rw", normalmente en posicion 0)
		chunksize       int     tamaño en bytes del chunk
	"""
	fdest.write( fsrc.read(chunksize) )


def split_file(filename, destdir, chunksize, chunktype, exploracion_id = 0, paciente_id = 0, preset_uuid = None):
	"""
	Parte un fichero en varios trozos (chunks).
	Puede fallar si el archivo a partir está en uso, o si no se puede escribir
	en el destino (falta espacio, permisos, etc...).
	Los archivos chunk creados se nombran con el UUID generado y un número consecutivo.

		filename    	nombre del fichero a partir.
		destdir     	carpeta de destino donde se crearán los trozos.
		chunksize   	tamaño de cada trozo, en bytes.
        chunktype   	tipo de archivo. Debe ser uno de los valores de CHUNKTYPES
		paciente_id     el id del paciente. Es opcional.
		exploracion_id  el id de la exploracion. Es opcional.
		preset_uuid		El nombre del chunk generado. Opcional 
		
	"""

	
	
	# obtener el tamaño del fichero en bytes
	filesize = os.stat(filename).st_size

	# calcular el número de chunks que se han de crear
	chunkscount = filesize/chunksize
	if (filesize % chunksize):
		chunkscount += 1

	# abrir el fichero para ir leyendo los chunks
	fsrc = open(filename, 'rb')
	try:
		# crear los chunks leyendo el fichero
		chunknames = []
		num = 1

		#Busca si viene por parametro el uuid, sino lo genera
		chunks_uuid = preset_uuid
		if chunks_uuid is None:
			chunks_uuid = uuid.uuid4().hex
		

		for i in range(0, filesize+1, chunksize):
			if i >= filesize: break # (si es exacto se creaba un fichero de 0 bytes)
			chunkname = "%s.%s.chunk" % (chunks_uuid, num)
			if destdir:
				chunkname = os.path.join(destdir, chunkname)
			chunknames.append(chunkname)
			fdest = open(chunkname, 'wb')
            # Bloquea el fichero para que no se pueda abrir por otro proceso hasta que no se haya cerrado.
			# Asi se evita que se intente enviar el chunk cuando aun no se ha escrito por completo.
			#   XXX usar threading.lock ???
			portalocker.lock(fdest, portalocker.LOCK_EX)
			try:
				_write_chunk_header(CURRENT_CHUNK_VERSION, fdest, filename, num, chunkscount, exploracion_id, paciente_id, chunks_uuid, chunktype)
				_write_chunk_content(fsrc, fdest, chunksize)
			except Exception as e:
				log.error(e)
				# si no se puede crear el chunk, antes de lanzar la excepcion intenta cerrar el fichero y eliminarlo
				try:
					fdest.close()
					os.remove(chunkname)
				except Exception as e:
					log.error(e)
				raise
			fdest.close()
			num = num + 1
	finally:
		fsrc.close()

	return chunks_uuid 

def _read_chunk_header(fsrc):
	"""
	leer la cabecera del chunk. Se controla la versión del formato a emplear.
	se lee directamente del fichero fuente (chunk).

		fsrc            file    archivo chunk (abierto como "rb", en la posición 0)

	Devuelve un dict con esta información:
		num             int     número del chunk
		total     		int     total de chunks (se ha calculado previamente)
		chunks_uuid     str     UUID del archivo a partir, representado como un string hex de 32 caracteres
		chunk_type      str     indica el tipo de archivo. Debe ser uno de los valores de CHUNKTYPES
		filename        str     nombre del archivo a partir, para escribir en el header (sin ruta)
		ctime           ...     fecha y hora de creacion del archivo original (lo mismo que os.path.getctime())
		paciente_id     str		el id del paciente. Es opcional, puede ser None.
		exploracion_id  str		el id de la exploracion. Es opcional, puede ser None.
	"""

	# funciones reutilizables entre versiones. El sufijo _v1, _v2, etc...
	# indica en que version se introdujo la funcion, pero se puede reutilizar
	# en versiones posteriores si no cambia la implementacion.
	class funcs:
		@staticmethod
		def read_chunk_version():
			fsrc.read(3)				#   ver(3)
			return int(fsrc.read(7))	#   version(5)\r\n

		@staticmethod
		def read_blank_line():
			fsrc.read(2)         		#   \r\n

		# v3
		@staticmethod
		def read_chunk_num_total_v3():
			num = int(fsrc.read(8))     #   num(8)
			fsrc.read(1)    			#	/
			total = int(fsrc.read(8))   #   total(8)
			fsrc.read(1)    			#	_
			fsrc.read(2)    			#   \r\n
			return num, total

		@staticmethod
		def read_filename_v3():
			filename = fsrc.read(120).strip() # nombre del archivo(120)
			fsrc.read(2)    			#   \r\n
			return filename

		@staticmethod
		def read_creation_time_v3():
			fechahora = fsrc.read(20)   #   dd/mm/aaaa  hh:mm:ss(20)
			fsrc.read(2)    			#   \r\n
			return time.mktime( time.strptime(fechahora, '%d/%m/%Y  %H:%M:%S') )
			#   devuelve "time expressed in seconds since the epoch", lo mismo que os.path.getctime()

		@staticmethod
		def read_paciente_exploracion_ids_v3():
			paciente_id = fsrc.read(12) 	#   paciente_id(12)
			if paciente_id.strip():
				paciente_id = paciente_id.strip()
			else:
				paciente_id = None
			fsrc.read(1)    				#	/
			exploracion_id = fsrc.read(12)	#   exploracion_id(12)
			if exploracion_id.strip():
				exploracion_id = exploracion_id.strip()
			else:
				exploracion_id = None
			fsrc.read(1)    			#	_
			fsrc.read(2)    			#   \r\n
			return paciente_id, exploracion_id

		@staticmethod
		def read_uuid_v3():
			uuid = fsrc.read(32)	#   uuid(32)
			fsrc.read(2)			#   \r\n
			return uuid

		@staticmethod
		def read_type_v3():
			tipo = fsrc.read(60).strip() # uuid(60)
			fsrc.read(2)			#   \r\n
			return tipo


	# NOTA: No se ha implementado la lectura de las versiones 1 y 2.

	def read_v3():
		"""
		Se cambia el orden de los campos, agrupando los que contienen información
		del archivo original, y por lo tanto son iguales entre todos los chunks.
		(realmente solo se ha movido el "nº/total chunks" arriba, asi todos los
		siguientes son ya la info del archivo original)

		FORMATO CABECERA (300 bytes):
			version del formato de chunk	8 bytes + #13#10            ver99999
			Nº chunk / total chunks			18 bytes + #13#10           99999999/99999999_
			UUID de los chunks              32 bytes + #13#10           f32d54c3186d43f085f8eec606c96352 (p.ej.)
			Tipo del chunk                  60 bytes + #13#10           CAPTURA_DE_EXPLORACION______________________________________ (p.ej.)
			nombre archivo					120 bytes + #13#10			xxxx[...]xxxx.xxx
			fecha y hora creacion archivo	20 bytes + #13#10   		dd/mm/aaaa  hh:mm:ss
			paciente_id / exploracion_id	26 bytes + #13#10           999999999999/999999999999_ (paciente_id es opcional, puede ser todo espacios)
			salto de linea					#13#10
		"""
		result = {}
		# leer la cabecera
		result['num'], result['total'] =					funcs.read_chunk_num_total_v3()
		result['chunks_uuid'] =								funcs.read_uuid_v3()
		result['chunk_type'] =								funcs.read_type_v3()
		result['filename'] =								funcs.read_filename_v3()
		result['ctime'] =									funcs.read_creation_time_v3()
		result['paciente_id'], result['exploracion_id'] =	funcs.read_paciente_exploracion_ids_v3()
		funcs.read_blank_line()
		return result


	#   leer la version y ejecutar la funcion correspondiente a la version indicada
	chunk_version = funcs.read_chunk_version()
	if chunk_version in (1,2):
		raise Exception('No se ha implementado la lectura de un "chunk" con version de formato de fichero %s.' % str(chunk_version))
	if chunk_version > CURRENT_CHUNK_VERSION:
		raise Exception('No se puede leer un "chunk" con version de formato de fichero %s. Esta implementacion solo es compatible hasta la version %s.' % (str(chunk_version), str(CURRENT_CHUNK_VERSION)))
	return eval('read_v%s' % chunk_version)()


def _read_chunk_content(fsrc, fdest):
	"""
	leer el contenido de un chunk. No se controla la versión, en principio siempre es igual.
	se lee directamente del fichero fuente (chunk) y se escribe en el destino (archivo original).
	Se tiene que haber leido antes la cabecera del chunk.

		fsrc            file    archivo chunk (abierto como "rb", y en la posición de inicio del contenido del chunk, despues de la cabecera)
		fdest           file    archivo donde se escribe del archivo (abiero como "rw", en la posicion del final para seguir reconstruyendo)
	"""
	fdest.write( fsrc.read() )


def join_chunks(srcdir, chunks_uuid, destdir, filename = ''):
	"""
	Junta varios trozos (chunks) en un fichero.
	Puede fallar si alguno de los chunks está en uso, o si no se puede escribir
	en el destino (falta espacio, permisos, etc...).

		srcdir          carpeta de origen donde están los chunks.
		chunks_uuid     uuid de los chunks, para localizar los ficheros chunk.
		  (en vez de srcdir y uuid se podria usar un solo filename, y que se procese...)
		destdir         carpeta de destino donde se creará el fichero original.
		filename        nombre del fichero a crear. Opcional, si se omite se crea con el nombre original.

	  Información a devolver, leida de los headers (chunkinfo?):
        chunktype
		paciente_id
		exploracion_id

	TODO: controlar bloqueos, etc... para que no haya problemas entre threads accediendo a los mismos archivos
	"""
	# leer los ficheros chunk secuencialmente
	num = 1
	total = None
	fdest = None
	try:
		while True:
			chunkfilename = os.path.join(srcdir, '%s.%s.chunk' % (chunks_uuid, num))
			if not os.path.isfile(chunkfilename):
				raise ChunkErrorMissing('No se ha encontrado el fichero chunk %s' % chunkfilename)
			fsrc = open(chunkfilename, 'rb')
			try:
				# leer header
				header = _read_chunk_header(fsrc)
				# si se trata del primero extraer el total y comprobar si existen los chunks
				if num == 1:
					header_1 = header.copy()
					total = header_1['total']
					for i in range(1, total + 1):
						x = os.path.join(srcdir, '%s.%s.chunk' % (chunks_uuid, i))
						if not os.path.isfile(x):
							raise ChunkErrorMissing('No existen todos los ficheros chunk para poder reconstruir el archivo. Falta %s' % x)
					# todo parece correcto, crear el archivo de destino
					if not filename: filename = header_1['filename']
					fdest = open(os.path.join(destdir, filename), 'wb')
				# para todos los chunks, comprobar que la cabecera sea correcta
				if not header['num'] ==				num or\
				  not header['total'] ==			total or\
				  not header['chunks_uuid'] ==		chunks_uuid or\
				  not header['chunk_type'] ==		header_1['chunk_type'] or\
				  not header['filename'] ==			header_1['filename'] or\
				  not header['ctime'] ==			header_1['ctime'] or\
				  not header['paciente_id'] ==      header_1['paciente_id'] or\
				  not header['exploracion_id'] ==	header_1['exploracion_id']:
					raise ChunkError('La información de la cabecera del chunk es incorrecta, o no consistente con la del resto de chunks (%s)' % chunkfilename)
				# leer el contenido y escribirlo en el archivo que se esta reconstruyendo
				_read_chunk_content(fsrc, fdest)
			finally:
				fsrc.close()

			if num == total: break # si es el ultimo, salir del bucle
			num = num + 1

	finally:
		if fdest:
			fdest.close()

	# ya se han escrito todos los chunks correctamente, asi que eliminarlos
	#for i in range(1, total + 1):
	#	x = os.path.join(srcdir, '%s.%s.chunk' % (chunks_uuid, i))
	#	os.remove(x)

'''
	Borra los chunks con el uuid pasado por parametro
	-------------------------------------------------
	Parametros:
		- chunk_dir: el directorio donde se encuentran los chunks
		- uuid_name: el uuid de los chunks que se quieren borrar
'''
def delete_chunks(chunk_dir, uuid_name):

	# Crea la ruta completa del primer chunk para obtener informacion del encabezad
	chunk1_path = os.path.join(chunk_dir, '%s.%s.chunk' % (uuid_name, 1))

	# Controla si existe
	if not os.path.isfile(chunk1_path):
		raise ChunkErrorMissing('No se ha encontrado el fichero chunk %s' % chunk1_path)

	#obtiene la informacion del encabezado
	chunk1_file = open(chunk1_path, 'rb')
	header = _read_chunk_header(chunk1_file)
	chunk1_file.close()
	total = header['total']
	
	# recorre 1 a 1 controlando que existan, si no existen todos los chunks no los borra
	for i in range(1, total + 1):
		chunk_part_path = os.path.join(chunk_dir, '%s.%s.chunk' % (uuid_name, i))
		if not os.path.isfile(chunk_part_path):
			raise ChunkErrorMissing('No existen todos los ficheros chunk para poder borrar. Falta %s' % chunk_part_path)

	# recorre 1 a 1 controlando borrando
	for i in range(1, total + 1):
		chunk_part_path = os.path.join(chunk_dir, '%s.%s.chunk' % (uuid_name, i))
		os.remove(chunk_part_path)
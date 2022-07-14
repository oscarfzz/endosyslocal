import os
import sys
import zipfile
import shutil
import logging
import datetime



logging.basicConfig(filename='actualizar_ficheros.log', level='INFO')
log = logging.getLogger(__name__)

log.addHandler( logging.StreamHandler(sys.stdout) )

##log.info
##log.debug
##log.error

def cargar_lista_updates(version):
	#ejemplo ficheros update "endosysapp-update-2.3.1.12-2.3.1.3"
	versiones_disponibles = []
	ficheros = os.listdir('update_archives')
	print "Selecciona la version a la que desea actualizar:"

	for f in ficheros:
		if 'endosysapp-update' in f:
			a = str(f).split('-')
			try:
				if version == a[2]:
					if '.zip' in a[3]:
						versiones_disponibles.append( os.path.splitext(a[3])[0] )
						print "--->   ", os.path.splitext(a[3])[0]
			except:
				pass

	if not len(versiones_disponibles) > 0:
		raise Exception("No hay disponible ningun update")


	return versiones_disponibles

def consultar_version_actual():
	f = open("version.txt")
	try:
		version = f.readline().replace("\n","")
	finally:
		f.close()
	return version

def descomprimir_zip(filezip):

	#path_zip = 'update_archives\\'+filezip
	path_zip = os.path.join('update_archives', filezip)

	zip = zipfile.ZipFile(path_zip)
	zip.extractall(path='update_archives')
	try:

		path_carpeta_descomprimida = path_zip.replace(".zip","")
		# trabajar con rutas absolutas
		path_lectura = os.path.join(os.getcwd(), path_carpeta_descomprimida)


		ejecutar_delete(path_lectura)
		recorrer_update(path_lectura)

	finally:
		#eliminar la carpeta descomprimida
		shutil.rmtree(path_lectura)

def recorrer_update(path_lectura,path_destino=os.getcwd()):

	ficheros = os.listdir(path_lectura)

	for f in ficheros:

		sub_element = path_lectura + "\\" + f
		#print "subelement-->",sub_element

		if os.path.isfile(sub_element):
			logica_ejecucion_update(path_destino, True, sub_element, f )

		if os.path.isdir(sub_element):
			path_siguiente_lectura = path_lectura +'\\' + f
			path_siguiente_destino = path_destino +'\\' + f
			logica_ejecucion_update(path_siguiente_destino, False)
			recorrer_update(path_siguiente_lectura,path_siguiente_destino)

def logica_ejecucion_update(destino, esfichero, origen = None, nameFile = None):
	"""
		en esta funcion se implementa la logica de copiar los ficheros de la
		carpeta del paquete de actualizacion a la carpeta de endosys

		Si es un directorio
			si no existe --> crear carpeta
			si existe --> no hacer nada
		Si es un fichero
			si exite ---> eliminar existente y copiar nuevo
			si no existe ---> copiar nuevo
	"""

	if esfichero:
		sub_element_destino = destino + "\\" + nameFile

		if os.path.exists(sub_element_destino):
			log.info("modificar fichero--->"+sub_element_destino)
			os.remove(sub_element_destino)

		else:
			log.info("nuevo fichero--->"+sub_element_destino)

		shutil.copyfile(origen,sub_element_destino)
	else:
		if not os.path.exists(destino):
			log.info('Nuevo directorio--->'+destino)
			os.mkdir(destino)


def ejecutar_delete(path_lectura):

	path_delete = path_lectura + "\DELETE.txt"

	if not os.path.exists(path_delete):
		log.info("No existe el fichero DELETE.txt")
		return

	archi=open(path_delete,'r')
	try:
		archi_str = archi.read()

		# El archivo DELETE.txt se genera automaticamente desde subversion,
		# con la opcion compare revisions -> save list of selected files to...
		# y parece que siempre lo genera en formato UTF-16.
		archi_str = archi_str.decode('utf_16')
		lineas = archi_str.split('\n')

		for li in lineas[1:]:

			if li.strip() == "": continue

			if li.startswith("custom") == False:
				#SI empieza por custom se omitira el delete
				#por seguridad de que no elimine la carpeta CUSTOM y perder datos del cliente


				ruta_delete = os.path.join(os.getcwd(), li.replace("/","\\"))


				if os.path.exists(ruta_delete):

					if os.path.isdir(ruta_delete):

						try:
							shutil.rmtree(ruta_delete)
							log.info("eliminar directorio--->"+ruta_delete)
							#print "eliminar directorio--->",ruta_delete
						except Exception as e:
							log.info('Ha ocurrido un ERROR al eliminar el directorio '+ ruta_delete)
							#print 'Ha ocurrido un ERROR al eliminar el directorio ', ruta_delete
							raise e
					else:
						try:
							os.remove(ruta_delete)
							log.info("eliminar fichero--->"+ruta_delete)
							#print "eliminar fichero--->",ruta_delete
						except Exception as e:
							log.error('Ha ocurrido un ERROR al eliminar el fichero' + ruta_delete)
							#print 'Ha ocurrido un ERROR al eliminar el fichero', ruta_delete
							raise e

	finally:
		archi.close()
		os.remove(path_delete)


if __name__ == "__main__":

	log.info(datetime.datetime.now())
	version = consultar_version_actual()
	print "Version actual: ",version
	versiones_disponibles =	cargar_lista_updates(version)
	actualizacion = raw_input("Introduce la version a la que desea actualizar: ")


	if actualizacion in versiones_disponibles:
		log.info("La actualizacion seleccionada es: %s" % actualizacion)
		filezip = 'endosysapp-update-%s-%s.zip' % (version, actualizacion)
		try:
			descomprimir_zip(filezip)
			log.info("Endosys se ha actualizado correctamente")
		except:
			log.error("ERROR - Endosys NO se ha actualizado correctamente")
			raise

	else:
		print "La actualizacion introducida no existe"
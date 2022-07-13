#Este fichero se encarga de pasar un listado de poblaciones de un fichero CSV a
#la tabla de poblaciones de base de datos de endotoolsweb.
#caracter del fichero CSV:
#   LIMITADO POR ;
#   La primera linea del fichero ha de contener el primer valor, no los titulos de los campos
#   la primera columna ha de ser el codigo de la poblacion
#   la segunda columna ha de ser la descripcion de la poblacion
#   el fichero csv ha de estar a la misma altura que este fichero
#IMPORTANTE para cada instalación se han de configurar las constantes de este fichero
#este script NO verifica si existe ya la poblacion

# CONFIGURACION B.D
HOST_ENDOTOOLS = 'host'
USER_ENDOTOOLS = 'user'
PASS_ENDOTOOLS = 'password'
BBDD_ENDOTOOLS = 'endotoolsweb'

# configuracio fichero
RUTA = 'poblaciones.csv'


from sqlalchemy import *
import csv


# cadena de conexión a BBDD de endotools
endotools = {}
endotools['CONN'] =  'mssql://%s:%s@%s/%s' % (USER_ENDOTOOLS, PASS_ENDOTOOLS, HOST_ENDOTOOLS, BBDD_ENDOTOOLS)

contador = 0
poblaciones_endotools = None

def ini_endotools():
	global endotools, poblaciones_endotools, contador

	# iniciar sqlachemy, conexión a la bbdd y tabla de pacientes
	endotools['engine'] = create_engine(endotools['CONN'])
	endotools['metadata'] = MetaData()
	endotools['metadata'].bind = endotools['engine']
	poblaciones_endotools = Table('Poblaciones', endotools['metadata'], autoload=True)
	contador = 0
	leer_fichero_csv()

def leer_fichero_csv():
	global endotools, poblaciones_endotools, contador
	csvfile = open(RUTA, 'rb')
	try:
		csvreader = csv.reader(csvfile, delimiter=';', quotechar='"', quoting = csv.QUOTE_NONE, escapechar = '\\')
		contador = 0
		for row in csvreader:
			codigo = row[0]
			descripcion = row[1]
			rslt = poblaciones_endotools.insert().values(codigo=codigo, nombre=descripcion).execute()
			print "registro actual: %s" % (row)
			contador = contador + 1
		print "COMPLETADO. Se han resgistrado %s poblaciones" % (contador)
	finally:
		csvfile.close()



ini_endotools()

#Este fichero se encarga de pasar un listado de provincias de un fichero CSV a
#la tabla de provincias de base de datos de endosysapp.
#caracter del fichero CSV:
#   LIMITADO POR ;
#   La primera linea del fichero ha de contener el primer valor, no los titulos de los campos
#   la primera columna ha de ser el codigo de la provincia
#   la segunda columna ha de ser la descripcion de la provincia
#   el fichero csv ha de estar a la misma altura que este fichero
#IMPORTANTE para cada instalación se han de configurar las constantes de este fichero
#este script NO verifica si existe ya la PROVINCIA

# CONFIGURACION B.D
HOST_ENDOSYS = 'host'
USER_ENDOSYS = 'user'
PASS_ENDOSYS = 'password'
BBDD_ENDOSYS = 'endosysapp'

# configuracio fichero
RUTA = 'provincias.csv'


from sqlalchemy import *
import csv


# cadena de conexión a BBDD de endosys
endosys = {}
endosys['CONN'] =  'mssql://%s:%s@%s/%s' % (USER_ENDOSYS, PASS_ENDOSYS, HOST_ENDOSYS, BBDD_ENDOSYS)

contador = 0
provincias_endosys = None

def ini_endosys():
	global endosys, provincias_endosys, contador

	# iniciar sqlachemy, conexión a la bbdd y tabla de pacientes
	endosys['engine'] = create_engine(endosys['CONN'])
	endosys['metadata'] = MetaData()
	endosys['metadata'].bind = endosys['engine']
	provincias_endosys = Table('Provincias', endosys['metadata'], autoload=True)
	contador = 0
	leer_fichero_csv()

def leer_fichero_csv():
	global endosys, provincias_endosys, contador
	csvfile = open(RUTA, 'rb')
	try:
		csvreader = csv.reader(csvfile, delimiter=';', quotechar='"', quoting = csv.QUOTE_NONE, escapechar = '\\')
		contador = 0
		for row in csvreader:
			codigo = row[0]
			descripcion = row[1]
			rslt = provincias_endosys.insert().values(codigo=codigo, nombre=descripcion).execute()
			print "registro actual: %s" % (row)
			contador = contador + 1
		print "COMPLETADO. Se han resgistrado %s provincias" % (contador)
	finally:
		csvfile.close()



ini_endosys()

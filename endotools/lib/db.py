import logging

import sqlalchemy as sa
import sqlalchemy.databases.mssql as mssql
import sqlalchemy.databases.oracle as oracle
import sqlalchemy.databases.mysql as mysql

log = logging.getLogger(__name__)

def nombre_tabla(engine,tabla):
	"""
	tabla:  debe ser el nombre de la tabla sin comillas
	"""
	#   SQL Server
	if isinstance(engine.dialect, mssql.MSSQLDialect):
		pass
	#	Oracle 11g (y probablemente inferiores, 10g...)
	elif isinstance(engine.dialect, oracle.OracleDialect):
		tabla = '"%s"' % tabla
	#   MySQL
	elif isinstance(engine.dialect, mysql.MySQLDialect):
		pass
	return tabla

def existe_columna(sess, engine, table_name, column_name):
		# Comprobar si ya existe la columna

		#   SQL Server 2000, 2008 (y 2005 supongo)
		#   si el usuario de bbdd no tiene permisos es como si no existiera la columna...
		#   ( para comprobar si existe una tabla es engine.has_table() )
		if isinstance(engine.dialect, mssql.MSSQLDialect):
			r = sess.execute("SELECT COL_LENGTH('%s', '%s') AS result" % (table_name, column_name))
			existe = (iter(r).next()['result'] != None)

		#	Oracle 11g (y probablemente inferiores, 10g...)
		elif isinstance(engine.dialect, oracle.OracleDialect):
			# Algunos nombres de columnas estan en minusculas para hacerlos coincidir
			# con el estandar dicom. Por lo tanto en oracle hay que hacer dos comprobaciones
			# una con el nombre de las columnas en mayuscula y otras en minusculas, sino
			# en algunos casos detectara que la columna no existe, intentara crearla y fallara
			SQL = "SELECT COUNT(*) AS result FROM user_tab_cols WHERE column_name like '%s' AND table_name = '%s'"
			r = sess.execute(SQL % (column_name.upper(), table_name))
			existe = (iter(r).next()['result'] > 0)
			if not existe:
				r = sess.execute(SQL % (column_name, table_name))
				existe = (iter(r).next()['result'] > 0)
		#   MySQL
		elif isinstance(engine.dialect, mysql.MySQLDialect):
			schema_name = engine.dialect.get_default_schema_name( sess.connection() )
			r = sess.execute("SELECT COUNT(*) AS result FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = '%s' AND COLUMN_NAME = '%s' AND TABLE_NAME = '%s'" % (schema_name, column_name.upper(), table_name))
			existe = (iter(r).next()['result'] > 0)
		return existe

def nueva_columna(sess, engine, table_name, column_name, column_type, *args, **kwargs):
	"""
	Se intenta mantener los mismos parametros que sqlalchemy.Column(), usado
	en la definición del model.

	OJO:
		si se intenta añadir una columna con nullable=False, si ya hay registros
		siempre fallará.
	"""
	# PRUEBAS XXX
	# obtener el tipo de cada motor de base de datos automaticamente de sqlalchemy
	#print "engine.dialect:", engine.dialect
	#print "Boolean:", engine.dialect.type_descriptor(sa.types.String(50)).get_col_spec()

	#generar la definicion de columna de cada motor
	#schema_generator = engine.dialect.schemagenerator(engine.dialect, Session.connection)
	#print schemagen.get_column_specification( sa.Column("deshabilitado", sa.types.Boolean, nullable=False) )

	#Session.peta() # forzar excepcion para debugar
	# meta
	#mssql.dialect().type_descriptor(sa.types.Boolean).get_col_spec()
	#

	output_log = ''
	output_log +=	'NUEVA COLUMNA	%s.%s ( %s %s %s )\n' % \
						(table_name,
						 column_name,
						 engine.dialect.type_descriptor(column_type).get_col_spec(),
						 args,
						 kwargs
						 )
	log.debug('Nueva columna: %s, %s, %s' % (table_name, column_name, column_type))

	# Comprobar si ya existe la columna
	#   si el usuario de bbdd no tiene permisos es como si no existiera la columna...
	#   ( para comprobar si existe una tabla es engine.has_table() )
	existe = existe_columna(sess, engine, table_name, column_name)

	# Si existe se supone que es correcta y no se hace nada. Si no existe, la crea
	if not existe:
		log.debug('La columna no existe, se anadira a la tabla')
		#   Común a todos los motores de bbdd (probado con SQL Server 2008, Oracle)
		##column_type_sql = engine.dialect.type_descriptor(column_type).get_col_spec()
		#		generar la definicion de columna para el motor de bbdd
		schema_generator = engine.dialect.schemagenerator(engine.dialect, sess.connection)
		columna_sql = schema_generator.get_column_specification( sa.Column(column_name, column_type, *args, **kwargs) )

		#	   ejecutar el ALTER TABLE para añadir la columna
		if isinstance(engine.dialect, mysql.MySQLDialect):
			#   en MySQL la tabla no puede ir entre ""
			r = sess.execute('ALTER TABLE %s ADD %s' % (table_name, columna_sql))
		else:
			#   ...en SQL Server y Oracle si
			r = sess.execute('ALTER TABLE "%s" ADD %s' % (table_name, columna_sql))
		output_log +=	'		Se ha creado la columna\n'
		result = True
	else:
		output_log +=	'		La columna ya existe, no se realiza ninguna acción\n'
		log.debug('La columna ya existe. No se realizara ningun cambio')
		result = False

	return (result, output_log)
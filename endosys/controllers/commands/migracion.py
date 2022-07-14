""" 
TODO:
	- Mejorar rendimiento de tabla citas
	- Migrar tabla worklist
	- Migrar tabla citas_ex

"""

import logging, os, csv, uuid
from datetime import datetime
import shutil

from pylons.i18n import _
from pylons import config
from pylons.templating import render
import sqlalchemy as sa
from sqlalchemy import orm
from sqlalchemy.sql import and_, or_, not_
from sqlalchemy.sql.expression import bindparam
from authkit.authorize.pylons_adaptors import authorize

from endosys.lib.base import BaseController, CommandController
from endosys.model import meta
from endosys.model.meta import metadata, engine
from endosys.model import Centro
from endosys.lib.db import nueva_columna
from endosys.lib.pacientes import get_by_idunico_generic
from endosys.controllers.commands.migracion_db_classes import *
from endosys.lib.capturas import _archivo

log = logging.getLogger(__name__)

LOG_DEBUG = "DEBUG"
LOG_ERROR = "ERROR"
LOG_INFO = "INFO"
LOG_WARNING = "WARNING"

MSG_NUEVA = "%s (Nuevo registro) [Origen ID=%s]"
MSG_MIGRADA = "%s (Migrada Anteriormente) [Origen ID=%s]"
MSG_ACT_NULL = "%s: Se actualizo el data_destino_uid a NULL en todas las filas con data_destino_uid = %s"
MSG_DEL = "%s: Se eliminaron todas las filas con data_origen_uid = %s"
MSG_START = "%s: Comienzo de la migracion"
MSG_END = "%s: Fin de la migracion"
MSG_TOTAL_NEW = "%s: Nuevas (%d)"
MSG_TOTAL_NEW_ACT = "%s: Nuevas (%d) / Actualizadas (%d)"
MSG_TOTAL_NEW_ANT = "%s: Nuevas (%d) / M.Anteriormente (%d)"
MSG_TOTAL_NEW_ACT_EXI = "%s: Nuevas (%d) / Actualizadas (%d) / Existentes (%d)"
MSG_TOTAL_NEW_ANT_EXI = "%s: Nuevas (%d) / M.Anteriormente (%d) / Existentes (%d)"
MSG_TOTAL_NEW_ACT_EXC = "%s: Nuevas (%d) / Actualizadas (%d) / Excluidos (%d)"
MSG_TOTAL_NEW_ANT_EXC = "%s: Nuevas (%d) / M. Anteriormente (%d) / Excluidos (%d)"
MSG_STATUS = "%s: Filas migradas hasta el momento: %d"
MSG_DISP = "%s: Disponibles para migrar (%d)"
MSG_NOT_FOUND = "No encontro (%s) ID %d" 

USERNAME_EXCLUDES = ['sysadmin', 'admin']

def xstr(s):
    if s is None:
        return ''
    return str(s)

def raise_error_one_line(msg):
	self.write_log(msg, LOG_ERROR)
	raise Exception(msg)

class CeroFilasError(Exception):
	pass

class MultipleFilasError(Exception):
	pass

class ConflictoPacienteError(Exception):
	pass

class MigracionController(CommandController):

	db_origen = {}
	db_destino = {}
	uid_origen = ''
	uid_destino = ''
	msgs = {'error_db': 'Ocurrio un error con la BD, \
						verifique la cadena de conexion', \
			'error_versiones': 'Ocurrio un error en la comprobacion de versiones'}
	des_session = None
	ori_session = None
	logger = None
	prefijo_exploracion = 0
	prefijo_informe = 0

	def_valores_texto_d = None
	def_valores_texto_o = None
	def_valores_selec_o = None
	def_valores_selec_o = None
	def_valores_multi_o = None
	def_valores_multi_o = None
	def_valores_bool_o = None
	def_valores_bool_o = None
	def_rel_form_expl_d = None
	def_rel_form_expl_o = None
	def_capturas_d = None
	def_capturas_o = None
	def_informes_d = None
	def_informes_o = None
	def_rel_capturas_informes_o = None
	def_rel_capturas_informes_d = None
	def_exploraciones_dicom_o = None
	def_exploraciones_dicom_d = None

	# hash tables de id's para mejorar rendimiento.
	exploraciones_hash = []
	capturas_hash = []
	informes_hash = []
	formularios_hash = []
	campos_hash = []
	elementos_hash = []
	tipos_exploraciones_hash = []
	motivos_hash = []
	centros_hash = []
	servicios_hash = []
	aseguradora_hash = []
	medicos_hash = []
	exploraciones_dicom_hash = []
	salas_hash = []
	prioridades_hash = []
	agendas_hash = []
	
	# en este diccionario se guardan los pacientes que se crearon
	# para aumentar rendimiento y evitar hacer consultas a la bd
	pacientes_dict = []

	# array de dict de exploraciones con mes y anio
	expl_mes_anio_dict = []

	def get(self, request):
		params = {}
		params['step'] = 1
		params["database_destino"] = config.get('sqlalchemy.url')
		return render('/migracion.html',extra_vars=params)

	def post(self, request):
		template = '/migracion.html'
		params = {}
		params['output'] = []

		self._set_log()

		# conectar y verificar db origen
		db_ok = True
		if 'database_origen' in request.params:
			try:
				self.conectar_db('origen',request.params.get('database_origen'))
				params['database_origen'] = request.params.get('database_origen')
				
			except sa.exceptions.DBAPIError:	
				# ya tiene asignado db_ok False por defecto
				db_ok = False

		if 'database_destino' in request.params:
			try:
				self.conectar_db('destino',request.params.get('database_destino'))
				params['database_destino'] = request.params.get('database_destino')
			except sa.exceptions.DBAPIError:	
				# ya tiene asignado db_ok False por defecto
				db_ok = False

		self.ori_session = self.crear_session('origen')	
		self.des_session = self.crear_session('destino')

		# Si hay algun problema con la bd origen no continua
		if not db_ok:
			params['error'] = self.msgs['error_db']
			params['step'] = 1
			return render(template,extra_vars=params)

		#verificar las versiones del endosys que sean iguales
		versiones_ok = self.verificar_versiones_endotools()
		if not versiones_ok:
			params['error'] = self.msgs['error_versiones']
			params['step'] = 1
			return render(template,extra_vars=params)

		if 'step' in request.params:
			step = int(request.params.get('step'))

			#procesar migracion
			if step == 2:
				# crear las tablas auxiliares para la migracion
				self.crear_tablas_migracion()
				self.crear_obtener_datos_migracion()
				self.crear_columnas_migracion()
				self.orm_mapear_tablas()
			elif step == 3:
				# mapear centros 
				self.crear_obtener_datos_migracion()
				self.crear_mapear_centros(request)
			elif step == 4:
				# mapear servicios
				self.crear_obtener_datos_migracion()
				self.crear_mapear_servicios(request)
			elif step == 5:
				# migrar datos aux
				self.crear_obtener_datos_migracion()
				output = self.migrar_datos_auxiliares()
				params['output'] = output
			elif step == 6:
				#migrar exploraciones
				self.crear_obtener_datos_migracion()
				self.exploraciones_hash = self.get_hash_table(ExploracionD)
				self.tipos_exploraciones_hash = self.get_hash_table(TipoExploracionD)
				self.motivos_hash = self.get_hash_table(MotivoCancelacionD)
				self.centros_hash = self.get_hash_table(CentroD)
				self.servicios_hash = self.get_hash_table(ServicioD)
				self.aseguradora_hash = self.get_hash_table(AseguradoraD)
				self.medicos_hash = self.get_hash_table(MedicoD)
				self.formularios_hash = self.get_hash_table(FormularioD)
				output = self.migrar_exploraciones(request)
				params['output'] = output
			elif step == 7:
				#migrar exploraciones dicom
				self.crear_obtener_datos_migracion()
				self.exploraciones_hash = self.get_hash_table(ExploracionD)
				self.exploraciones_dicom_hash = self.get_hash_table(Exploracion_dicomD)
				output = self.migrar_exploraciones_dicom()
				params['output'] = output
			elif step == 8:
				#migrar rel_form_expl
				self.crear_obtener_datos_migracion()
				self.exploraciones_hash = self.get_hash_table(ExploracionD)
				self.formularios_hash = self.get_hash_table(FormularioD)
				output = self.migrar_rel_formularios_exploraciones()
				params['output'] = output
			elif step == 9:
				#migrar valores texto
				self.crear_obtener_datos_migracion()
				self.exploraciones_hash = self.get_hash_table(ExploracionD)
				self.formularios_hash = self.get_hash_table(FormularioD)
				self.campos_hash = self.get_hash_table(CampoD)
				output = self.migrar_valores_texto()
				params['output'] = output
			elif step == 10:
				# migrar valores selec
				self.crear_obtener_datos_migracion()
				self.exploraciones_hash = self.get_hash_table(ExploracionD)
				self.formularios_hash = self.get_hash_table(FormularioD)
				self.campos_hash = self.get_hash_table(CampoD)
				self.elementos_hash = self.get_hash_table(ElementoD)
				output = self.migrar_valores_selec()
				params['output'] = output
			elif step == 11:
				# migrar valores multi
				self.crear_obtener_datos_migracion()
				self.exploraciones_hash = self.get_hash_table(ExploracionD)
				self.formularios_hash = self.get_hash_table(FormularioD)
				self.campos_hash = self.get_hash_table(CampoD)
				self.elementos_hash = self.get_hash_table(ElementoD)
				output = self.migrar_valores_multi()
				params['output'] = output
			elif step == 12:
				# migrar valores bool
				self.crear_obtener_datos_migracion()
				self.exploraciones_hash = self.get_hash_table(ExploracionD)
				self.formularios_hash = self.get_hash_table(FormularioD)
				self.campos_hash = self.get_hash_table(CampoD)
				output = self.migrar_valores_bool()
				params['output'] = output
			elif step == 13:
				#migrar capturas
				self.crear_obtener_datos_migracion()
				self.exploraciones_hash = self.get_hash_table(ExploracionD)
				self.capturas_hash = self.get_hash_table(CapturaD)
				output = self.migrar_capturas_bd()
				params['output'] = output
			elif step == 14:
				#migrar informes 
				self.crear_obtener_datos_migracion()
				self.exploraciones_hash = self.get_hash_table(ExploracionD)
				self.informes_hash = self.get_hash_table(InformeD)
				output = self.migrar_informes_bd(request)
				params['output'] = output
			elif step == 15:
				# migrar rel capturas informes
				self.crear_obtener_datos_migracion()
				self.capturas_hash = self.get_hash_table(CapturaD)
				self.informes_hash = self.get_hash_table(InformeD)
				output = self.migrar_rel_capturas_informes()
				params['output'] = output
			elif step == 16:
				#migrar citas
				self.crear_obtener_datos_migracion()
				self.tipos_exploraciones_hash = self.get_hash_table(TipoExploracionD)
				self.salas_hash = self.get_hash_table(SalaD)
				self.exploraciones_hash = self.get_hash_table(ExploracionD)
				self.motivos_hash = self.get_hash_table(MotivoCancelacionD)
				self.prioridades_hash = self.get_hash_table(PrioridadD)
				self.agendas_hash = self.get_hash_table(AgendaD)
				self.aseguradora_hash = self.get_hash_table(AseguradoraD)
				output = self.migrar_citas()
				params['output'] = output
			elif step == 17:
				# archivos de capturas
				self.crear_obtener_datos_migracion()
				self.expl_mes_anio_dict = self.get_expl_mes_anio()
				output = self.copiar_mover_capturas(request)
				params['output'] = output
			elif step == 18:
				# archivos de informes
				self.crear_obtener_datos_migracion()
				self.expl_mes_anio_dict = self.get_expl_mes_anio()
				output = self.copiar_mover_informes(request)
				params['output'] = output

			#preparar para el siguienet paso
			siguiente_paso = step + 1
			stepnext = request.params.get('stepnext')
			if stepnext != '':
				siguiente_paso = int(stepnext)
			params['step'] = siguiente_paso

			if siguiente_paso == 1:
				return render(template,extra_vars=params)
			elif siguiente_paso == 2:		
				return render(template,extra_vars=params)
			elif siguiente_paso == 3:
				data_centros = self.preparar_datos_centros()
				params['centros'] = data_centros
				return render(template,extra_vars=params)
			elif siguiente_paso == 4:
				data_centros = self.preparar_datos_centros()
				params['centros'] = data_centros
				data_servicios = self.preparar_datos_servicios()
				params['servicios'] = data_servicios
				return render(template,extra_vars=params)
			elif siguiente_paso == 5:
				return render(template,extra_vars=params)
			elif siguiente_paso == 6:
				params['rangos'] = self.preparar_datos_migrar_datos()
				return render(template,extra_vars=params)
			elif siguiente_paso == 7:
				return render(template,extra_vars=params)
			elif siguiente_paso == 8:	
				return render(template,extra_vars=params)
			elif siguiente_paso == 9:
				return render(template,extra_vars=params)
			elif siguiente_paso == 10:
				return render(template,extra_vars=params)
			elif siguiente_paso == 11:
				return render(template,extra_vars=params)
			elif siguiente_paso == 12:
				return render(template,extra_vars=params)
			elif siguiente_paso == 13:
				# capturas
				return render(template,extra_vars=params)
			elif siguiente_paso == 14:
				params['rangos'] = self.preparar_datos_migrar_datos()
				return render(template,extra_vars=params)
			elif siguiente_paso == 15:
				return render(template,extra_vars=params)
			elif siguiente_paso == 16:
				return render(template,extra_vars=params)
			elif siguiente_paso == 17:
				return render(template,extra_vars=params)
			elif siguiente_paso == 18:
				return render(template,extra_vars=params)
			elif siguiente_paso == 19:
				return render(template,extra_vars=params)
			
	def del_hash_tables(self):
		# liberar memoria
		self.exploraciones_hash = []
		self.capturas_hash = []
		self.informes_hash = []
		self.formularios_hash = []
		self.campos_hash = []
		self.elementos_hash = []
		self.tipos_exploraciones_hash = []
		self.motivos_hash = []
		self.centros_hash = []
		self.servicios_hash = []
		self.aseguradora_hash = []
		self.medicos_hash = []
		self.exploraciones_dicom_hash = []
		self.salas_hash = []
		self.prioridades_hash = []
		self.agendas_hash = []

	def run_command(self):
		"""
		los comandos se implementan adentro del post()
		para facilitar el desarrollo y la claridad del codigo
		"""
		pass

	def post_message(self):
		a_volver = u'<a href="/admin"> << Volver </a> <br>'
		return a_volver + u'<p>Comando Ejecutado. Ingrese a "Tareas" del EndoTools para ver el estado de la misma.</p>'
	
	def _set_log(self):
		#import pdb; pdb.set_trace()
		filename = 'logs/migracion.log'
		log_level = logging.INFO	
		self.log_handler = logging.handlers.RotatingFileHandler(filename, maxBytes=5485760,backupCount=2000)
		formatter = logging.Formatter('[%(levelname)s][%(asctime)s] %(message)s')
		self.log_handler.setFormatter(formatter)
		self.logger = logging.getLogger(__name__)
		self.logger.setLevel(log_level)
		self.logger.addHandler(self.log_handler)
		self.write_log("-------------------------------", LOG_INFO)

	def write_log(self, msg, lvl):
		try:
			#import pdb; pdb.set_trace()
			msg = "["+lvl+"] "+str(msg)
			if lvl.upper() == LOG_INFO:
				self.logger.info(msg)
				print msg
			if lvl.upper() == LOG_DEBUG:
				self.logger.debug(msg)
				print msg
			if lvl.upper() == LOG_ERROR:
				self.logger.error(msg)
				print msg
			if lvl.upper() == LOG_WARNING:
				self.logger.warning(msg)
				print msg
		except Exception, e:
			print msg
			self.logger.error("Error al escribir el LOG: " + str(e))

	def crear_session(self, tipo):
		""" Crear la session para la base de datos 
			origen que no esta conectada con endosys
		"""
		if tipo == 'origen':
			bind = self.db_origen['engine']
		elif tipo == 'destino':
			bind = self.db_destino['engine']
		else:
			raise Exception('Seleccione el tipo de Session')

		sm = orm.sessionmaker(autoflush=True, transactional=True,
							  bind=bind) 
		session = orm.scoped_session(sm)
		return session

	def conectar_db(self, tipo, database):
		""" Conectar con la bd origen que no esta asociada
			al endosys
		"""
		if tipo=='origen':
			self.db_origen['CONN'] = database
			self.db_origen['engine'] = sa.create_engine(self.db_origen['CONN'])
			self.db_origen['engine'].connect()
			self.db_origen['metadata'] = sa.MetaData()
			self.db_origen['metadata'].bind = self.db_origen['engine']
		elif tipo=='destino':
			self.db_destino['CONN'] = database
			self.db_destino['engine'] = sa.create_engine(self.db_destino['CONN'])
			self.db_destino['engine'].connect()
			self.db_destino['metadata'] = sa.MetaData()
			self.db_destino['metadata'].bind = self.db_destino['engine']
		else:
			raise Exception('Seleccione el tipo de BD')

	def verificar_versiones_endotools(self):

		try:
			def_configuraciones_o = sa.Table('Configuraciones', self.db_origen['metadata'], autoload=True)
			def_configuraciones_d = sa.Table('Configuraciones', self.db_destino['metadata'], autoload=True)
			orm.mapper(ConfiguracionO, def_configuraciones_o)
			orm.mapper(ConfiguracionD, def_configuraciones_d)
		except sa.exceptions.ArgumentError:
			# Este error es cuando ya estan mapeadas, no hace
			# falta hacer nada
			pass
		except Exception, e:
			self.write_log("Ocurrio un problema al obtener las tablas de configuracion", LOG_ERROR)
			return False

		try:
			ori_version = self.ori_session.query(ConfiguracionO).filter(ConfiguracionO.clave=='version').first()
			des_version = self.des_session.query(ConfiguracionD).filter(ConfiguracionD.clave=='version').first()
			if ori_version.valor == des_version.valor:
				return True
			else:
				self.write_log("Las versiones de endosys son distintas", LOG_ERROR)
				return False
		except Exception,e:
			self.write_log("Ocurrio un error al obtener las versions del endosys (%s)" % (str(e)), LOG_ERROR)
			return False

	def crear_tablas_migracion(self):
		""" Crea las tablas necesarias en origen y destino
		 	para guardar los datos de las migraciones
		 	Usado en paso 2
		"""
		migracion_tabla_destino = sa.Table('migracion',self.db_destino['metadata'],
			sa.Column("id", sa.types.Integer, 
							sa.schema.Sequence('secuencia_migracion'), 
							primary_key=True),
			sa.Column("fechahora", sa.types.DateTime, nullable=True),
			sa.Column("origen", sa.types.String(500), nullable=True),
			sa.Column("destino", sa.types.String(500), nullable=True),
			sa.Column("uid_origen", sa.types.String(128), nullable=True),
			sa.Column("uid_destino", sa.types.String(128), nullable=True),
			useexisting=True
		)
		migracion_tabla_destino.create(self.db_destino['engine'], checkfirst=True)
	
		migracion_tabla_origen = sa.Table('migracion', 
			self.db_origen['metadata'],
			sa.Column("id", sa.types.Integer, 
							sa.schema.Sequence('secuencia_migracion'), 
							primary_key=True),
			sa.Column("fechahora", sa.types.DateTime, nullable=True),
			sa.Column("origen", sa.types.String(500), nullable=True),
			sa.Column("destino", sa.types.String(500), nullable=True),
			sa.Column("uid_origen", sa.types.String(128), nullable=True),
			sa.Column("uid_destino", sa.types.String(128), nullable=True),
			useexisting=True
		)
		migracion_tabla_origen.create(self.db_origen['engine'],
									  checkfirst=True)

		# crear u obtener los uid de las migraciones.
		try:
			orm.mapper(MigracionO, migracion_tabla_origen)
			orm.mapper(MigracionD, migracion_tabla_destino)
		except sa.exceptions.ArgumentError:
			# Este error es cuando ya estan mapeadas, no hace
			# falta hacer nada
			pass
	
	def crear_obtener_datos_migracion(self):
		
		migracion_origen = self.ori_session.query(MigracionO)
		migracion_origen = migracion_origen.filter( and_( \
								MigracionO.origen==self.db_origen['CONN'],
								MigracionO.destino==self.db_destino['CONN']))
		if migracion_origen.count() > 0:
			#se encontro una migracion existente en origen
			migracion_origen = migracion_origen.one()
			self.uid_origen = migracion_origen.uid_origen
			self.uid_destino = migracion_origen.uid_destino
		
		migracion_destino = self.des_session.query(MigracionD)
		migracion_destino = migracion_destino.filter( and_( \
								MigracionD.origen==self.db_origen['CONN'],
								MigracionD.destino==self.db_destino['CONN']))
		if migracion_destino.count() > 0:
			#se encontro una migracion existente en destino
			migracion_destino = migracion_destino.one()
			if (self.uid_origen is not None and \
				self.uid_origen != migracion_destino.uid_origen) or \
				(self.uid_destino is not None and \
				self.uid_destino != migracion_destino.uid_destino):
				raise Exception("Existe conflicto de uid entre origen y destino. \
								Es necesario borrar la fila de la tabla migracion \
								en destino.")

		if self.uid_origen is '':
			# No se hizo nunca la migracion esta, se crean los uid
			self.uid_origen = uuid.uuid4().hex
			self.uid_destino = uuid.uuid4().hex
			#grabarlos en las bd.
			migracion_ori_reg = MigracionO()
			migracion_ori_reg.uid_origen = self.uid_origen
			migracion_ori_reg.origen = self.db_origen['CONN']
			migracion_ori_reg.uid_destino = self.uid_destino
			migracion_ori_reg.destino = self.db_destino['CONN']
			migracion_ori_reg.fechahora = datetime.now()
			self.ori_session.save(migracion_ori_reg)

			migracion_des_reg = MigracionD()
			migracion_des_reg.uid_origen = self.uid_origen
			migracion_des_reg.origen = self.db_origen['CONN']
			migracion_des_reg.uid_destino = self.uid_destino
			migracion_des_reg.destino = self.db_destino['CONN']
			migracion_des_reg.fechahora = datetime.now()
			self.des_session.save(migracion_des_reg)

			self.ori_session.commit()
			self.des_session.commit()

		# Log
		self.write_log("DB Origen: " + self.db_origen["CONN"] ,LOG_INFO)
		self.write_log("UID Origen: " + self.uid_origen ,LOG_INFO)
		self.write_log("DB Destino: " + self.db_destino["CONN"] ,LOG_INFO)
		self.write_log("UID Destino: " + self.uid_destino ,LOG_INFO)

		self.ori_session.close()
		self.des_session.close()
	
	def crear_columnas_migracion(self):
		""" Crea las columnas de identificacion de migracion en 
			las diferentes tablas de endosys que estan 
			involucradas en la migracion
			Usado en Paso 2
		"""
		# Crear Columans en destino
		self.des_session = self.crear_session('destino')
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'Centros', 'data_origen_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'Centros', 'data_origen_reg_id', sa.types.Integer, nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'Servicios', 'data_origen_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'Servicios', 'data_origen_reg_id', sa.types.Integer, nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'Salas', 'data_origen_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'Salas', 'data_origen_reg_id', sa.types.Integer, nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'rel_Salas_Servicios', 'data_origen_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'rel_Salas_Servicios', 'data_origen_reg_id', sa.types.Integer, nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'Agendas', 'data_origen_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'Agendas', 'data_origen_reg_id', sa.types.Integer, nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'rel_Salas_Agendas', 'data_origen_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'rel_Salas_Agendas', 'data_origen_reg_id', sa.types.Integer, nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'HorariosAgendas', 'data_origen_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'HorariosAgendas', 'data_origen_reg_id', sa.types.Integer, nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'Workstations', 'data_origen_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'Workstations', 'data_origen_reg_id', sa.types.Integer, nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'rel_Servicios_Workstations', 'data_origen_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'rel_Servicios_Workstations', 'data_origen_reg_id', sa.types.Integer, nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'users', 'data_origen_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'users', 'data_origen_reg_id', sa.types.Integer, nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'users_roles', 'data_origen_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'users_roles', 'data_origen_reg_id', sa.types.Integer, nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'Usuarios', 'data_origen_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'Usuarios', 'data_origen_reg_id', sa.types.Integer, nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'Medicos', 'data_origen_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'Medicos', 'data_origen_reg_id', sa.types.Integer, nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'rel_Medicos_Servicios', 'data_origen_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'rel_Medicos_Servicios', 'data_origen_reg_id', sa.types.Integer, nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'rel_Medicos_Agendas', 'data_origen_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'rel_Medicos_Agendas', 'data_origen_reg_id', sa.types.Integer, nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'Aseguradoras', 'data_origen_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'Aseguradoras', 'data_origen_reg_id', sa.types.Integer, nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'Prioridades', 'data_origen_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'Prioridades', 'data_origen_reg_id', sa.types.Integer, nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'MotivosCancelacion', 'data_origen_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'MotivosCancelacion', 'data_origen_reg_id', sa.types.Integer, nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'Campos', 'data_origen_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'Campos', 'data_origen_reg_id', sa.types.Integer, nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'TextosPredefinidos', 'data_origen_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'TextosPredefinidos', 'data_origen_reg_id', sa.types.Integer, nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'GruposCampos', 'data_origen_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'GruposCampos', 'data_origen_reg_id', sa.types.Integer, nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'Elementos', 'data_origen_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'Elementos', 'data_origen_reg_id', sa.types.Integer, nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'Formularios', 'data_origen_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'Formularios', 'data_origen_reg_id', sa.types.Integer, nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'rel_Campos_Formularios', 'data_origen_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'rel_Campos_Formularios', 'data_origen_reg_id', sa.types.Integer, nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'rel_GruposCampos_Formularios', 'data_origen_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'rel_GruposCampos_Formularios', 'data_origen_reg_id', sa.types.Integer, nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'ValoresPorDefecto', 'data_origen_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'ValoresPorDefecto', 'data_origen_reg_id', sa.types.Integer, nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'TiposExploracion', 'data_origen_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'TiposExploracion', 'data_origen_reg_id', sa.types.Integer, nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'rel_Forms_TiposExpl', 'data_origen_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'rel_Forms_TiposExpl', 'data_origen_reg_id', sa.types.Integer, nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'rel_Serv_TiposExpl', 'data_origen_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'rel_Serv_TiposExpl', 'data_origen_reg_id', sa.types.Integer, nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'Poblaciones', 'data_origen_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'Poblaciones', 'data_origen_reg_id', sa.types.Integer, nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'Provincias', 'data_origen_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'Provincias', 'data_origen_reg_id', sa.types.Integer, nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'Pacientes', 'data_origen_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'Pacientes', 'data_origen_reg_id', sa.types.Integer, nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'rel_Pacientes_Centros', 'data_origen_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'rel_Pacientes_Centros', 'data_origen_reg_id', sa.types.Integer, nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'Exploraciones', 'data_origen_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'Exploraciones', 'data_origen_reg_id', sa.types.Integer, nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'Exploraciones_dicom', 'data_origen_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'Exploraciones_dicom', 'data_origen_reg_id', sa.types.Integer, nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'rel_Formularios_Exploraciones', 'data_origen_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'rel_Formularios_Exploraciones', 'data_origen_reg_id', sa.types.Integer, nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'ValoresTexto', 'data_origen_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'ValoresTexto', 'data_origen_reg_id', sa.types.Integer, nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'ValoresSelec', 'data_origen_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'ValoresSelec', 'data_origen_reg_id', sa.types.Integer, nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'ValoresMulti', 'data_origen_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'ValoresMulti', 'data_origen_reg_id', sa.types.Integer, nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'ValoresBool', 'data_origen_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'ValoresBool', 'data_origen_reg_id', sa.types.Integer, nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'Capturas', 'data_origen_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'Capturas', 'data_origen_reg_id', sa.types.Integer, nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'Informes', 'data_origen_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'Informes', 'data_origen_reg_id', sa.types.Integer, nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'rel_Capturas_Informes', 'data_origen_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'rel_Capturas_Informes', 'data_origen_reg_id', sa.types.Integer, nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'Citas', 'data_origen_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.des_session, self.db_destino['engine'], 'Citas', 'data_origen_reg_id', sa.types.Integer, nullable=True)
		self.write_log(out,LOG_INFO)

		self.des_session.commit()
		self.des_session.close()

		# Crear columnas en origen
		self.ori_session = self.crear_session('origen')
		r, out = nueva_columna(self.ori_session, self.db_origen['engine'],'Centros', 'data_destino_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.ori_session, self.db_origen['engine'],'Servicios', 'data_destino_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.ori_session, self.db_origen['engine'],'Salas', 'data_destino_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.ori_session, self.db_origen['engine'],'rel_Salas_Servicios', 'data_destino_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.ori_session, self.db_origen['engine'],'Agendas', 'data_destino_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.ori_session, self.db_origen['engine'],'rel_Salas_Agendas', 'data_destino_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.ori_session, self.db_origen['engine'],'HorariosAgendas', 'data_destino_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.ori_session, self.db_origen['engine'],'Workstations', 'data_destino_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.ori_session, self.db_origen['engine'],'rel_Servicios_Workstations', 'data_destino_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.ori_session, self.db_origen['engine'],'users', 'data_destino_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.ori_session, self.db_origen['engine'],'users_roles', 'data_destino_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.ori_session, self.db_origen['engine'],'Usuarios', 'data_destino_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.ori_session, self.db_origen['engine'],'Medicos', 'data_destino_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.ori_session, self.db_origen['engine'],'rel_Medicos_Servicios', 'data_destino_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.ori_session, self.db_origen['engine'],'rel_Medicos_Agendas', 'data_destino_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.ori_session, self.db_origen['engine'],'Aseguradoras', 'data_destino_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.ori_session, self.db_origen['engine'],'Prioridades', 'data_destino_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.ori_session, self.db_origen['engine'],'MotivosCancelacion', 'data_destino_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.ori_session, self.db_origen['engine'],'Campos', 'data_destino_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.ori_session, self.db_origen['engine'],'TextosPredefinidos', 'data_destino_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.ori_session, self.db_origen['engine'],'GruposCampos', 'data_destino_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.ori_session, self.db_origen['engine'],'Elementos', 'data_destino_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.ori_session, self.db_origen['engine'],'Formularios', 'data_destino_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.ori_session, self.db_origen['engine'],'rel_Campos_Formularios', 'data_destino_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.ori_session, self.db_origen['engine'],'rel_GruposCampos_Formularios', 'data_destino_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.ori_session, self.db_origen['engine'],'ValoresPorDefecto', 'data_destino_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.ori_session, self.db_origen['engine'],'TiposExploracion', 'data_destino_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.ori_session, self.db_origen['engine'],'rel_Forms_TiposExpl', 'data_destino_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.ori_session, self.db_origen['engine'],'rel_Serv_TiposExpl', 'data_destino_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.ori_session, self.db_origen['engine'],'Poblaciones', 'data_destino_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.ori_session, self.db_origen['engine'],'Provincias', 'data_destino_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.ori_session, self.db_origen['engine'],'Pacientes', 'data_destino_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.ori_session, self.db_origen['engine'],'rel_Pacientes_Centros', 'data_destino_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.ori_session, self.db_origen['engine'],'Exploraciones', 'data_destino_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.ori_session, self.db_origen['engine'],'Exploraciones_dicom', 'data_destino_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.ori_session, self.db_origen['engine'],'rel_Formularios_Exploraciones', 'data_destino_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.ori_session, self.db_origen['engine'],'ValoresTexto', 'data_destino_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.ori_session, self.db_origen['engine'],'ValoresSelec', 'data_destino_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.ori_session, self.db_origen['engine'],'ValoresMulti', 'data_destino_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.ori_session, self.db_origen['engine'],'ValoresBool', 'data_destino_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.ori_session, self.db_origen['engine'],'Capturas', 'data_destino_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.ori_session, self.db_origen['engine'],'Informes', 'data_destino_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.ori_session, self.db_origen['engine'],'rel_Capturas_Informes', 'data_destino_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)
		r, out = nueva_columna(self.ori_session, self.db_origen['engine'],'Citas', 'data_destino_uid', sa.types.String(128), nullable=True)
		self.write_log(out,LOG_INFO)

		self.ori_session.commit()
		self.ori_session.close()

	def preparar_datos_centros(self):
		""" Busca la informacion de los centros en las BD
			y los transforma para mostrarlos en la UI
		"""

		self.ori_session = self.crear_session('origen')
		self.des_session = self.crear_session('destino')	



		ori_centros_result = self.ori_session.query(CentroO).all()
		data_origen = []
		for c in ori_centros_result:
			mapeado = 0
			if c.data_destino_uid == self.uid_destino:
				mapeado = 1
			data_origen.append({
				'id': c.id,
				'nombre': c.nombre.decode('utf-8', errors="ignore"),
				'mapeado': mapeado
			})

		des_centros_result = self.des_session.query(CentroD).all()
		data_destino = []
		for c in des_centros_result:

			data_destino.append({
				'id': c.id,
				'nombre': c.nombre.decode('utf-8', errors="ignore")
			})

		centros = {'origen': data_origen,
				   'destino': data_destino}
		
		self.ori_session.close()
		self.des_session.close()

		return centros

	def crear_mapear_centros(self, request):
		""" Crea o mapea centros de la bd origen
			a la bd destino
		"""
		error = False
		self.ori_session = self.crear_session('origen')	
		self.des_session = self.crear_session('destino')

		ori_centros_result = self.ori_session.query(CentroO).all()
		for ori_centro in ori_centros_result:

			if ori_centro.data_destino_uid != self.uid_destino:
				# si es igual no entra pq quiere decir que ya esta mapeado.

				# Recorre los centros de origen y crea o mapea
				# segun la seleccion del select en la UI
				param_name = 'centro' + str(ori_centro.id)
				value = int(request.params.get(param_name, 0))
				if value == 0:
					centro = CentroD()
					centro.nombre = ori_centro.nombre
					centro.codigo = ori_centro.codigo
					centro.data_origen_uid = self.uid_origen
					centro.data_origen_reg_id = ori_centro.id
					self.des_session.save(centro)
				else:
					centro_des = self.des_session.query(CentroD).filter(CentroD.id == value).one()
					centro_des.data_origen_uid = self.uid_origen
					centro_des.data_origen_reg_id = ori_centro.id
					self.des_session.update(centro_des)

				#grabar data_destino_uid en origen
				ori_centro.data_destino_uid = self.uid_destino
				self.ori_session.update(ori_centro)

		if not error:
			self.des_session.commit()
			self.ori_session.commit()

		self.ori_session.close()
		self.des_session.close()

	def preparar_datos_servicios(self):
		""" Busca la informacion de los centros en las BD
			y los transforma para mostrarlos en la UI
		"""

		centros = self.preparar_datos_centros()

		self.ori_session = self.crear_session('origen')
		self.des_session = self.crear_session('destino')	

		ori_servicios_result = self.ori_session.query(ServicioO).all()
		data_origen = []
		for c in ori_servicios_result:
			mapeado = 0
			if c.data_destino_uid == self.uid_destino:
				mapeado = 1
			data_origen.append({
				'id': c.id,
				'nombre': c.nombre.decode('utf-8', errors="ignore"),
				'centro': filter(lambda cen: cen['id'] == c.centro_id, centros['origen'])[0],
				'mapeado': mapeado
			})

		des_servicios_result = self.des_session.query(ServicioD).all()
		data_destino = []
		for c in des_servicios_result:
			data_destino.append({
				'id': c.id,
				'nombre': c.nombre.decode('utf-8', errors="ignore"),
				'centro': filter(lambda cen: cen['id'] == c.centro_id, centros['destino'])[0]
			})

		servicios = {'origen': data_origen,
				   'destino': data_destino}
		
		self.ori_session.close()
		self.des_session.close()

		return servicios

	def crear_mapear_servicios(self,request):
		""" Crea o mapea servicios de origen a destino
		"""
		error = False
		self.ori_session = self.crear_session('origen')	
		self.des_session = self.crear_session('destino')

		ori_servicios_result = self.ori_session.query(ServicioO).all()
		for ori_servicio in ori_servicios_result:
			if ori_servicio.data_destino_uid != self.uid_destino:
				# solo deja mapear si no esta mapeado anteriormente.
				# obtiene la infor del formulario
				param_name = 'servicio' + str(ori_servicio.id)
				value = int(request.params.get(param_name, 0))
				param_name_centro = param_name + 'centro'
				value_centro = int(request.params.get(param_name_centro, 0))

				if value == 0:
					servicio = ServicioD()
					servicio.nombre = ori_servicio.nombre
					servicio.codigo = ori_servicio.codigo
					servicio.data_origen_uid = self.uid_origen
					servicio.data_origen_reg_id = ori_servicio.id
					# solo graba el centro cuando se crea uno nuevo
					servicio.centro_id = value_centro
					self.des_session.save(servicio)
				else:
					servicio_des = self.des_session.query(ServicioD).filter(ServicioD.id == value).one()
					servicio_des.data_origen_uid = self.uid_origen
					servicio_des.data_origen_reg_id = ori_servicio.id
					self.des_session.update(servicio_des)

				ori_servicio.data_destino_uid = self.uid_destino
				self.ori_session.update(ori_servicio)

		if not error:
			self.des_session.commit()
			self.ori_session.commit()

		self.ori_session.close()
		self.des_session.close()

	def orm_mapear_tablas(self):
		try:
			def_centro_d = sa.Table('Centros', self.db_destino['metadata'], autoload=True)
			def_centro_o = sa.Table('Centros', self.db_origen['metadata'], autoload=True)
			orm.mapper(CentroO, def_centro_o)
			orm.mapper(CentroD, def_centro_d)
			def_servicio_d = sa.Table('Servicios', self.db_destino['metadata'], autoload=True)
			def_servicio_o = sa.Table('Servicios', self.db_origen['metadata'], autoload=True)
			orm.mapper(ServicioO, def_servicio_o)
			orm.mapper(ServicioD, def_servicio_d)
			def_salas_o = sa.Table('Salas', self.db_origen['metadata'], autoload=True)
			def_salas_d = sa.Table('Salas', self.db_destino['metadata'], autoload=True)
			orm.mapper(SalaO, def_salas_o)
			orm.mapper(SalaD, def_salas_d)
			def_rel_salas_servicios_o = sa.Table('rel_Salas_Servicios', self.db_origen['metadata'], autoload=True)
			def_rel_salas_servicios_d = sa.Table('rel_Salas_Servicios', self.db_destino['metadata'], autoload=True)
			orm.mapper(Rel_Salas_ServiciosO, def_rel_salas_servicios_o)
			orm.mapper(Rel_Salas_ServiciosD, def_rel_salas_servicios_d)
			def_agendas_o = sa.Table('Agendas', self.db_origen['metadata'], autoload=True)
			def_agendas_d = sa.Table('Agendas', self.db_destino['metadata'], autoload=True)
			orm.mapper(AgendaO, def_agendas_o)
			orm.mapper(AgendaD, def_agendas_d)
			def_rel_salas_agendas_o = sa.Table('rel_Salas_Agendas', self.db_origen['metadata'], autoload=True)
			def_rel_salas_agendas_d = sa.Table('rel_Salas_Agendas', self.db_destino['metadata'], autoload=True)
			orm.mapper(Rel_Salas_AgendasO, def_rel_salas_agendas_o)
			orm.mapper(Rel_Salas_AgendasD, def_rel_salas_agendas_d)
			def_horarios_agendas_o = sa.Table('HorariosAgendas', self.db_origen['metadata'], autoload=True)
			def_horarios_agendas_d = sa.Table('HorariosAgendas', self.db_destino['metadata'], autoload=True)
			orm.mapper(HorarioAgendaO, def_horarios_agendas_o)
			orm.mapper(HorarioAgendaD, def_horarios_agendas_d)
			def_workstations_o = sa.Table('Workstations', self.db_origen['metadata'], autoload=True)
			def_workstations_d = sa.Table('Workstations', self.db_destino['metadata'], autoload=True)
			orm.mapper(WorkstationO, def_workstations_o)
			orm.mapper(WorkstationD, def_workstations_d)
			def_rel_servicios_workstations_o = sa.Table('rel_Servicios_Workstations', self.db_origen['metadata'], autoload=True)
			def_rel_servicios_workstations_d = sa.Table('rel_Servicios_Workstations', self.db_destino['metadata'], autoload=True)
			orm.mapper(Rel_Servicios_WorkstationsO, def_rel_servicios_workstations_o)
			orm.mapper(Rel_Servicios_WorkstationsD, def_rel_servicios_workstations_d)
			def_users_o = sa.Table('users', self.db_origen['metadata'], autoload=True)
			def_users_d = sa.Table('users', self.db_destino['metadata'], autoload=True)
			orm.mapper(UserO, def_users_o)
			orm.mapper(UserD, def_users_d)
			def_roles_o = sa.Table('roles', self.db_origen['metadata'], autoload=True)
			def_roles_d = sa.Table('roles', self.db_destino['metadata'], autoload=True)
			orm.mapper(RoleO, def_roles_o)
			orm.mapper(RoleD, def_roles_d)
			def_users_roles_o = sa.Table('users_roles', self.db_origen['metadata'], \
								sa.Column('user_id', sa.types.Integer, primary_key=True, autoincrement=False), \
								sa.Column('role_id', sa.types.Integer, primary_key=True, autoincrement=False), \
								sa.Column('data_destino_uid', sa.types.String(128), nullable=True))
			def_users_roles_d = sa.Table('users_roles', self.db_destino['metadata'], \
								sa.Column('user_id', sa.types.Integer, primary_key=True, autoincrement=False), \
								sa.Column('role_id', sa.types.Integer, primary_key=True, autoincrement=False), \
								sa.Column('data_origen_uid', sa.types.String(128), nullable=True), \
								sa.Column('data_origen_reg_id', sa.types.Integer, nullable=True))
			orm.mapper(UserRoleO, def_users_roles_o)
			orm.mapper(UserRoleD, def_users_roles_d)
			def_usuarios_o = sa.Table('Usuarios', self.db_origen['metadata'], autoload=True)
			def_usuarios_d = sa.Table('Usuarios', self.db_destino['metadata'], autoload=True)
			orm.mapper(UsuarioO, def_usuarios_o)
			orm.mapper(UsuarioD, def_usuarios_d)
			def_medicos_o = sa.Table('Medicos', self.db_origen['metadata'], autoload=True)
			def_medicos_d = sa.Table('Medicos', self.db_destino['metadata'], autoload=True)
			orm.mapper(MedicoO, def_medicos_o)
			orm.mapper(MedicoD, def_medicos_d)
			def_rel_medicos_servicios_o = sa.Table('rel_Medicos_Servicios', self.db_origen['metadata'], autoload=True)
			def_rel_medicos_servicios_d = sa.Table('rel_Medicos_Servicios', self.db_destino['metadata'], autoload=True)
			orm.mapper(Rel_Medicos_ServiciosO, def_rel_medicos_servicios_o)
			orm.mapper(Rel_Medicos_ServiciosD, def_rel_medicos_servicios_d)
			def_rel_medicos_agendas_o = sa.Table('rel_Medicos_Agendas', self.db_origen['metadata'], autoload=True)
			def_rel_medicos_agendas_d = sa.Table('rel_Medicos_Agendas', self.db_destino['metadata'], autoload=True)
			orm.mapper(Rel_Medicos_AgendasO, def_rel_medicos_agendas_o)
			orm.mapper(Rel_Medicos_AgendasD, def_rel_medicos_agendas_d)
			def_aseguradoras_o = sa.Table('Aseguradoras', self.db_origen['metadata'], autoload=True)
			def_aseguradoras_d = sa.Table('Aseguradoras', self.db_destino['metadata'], autoload=True)
			orm.mapper(AseguradoraO, def_aseguradoras_o)
			orm.mapper(AseguradoraD, def_aseguradoras_d)
			def_prioridades_o = sa.Table('Prioridades', self.db_origen['metadata'], autoload=True)
			def_prioridades_d = sa.Table('Prioridades', self.db_destino['metadata'], autoload=True)
			orm.mapper(PrioridadO, def_prioridades_o)
			orm.mapper(PrioridadD, def_prioridades_d)
			def_motivos_cancelacion_o = sa.Table('MotivosCancelacion', self.db_origen['metadata'], autoload=True)
			def_motivos_cancelacion_d = sa.Table('MotivosCancelacion', self.db_destino['metadata'], autoload=True)
			orm.mapper(MotivoCancelacionO, def_motivos_cancelacion_o)
			orm.mapper(MotivoCancelacionD, def_motivos_cancelacion_d)
			def_campos_o = sa.Table('Campos', self.db_origen['metadata'], autoload=True)
			def_campos_d = sa.Table('Campos', self.db_destino['metadata'], autoload=True)
			orm.mapper(CampoO, def_campos_o)
			orm.mapper(CampoD, def_campos_d)
			def_textos_predefinidos_o = sa.Table('TextosPredefinidos', self.db_origen['metadata'], autoload=True)
			def_textos_predefinidos_d = sa.Table('TextosPredefinidos', self.db_destino['metadata'], autoload=True)
			orm.mapper(TextoPredefinidoO, def_textos_predefinidos_o)
			orm.mapper(TextoPredefinidoD, def_textos_predefinidos_d)
			def_grupos_campos_o = sa.Table('GruposCampos', self.db_origen['metadata'], autoload=True)
			def_grupos_campos_d = sa.Table('GruposCampos', self.db_destino['metadata'], autoload=True)
			orm.mapper(GrupoCamposO, def_grupos_campos_o)
			orm.mapper(GrupoCamposD, def_grupos_campos_d)
			def_elementos_o = sa.Table('Elementos', self.db_origen['metadata'], autoload=True)
			def_elementos_d = sa.Table('Elementos', self.db_destino['metadata'], autoload=True)
			orm.mapper(ElementoO, def_elementos_o)
			orm.mapper(ElementoD, def_elementos_d)
			def_formularios_o = sa.Table('Formularios', self.db_origen['metadata'], autoload=True)
			def_formularios_d = sa.Table('Formularios', self.db_destino['metadata'], autoload=True)
			orm.mapper(FormularioO, def_formularios_o)
			orm.mapper(FormularioD, def_formularios_d)
			def_rel_campos_formularios_o = sa.Table('rel_Campos_Formularios', self.db_origen['metadata'], autoload=True)
			def_rel_campos_formularios_d = sa.Table('rel_Campos_Formularios', self.db_destino['metadata'], autoload=True)
			orm.mapper(Rel_Campos_FormulariosO, def_rel_campos_formularios_o)
			orm.mapper(Rel_Campos_FormulariosD, def_rel_campos_formularios_d)
			def_rel_grupocampos_formularios_o = sa.Table('rel_GruposCampos_Formularios', self.db_origen['metadata'], autoload=True)
			def_rel_grupocampos_formularios_d = sa.Table('rel_GruposCampos_Formularios', self.db_destino['metadata'], autoload=True)
			orm.mapper(Rel_GruposCampos_FormulariosO, def_rel_grupocampos_formularios_o)
			orm.mapper(Rel_GruposCampos_FormulariosD, def_rel_grupocampos_formularios_d)
			def_valores_por_defecto_o = sa.Table('ValoresPorDefecto', self.db_origen['metadata'], autoload=True)
			def_valores_por_defecto_d = sa.Table('ValoresPorDefecto', self.db_destino['metadata'], autoload=True)
			orm.mapper(ValorPorDefectoO, def_valores_por_defecto_o)
			orm.mapper(ValorPorDefectoD, def_valores_por_defecto_d)
			def_tipos_exploracion_o = sa.Table('TiposExploracion', self.db_origen['metadata'], autoload=True)
			def_tipos_exploracion_d = sa.Table('TiposExploracion', self.db_destino['metadata'], autoload=True)
			orm.mapper(TipoExploracionO, def_tipos_exploracion_o)
			orm.mapper(TipoExploracionD, def_tipos_exploracion_d)
			def_rel_forms_tiposexpl_o = sa.Table('rel_Forms_TiposExpl', self.db_origen['metadata'], autoload=True)
			def_rel_forms_tiposexpl_d = sa.Table('rel_Forms_TiposExpl', self.db_destino['metadata'], autoload=True)
			orm.mapper(Rel_Formularios_TiposExploracionO, def_rel_forms_tiposexpl_o)
			orm.mapper(Rel_Formularios_TiposExploracionD, def_rel_forms_tiposexpl_d)
			def_rel_serv_tiposexpl_o = sa.Table('rel_Serv_TiposExpl', self.db_origen['metadata'], autoload=True)
			def_rel_serv_tiposexpl_d = sa.Table('rel_Serv_TiposExpl', self.db_destino['metadata'], autoload=True)
			orm.mapper(Rel_Servicios_TiposExploracionO, def_rel_serv_tiposexpl_o)
			orm.mapper(Rel_Servicios_TiposExploracionD, def_rel_serv_tiposexpl_d)
			def_poblaciones_o = sa.Table('Poblaciones', self.db_origen['metadata'], autoload=True)
			def_poblaciones_d = sa.Table('Poblaciones', self.db_destino['metadata'], autoload=True)
			orm.mapper(PoblacionO, def_poblaciones_o)
			orm.mapper(PoblacionD, def_poblaciones_d)
			def_provincias_o = sa.Table('Provincias', self.db_origen['metadata'], autoload=True)
			def_provincias_d = sa.Table('Provincias', self.db_destino['metadata'], autoload=True)
			orm.mapper(ProvinciaO, def_provincias_o)
			orm.mapper(ProvinciaD, def_provincias_d)
			def_pacientes_o = sa.Table('Pacientes', self.db_origen['metadata'], autoload=True)
			def_pacientes_d = sa.Table('Pacientes', self.db_destino['metadata'], autoload=True)
			orm.mapper(PacienteO, def_pacientes_o)
			orm.mapper(PacienteD, def_pacientes_d)
			def_rel_paciente_centro_o = sa.Table('rel_Pacientes_Centros', self.db_origen['metadata'], autoload=True)
			def_rel_paciente_centro_d = sa.Table('rel_Pacientes_Centros', self.db_destino['metadata'], autoload=True)
			orm.mapper(Rel_Pacientes_CentrosO, def_rel_paciente_centro_o)
			orm.mapper(Rel_Pacientes_CentrosD, def_rel_paciente_centro_d)
			def_exploraciones_o = sa.Table('Exploraciones', self.db_origen['metadata'], autoload=True)
			def_exploraciones_d = sa.Table('Exploraciones', self.db_destino['metadata'], autoload=True)
			orm.mapper(ExploracionO, def_exploraciones_o)
			orm.mapper(ExploracionD, def_exploraciones_d)
			self.def_exploraciones_dicom_o = sa.Table('Exploraciones_dicom', self.db_origen['metadata'], autoload=True)
			self.def_exploraciones_dicom_d = sa.Table('Exploraciones_dicom', self.db_destino['metadata'], autoload=True)
			orm.mapper(Exploracion_dicomO, self.def_exploraciones_dicom_o)
			orm.mapper(Exploracion_dicomD, self.def_exploraciones_dicom_d)
			self.def_rel_form_expl_o = sa.Table('rel_Formularios_Exploraciones', self.db_origen['metadata'], autoload=True)
			self.def_rel_form_expl_d = sa.Table('rel_Formularios_Exploraciones', self.db_destino['metadata'], autoload=True)
			orm.mapper(Rel_Formularios_ExploracionesO, self.def_rel_form_expl_o)
			orm.mapper(Rel_Formularios_ExploracionesD, self.def_rel_form_expl_d)
			self.def_valores_texto_o = sa.Table('ValoresTexto', self.db_origen['metadata'], autoload=True)
			self.def_valores_texto_d = sa.Table('ValoresTexto', self.db_destino['metadata'], autoload=True)
			orm.mapper(ValorTextoO, self.def_valores_texto_o)
			orm.mapper(ValorTextoD, self.def_valores_texto_d)
			self.def_valores_select_o = sa.Table('ValoresSelec', self.db_origen['metadata'], autoload=True)
			self.def_valores_select_d = sa.Table('ValoresSelec', self.db_destino['metadata'], autoload=True)
			orm.mapper(ValorSelecO, self.def_valores_select_o)
			orm.mapper(ValorSelecD, self.def_valores_select_d)
			self.def_valores_multi_o = sa.Table('ValoresMulti', self.db_origen['metadata'], autoload=True)
			self.def_valores_multi_d = sa.Table('ValoresMulti', self.db_destino['metadata'], autoload=True)
			orm.mapper(ValorMultiO, self.def_valores_multi_o)
			orm.mapper(ValorMultiD, self.def_valores_multi_d)
			self.def_valores_bool_o = sa.Table('ValoresBool', self.db_origen['metadata'], autoload=True)
			self.def_valores_bool_d = sa.Table('ValoresBool', self.db_destino['metadata'], autoload=True)
			orm.mapper(ValorBoolO, self.def_valores_bool_o)
			orm.mapper(ValorBoolD, self.def_valores_bool_d)
			self.def_capturas_o = sa.Table('Capturas', self.db_origen['metadata'], autoload=True)
			self.def_capturas_d = sa.Table('Capturas', self.db_destino['metadata'], autoload=True)
			orm.mapper(CapturaO, self.def_capturas_o)
			orm.mapper(CapturaD, self.def_capturas_d)
			self.def_informes_o = sa.Table('Informes', self.db_origen['metadata'], autoload=True)
			self.def_informes_d = sa.Table('Informes', self.db_destino['metadata'], autoload=True)
			orm.mapper(InformeO, self.def_informes_o)
			orm.mapper(InformeD, self.def_informes_d)
			self.def_rel_capturas_informes_o = sa.Table('rel_Capturas_Informes', self.db_origen['metadata'], autoload=True)
			self.def_rel_capturas_informes_d = sa.Table('rel_Capturas_Informes', self.db_destino['metadata'], autoload=True)
			orm.mapper(Rel_Capturas_InformesO, self.def_rel_capturas_informes_o)
			orm.mapper(Rel_Capturas_InformesD, self.def_rel_capturas_informes_d)
			def_citas_o = sa.Table('Citas', self.db_origen['metadata'], autoload=True)
			def_citas_d = sa.Table('Citas', self.db_destino['metadata'], autoload=True)
			orm.mapper(CitaO, def_citas_o)
			orm.mapper(CitaD, def_citas_d)

		except sa.exceptions.ArgumentError:
			# Este error es cuando ya estan mapeadas, no hace
			# falta hacer nada
			pass

	def sa_one_error(query):
		if query.count() > 1:
			# tiene multiples resultados, es un error
			return True
		return False

	def sa_one_or_none(query):
		if query.count() == 0:
			return None
		elif query.count() == 1:
			return query.one()
		else: 
			raise Exception("Error de multiple registros")

	def get_row_des_from_ori_id(self, db_class, origen_id, return_bool = False):
		""" obtiene la fila en destino que esta mapeada con el
			origen_id en el campo data_origen_reg_id
			Si no encuentra devuelve un error
			Si hay mas de 1 devuelve error
			Si return_bool es True entonces devuelve:
				True si encuentra 1 fila
				False si encuentra 0 filas
				Error si encuentra multiples
		"""
		class_name = db_class.__name__
		des_row = self.des_session.query(db_class) \
					  .filter(and_(db_class.data_origen_uid == self.uid_origen, \
					  			   db_class.data_origen_reg_id == origen_id))

		if des_row.count() == 0:
			if return_bool:
				return False
			msg = 'No se encontro el registro con id origen: %s en la tabla destino: %s' % (str(origen_id), class_name)
			self.write_log(msg, LOG_ERROR)
			raise CeroFilasError(msg)

		if des_row.count() > 1: 
			msg = 'Existen multiples registros con el id origen: %s en la tabla destino: %s' % (str(origen_id), class_name)
			self.write_log(msg, LOG_ERROR)
			raise MultipleFilasError(msg)
		else:
			if return_bool:
				return True
			return des_row.one()

	def update_data_destino_uid(self, origen_row):
		origen_row.data_destino_uid = self.uid_destino
		self.ori_session.update(origen_row)
		self.ori_session.commit()

	def save_new_row_destino(self, db_object):
		self.des_session.save(db_object)
		self.des_session.commit()

	def crear_obj_paciente(request, ori_paciente):
		# buscar aseguradora
		des_aseguradora_id = None
		if ori_paciente.aseguradora_id:
			des_aseguradora = self.get_row_des_from_ori_id(AseguradoraD, ori_paciente.aseguradora_id)
			des_aseguradora_id = des_aseguradora.id

		paciente = PacienteD()
		paciente.idunico = ori_paciente.idunico  
		paciente.CIP = ori_paciente.CIP
		paciente.DNI = ori_paciente.DNI
		paciente.nombre = ori_paciente.nombre 
		paciente.apellido1 = ori_paciente.apellido1 
		paciente.apellido2 = ori_paciente.apellido2 
		paciente.sexo = ori_paciente.sexo
		paciente.fechaNacimiento = ori_paciente.fechaNacimiento
		paciente.direccion = ori_paciente.direccion
		paciente.poblacion = ori_paciente.poblacion
		paciente.provincia = ori_paciente.provincia
		paciente.codigoPostal = ori_paciente.codigoPostal 
		paciente.aseguradora_id = des_aseguradora_id
		paciente.numAfiliacion = ori_paciente.numAfiliacion 
		paciente.telefono1 = ori_paciente.telefono1 
		paciente.telefono2 = ori_paciente.telefono2 
		paciente.comentarios = ori_paciente.comentarios 
		paciente.numero_expediente = ori_paciente.numero_expediente 
		paciente.deshabilitado = ori_paciente.deshabilitado
		return paciente

	def migrar_datos_auxiliares(self):
		error = False
		self.ori_session = self.crear_session('origen')	
		self.des_session = self.crear_session('destino')
		# aqui se guardan cosas importantes que se mostraran en la UI
		output_ui = []
		user_id_excludes = []

		# ------
		# migrar salas 
		self.write_log(MSG_START % (SalaD.__name__), LOG_INFO)
		migradas_nuevas = 0
		migradas_anteriormente = 0
		ori_salas_result = self.ori_session.query(SalaO).all()
		output_ui.append(MSG_DISP % (SalaO.__name__, len(ori_salas_result)))
		self.write_log(MSG_DISP % (SalaO.__name__, len(ori_salas_result)),LOG_INFO)
		for ori_sala in ori_salas_result:
			# comprobar que la sala que se quiere migrar no este previamente migrada.
			des_sala = self.get_row_des_from_ori_id(SalaD, ori_sala.id, True)

			if not des_sala:
				#buscar el centro mapeado
				centro_des = self.get_row_des_from_ori_id(CentroD, ori_sala.centro_id)

				#crear la sala si no se migro anteriormente.
				sala = SalaD()
				sala.nombre = ori_sala.nombre
				sala.centro_id = centro_des.id
				sala.data_origen_uid = self.uid_origen
				sala.data_origen_reg_id = ori_sala.id
				self.save_new_row_destino(sala)
				self.update_data_destino_uid(ori_sala)

				self.write_log(MSG_NUEVA % (SalaO.__name__, str(ori_sala.id)), LOG_INFO)
				migradas_nuevas += 1
			else:
				self.write_log(MSG_MIGRADA % (SalaO.__name__, str(ori_sala.id)), LOG_INFO)
				migradas_anteriormente += 1
		
		output_ui.append(MSG_TOTAL_NEW_ANT % (SalaD.__name__, migradas_nuevas, migradas_anteriormente))
		self.write_log(MSG_TOTAL_NEW_ANT % (SalaD.__name__, migradas_nuevas, migradas_anteriormente), LOG_INFO)
		self.write_log(MSG_END % (SalaD.__name__), LOG_INFO)

		# ------
		# migrar rel_salas_servicios
		self.write_log(MSG_START % (Rel_Salas_ServiciosD.__name__), LOG_INFO)
		migradas_nuevas = 0
		migradas_anteriormente = 0
		ori_rel_salas_servicios_result = self.ori_session.query(Rel_Salas_ServiciosO).all()
		self.write_log(MSG_DISP % (Rel_Salas_ServiciosO.__name__, len(ori_rel_salas_servicios_result)), LOG_INFO)
		output_ui.append(MSG_DISP % (Rel_Salas_ServiciosO.__name__, len(ori_rel_salas_servicios_result)))
		for ori_rel_sala_servicio in ori_rel_salas_servicios_result:
			#buscar la sala origen en la base de datos destino
			sala_des = self.get_row_des_from_ori_id(SalaD, ori_rel_sala_servicio.sala_id)

			#buscar el servicio origen en la base de datos destino
			servicio_des = self.get_row_des_from_ori_id(ServicioD, ori_rel_sala_servicio.servicio_id)

			# comprobar que la relacion de rel_sala_servicio no este creada
			des_rel_sala_servicio = self.des_session.query(Rel_Salas_ServiciosD) \
									.filter(and_(Rel_Salas_ServiciosD.sala_id == sala_des.id, \
										         Rel_Salas_ServiciosD.servicio_id == servicio_des.id))
			if des_rel_sala_servicio.count() == 0:
				#crear la relacion
				rel_sala_servicio = Rel_Salas_ServiciosD()
				rel_sala_servicio.sala_id = sala_des.id
				rel_sala_servicio.servicio_id = servicio_des.id
				rel_sala_servicio.data_origen_uid = self.uid_origen
				self.save_new_row_destino(rel_sala_servicio)
				self.update_data_destino_uid(ori_rel_sala_servicio)

				self.write_log("Nuevo rel_salas_servicios en Destino [sala_id= " + \
							   str(rel_sala_servicio.sala_id) + ",servicio_id=" + \
							   str(rel_sala_servicio.servicio_id) + "]" ,LOG_INFO)
				migradas_nuevas += 1
			else:
				self.write_log("Ya existe rel_salas_servicios en Destino [sala_id= " + \
							   str(sala_des.id) + ",servicio_id=" + \
							   str(servicio_des.id) + "]" ,LOG_INFO)
				migradas_anteriormente += 1

		output_ui.append(MSG_TOTAL_NEW_ACT % (Rel_Salas_ServiciosD.__name__, migradas_nuevas, migradas_anteriormente))
		self.write_log(MSG_TOTAL_NEW_ACT % (Rel_Salas_ServiciosD.__name__, migradas_nuevas, migradas_anteriormente), LOG_INFO)
		self.write_log(MSG_END % (Rel_Salas_ServiciosD.__name__), LOG_INFO)

		# ------
		# migrar agendas
		self.write_log(MSG_START % (AgendaD.__name__), LOG_INFO)
		migradas_nuevas = 0
		migradas_anteriormente = 0 
		ori_agendas_result = self.ori_session.query(AgendaO).all()
		self.write_log(MSG_DISP % (AgendaO.__name__, len(ori_agendas_result)), LOG_INFO)
		output_ui.append(MSG_DISP % (AgendaO.__name__, len(ori_agendas_result)))
		for ori_agenda in ori_agendas_result:

			des_agenda = self.get_row_des_from_ori_id(AgendaD, ori_agenda.id, True)
			if not des_agenda:
				#buscar el servicio origen en la base de datos destino
				servicio_des = self.get_row_des_from_ori_id(ServicioD, ori_agenda.servicio_id)

				#crear agenda
				agenda = AgendaD()
				agenda.nombre = ori_agenda.nombre
				agenda.codigo = ori_agenda.codigo
				agenda.servicio_id = servicio_des.id
				agenda.data_origen_uid = self.uid_origen
				agenda.data_origen_reg_id = ori_agenda.id
				
				self.save_new_row_destino(agenda)
				self.update_data_destino_uid(ori_agenda)

				self.write_log(MSG_NUEVA % (AgendaO.__name__, str(ori_agenda.id)), LOG_INFO)
				migradas_nuevas += 1
			else:
				self.write_log(MSG_MIGRADA % (AgendaO.__name__, str(ori_agenda.id)), LOG_INFO)
				migradas_anteriormente += 1

		output_ui.append(MSG_TOTAL_NEW_ACT % (AgendaD.__name__, migradas_nuevas, migradas_anteriormente))
		self.write_log(MSG_TOTAL_NEW_ACT % (AgendaD.__name__, migradas_nuevas, migradas_anteriormente), LOG_INFO)
		self.write_log(MSG_END % (AgendaD.__name__), LOG_INFO)

		# ------
		#migrar rel_salas_agendas
		self.write_log(MSG_START % (Rel_Salas_AgendasD.__name__), LOG_INFO)
		migradas_nuevas = 0
		migradas_anteriormente = 0
		ori_rel_salas_agendas_result = self.ori_session.query(Rel_Salas_AgendasO).all()
		self.write_log(MSG_DISP % (Rel_Salas_AgendasO.__name__, len(ori_rel_salas_agendas_result)), LOG_INFO)
		output_ui.append(MSG_DISP % (Rel_Salas_AgendasO.__name__, len(ori_rel_salas_agendas_result)))
		for ori_rel_sala_agenda in ori_rel_salas_agendas_result:
			
			#buscar la sala origen en la base de datos destino
			sala_des = self.get_row_des_from_ori_id(SalaD, ori_rel_sala_agenda.sala_id) 

			#buscar el agenda origen en la base de datos destino
			agenda_des = self.get_row_des_from_ori_id(AgendaD, ori_rel_sala_agenda.agenda_id) 

			# comprobar si existe o no
			des_rel_sala_agenda = self.des_session.query(Rel_Salas_AgendasD) \
									.filter(and_(Rel_Salas_AgendasD.agenda_id == agenda_des.id, \
										         Rel_Salas_AgendasD.sala_id == sala_des.id))
			if des_rel_sala_agenda.count() == 0:
				# no existe, creo
				rel_sala_agenda = Rel_Salas_AgendasD()
				rel_sala_agenda.sala_id = sala_des.id
				rel_sala_agenda.agenda_id = agenda_des.id
				rel_sala_agenda.data_origen_uid = self.uid_origen
				self.save_new_row_destino(rel_sala_agenda)
				self.update_data_destino_uid(ori_rel_sala_agenda)

				self.write_log("Nuevo rel_salas_agenda en Destino [sala_id= " + \
							   str(rel_sala_agenda.sala_id) + ",agenda_id=" + \
							   str(rel_sala_agenda.agenda_id) + "]" ,LOG_INFO)
				migradas_nuevas += 1
			else:
				# ya existe, no hago nada
				self.write_log("Ya existe rel_salas_agenda en Destino [sala_id= " + \
							   str(sala_des.id) + ",agenda_id=" + \
							   str(agenda_des.id) + "]" ,LOG_INFO)
				migradas_anteriormente += 1

		output_ui.append(MSG_TOTAL_NEW_ACT % (Rel_Salas_AgendasD.__name__, migradas_nuevas, migradas_anteriormente))
		self.write_log(MSG_TOTAL_NEW_ACT % (Rel_Salas_AgendasD.__name__, migradas_nuevas, migradas_anteriormente), LOG_INFO)
		self.write_log(MSG_END % (Rel_Salas_AgendasD.__name__), LOG_INFO)

		# ------
		#migrar horariosagendas
		self.write_log(MSG_START % (HorarioAgendaD.__name__), LOG_INFO)
		migradas_nuevas = 0
		migradas_anteriormente = 0
		ori_horariosagendas_result = self.ori_session.query(HorarioAgendaO).all()
		self.write_log(MSG_DISP % (HorarioAgendaO.__name__, len(ori_horariosagendas_result)), LOG_INFO)
		output_ui.append(MSG_DISP % (HorarioAgendaO.__name__, len(ori_horariosagendas_result)))
		for ori_horarioagenda in ori_horariosagendas_result:
			#buscar el agenda origen en la base de datos destino
			agenda_des = self.get_row_des_from_ori_id(AgendaD, ori_horarioagenda.agenda_id) 

			#comprobar que horariosgenda no exista 
			des_horarioagenda = self.des_session.query(HorarioAgendaD) \
									.filter(and_(HorarioAgendaD.agenda_id == agenda_des.id, \
										         HorarioAgendaD.hora_ini == ori_horarioagenda.hora_ini, \
										         HorarioAgendaD.hora_fin == ori_horarioagenda.hora_fin, \
										         HorarioAgendaD.dia_semana == ori_horarioagenda.dia_semana, \
										         HorarioAgendaD.data_origen_uid == self.uid_origen))
			
			if des_horarioagenda.count() == 0:
				horarioagenda = HorarioAgendaD()
				horarioagenda.agenda_id = agenda_des.id
				horarioagenda.hora_ini = ori_horarioagenda.hora_ini
				horarioagenda.hora_fin = ori_horarioagenda.hora_fin
				horarioagenda.dia_semana = ori_horarioagenda.dia_semana
				horarioagenda.data_origen_uid = self.uid_origen
				self.save_new_row_destino(horarioagenda)
				self.update_data_destino_uid(ori_horarioagenda)

				self.write_log(MSG_NUEVA % (HorarioAgendaO.__name__, "-"), LOG_INFO)
				migradas_nuevas += 1
			else:
				self.write_log(MSG_MIGRADA % (HorarioAgendaO.__name__, "-"), LOG_INFO)
				migradas_anteriormente += 1

		output_ui.append(MSG_TOTAL_NEW_ACT % (HorarioAgendaD.__name__, migradas_nuevas, migradas_anteriormente))
		self.write_log(MSG_TOTAL_NEW_ACT % (HorarioAgendaD.__name__, migradas_nuevas, migradas_anteriormente), LOG_INFO)
		self.write_log(MSG_END % (HorarioAgendaD.__name__), LOG_INFO)

		# migrar workstation
		self.write_log(MSG_START % (WorkstationD.__name__), LOG_INFO)
		migradas_nuevas = 0
		migradas_anteriormente = 0
		excluidos = 0
		nuevo_rel_servicio_workstation = 0
		migrado_rel_servicio_workstation = 0
		ori_workstations_result = self.ori_session.query(WorkstationO).all()
		self.write_log(MSG_DISP % (WorkstationO.__name__, len(ori_workstations_result)), LOG_INFO)
		output_ui.append(MSG_DISP % (WorkstationO.__name__, len(ori_workstations_result)))
		for ori_workstation in ori_workstations_result:
			#comprobar que el workstation no este creada
			migrado = True
			des_workstation = self.des_session.query(WorkstationD) \
								.filter(and_(WorkstationD.data_origen_reg_id == ori_workstation.id, \
										 	 WorkstationD.data_origen_uid == self.uid_origen))
			if des_workstation.count() == 0:
				#controla que no exista un workstation con la misma IP asi no hay conflictos.
				des_workstation_ip = self.des_session.query(WorkstationD) \
										 .filter(WorkstationD.ip==ori_workstation.ip)
				if des_workstation_ip.count() == 0:
					
					workstation_borrado = False
					if ori_workstation.borrado:
						workstation_borrado = ori_workstation.borrado

					# crear workstation
					workstation = WorkstationD()
					workstation.nombre = ori_workstation.nombre 
					workstation.ip = ori_workstation.ip
					workstation.tipo = ori_workstation.tipo
					workstation.borrado = workstation_borrado
					workstation.borrado_motivo = ori_workstation.borrado_motivo
					workstation.data_origen_uid = self.uid_origen
					workstation.data_origen_reg_id = ori_workstation.id

					self.save_new_row_destino(workstation)
					self.update_data_destino_uid(ori_workstation)

					self.write_log(MSG_NUEVA % (WorkstationO.__name__, str(ori_workstation.id)), LOG_INFO)
					migradas_nuevas += 1
				else:
					# ya existe un workstation con esa IP
					msg = "No se puede migrar el Workstation ni los Rel_Servicio_Workstation porque" + \
						  " ya existe el workstation con esa IP en Destino. workstation ID (Origen): " + \
					   	  str(ori_workstation.id)
					output_ui.append(msg)
					self.write_log(msg ,LOG_INFO)
					migrado = False
					excluidos += 1
			else:
				self.write_log(MSG_MIGRADA % (WorkstationO.__name__, str(ori_workstation.id)), LOG_INFO)
				migradas_anteriormente += 1

			# si se migro entonces agrego la relacion workstation servicio
			if migrado:
				
				#migrar Rel_Servicios_Workstations
				ori_servicios_workstations_result = self.ori_session.query(Rel_Servicios_WorkstationsO) \
														.filter(Rel_Servicios_WorkstationsO.workstation_id == ori_workstation.id) \
														.all()

				for ori_rel_servicio_workstation in ori_servicios_workstations_result:

					#buscar el servicio origen en la base de datos destino
					servicio_des = self.get_row_des_from_ori_id(ServicioD, ori_rel_servicio_workstation.servicio_id)

					#buscar el workstation origen en la base de datos destino
					workstation_des = self.get_row_des_from_ori_id(WorkstationD, ori_rel_servicio_workstation.workstation_id) 
				
					# comprobar si existe o no
					des_rel_servicio_workstation = self.des_session.query(Rel_Servicios_WorkstationsD) \
											.filter(and_(Rel_Servicios_WorkstationsD.workstation_id == workstation_des.id, \
												         Rel_Servicios_WorkstationsD.servicio_id == servicio_des.id))

					if des_rel_servicio_workstation.count() == 0:

						rel_servicio_workstation = Rel_Servicios_WorkstationsD()
						rel_servicio_workstation.workstation_id = workstation_des.id
						rel_servicio_workstation.servicio_id = servicio_des.id
						rel_servicio_workstation.data_origen_uid = self.uid_origen
						
						self.save_new_row_destino(rel_servicio_workstation)
						self.update_data_destino_uid(ori_rel_servicio_workstation)

						self.write_log("Nuevo rel_servicio_workstation en Destino [servicio_id= " + \
								   str(rel_servicio_workstation.servicio_id) + ",agenda_id=" + \
								   str(rel_servicio_workstation.workstation_id) + "]" ,LOG_INFO) 
						nuevo_rel_servicio_workstation += 1
					else:
						# ya existe, no hago nada
						self.write_log("Ya existe rel_servicio_workstation en Destino [servicio_id= " + \
									   str(servicio_des.id) + ",workstation_id=" + \
									   str(workstation_des.id) + "]" ,LOG_INFO)
						migrado_rel_servicio_workstation += 1

		output_ui.append(MSG_TOTAL_NEW_ACT_EXC % (WorkstationD.__name__, migradas_nuevas, migradas_anteriormente, excluidos))
		self.write_log(MSG_TOTAL_NEW_ACT_EXC % (WorkstationD.__name__, migradas_nuevas, migradas_anteriormente, excluidos), LOG_INFO)
		self.write_log(MSG_END % (WorkstationD.__name__), LOG_INFO)


		self.write_log(MSG_START % (Rel_Servicios_WorkstationsD.__name__), LOG_INFO)
		output_ui.append(MSG_DISP % (Rel_Servicios_WorkstationsO.__name__, nuevo_rel_servicio_workstation+migrado_rel_servicio_workstation))
		self.write_log(MSG_DISP % (Rel_Servicios_WorkstationsO.__name__, nuevo_rel_servicio_workstation+migrado_rel_servicio_workstation), LOG_INFO)
		output_ui.append(MSG_TOTAL_NEW_ACT % (Rel_Servicios_WorkstationsD.__name__, nuevo_rel_servicio_workstation, migrado_rel_servicio_workstation))
		self.write_log(MSG_TOTAL_NEW_ACT % (Rel_Servicios_WorkstationsD.__name__, nuevo_rel_servicio_workstation, migrado_rel_servicio_workstation), LOG_INFO)
		self.write_log(MSG_END % (Rel_Servicios_WorkstationsD.__name__), LOG_INFO)

		# users
		self.write_log(MSG_START % (UserD.__name__), LOG_INFO)
		migradas_nuevas = 0
		migradas_anteriormente = 0
		excluidos = 0
		ori_users_result = self.ori_session.query(UserO).all()
		output_ui.append(MSG_DISP % (UserO.__name__, len(ori_users_result)))
		self.write_log(MSG_DISP % (UserO.__name__, len(ori_users_result)), LOG_INFO)
		
		for ori_user in ori_users_result:

			if ori_user.username not in USERNAME_EXCLUDES:

				#comprobar que el user no este creada
				des_user = self.get_row_des_from_ori_id(UserD, ori_user.id, True)

				if not des_user:
					# busca si el nombre de usuario esta usado ya en endosys ----
					# la primera busqueda es con el nombre igual
					numero_user = 0
					nombre_numero = None
					nombre_cambiado = False
					username = ori_user.username
					nombre_existe = self.des_session.query(UserD).filter(UserD.username == ori_user.username)
					while nombre_existe.count() != 0:
						# las proximas busquedas son con el nombre + un numero.
						numero_user += 1
						nombre_numero = username + str(numero_user) 
						nombre_existe = self.des_session.query(UserD).filter(UserD.username == nombre_numero)

					# si el campo tiene que ser un nombre con un numero lo asigna.
					# si es none es pq nunca entro al primer while y esta disponible el nombre del campo original
					if nombre_numero:
						username = nombre_numero
						nombre_cambiado = True


					# crear user porque no existe.
					user = UserD()
					user.username = username
					user.password = ori_user.password
					user.data_origen_uid = self.uid_origen
					user.data_origen_reg_id = ori_user.id
					self.save_new_row_destino(user)
					self.update_data_destino_uid(ori_user)

					self.write_log(MSG_NUEVA % (UserO.__name__, str(ori_user.id)), LOG_INFO)

					if nombre_cambiado:
						msg = "Username cambiado %s > %s " % (ori_user.username, username) 
						self.write_log(msg,LOG_WARNING)
						output_ui.append(msg)

					migradas_nuevas += 1
				else:
					self.write_log(MSG_MIGRADA % (UserO.__name__, str(ori_user.id)), LOG_INFO)
					migradas_anteriormente += 1
			else:
				user_id_excludes.append(ori_user.id)
				msg = "El usuario %s esta excluido de la migracion" % (ori_user.username)
				output_ui.append(msg)
				self.write_log(msg,LOG_INFO)
				excluidos += 1

		output_ui.append(MSG_TOTAL_NEW_ACT_EXC % (UserD.__name__, migradas_nuevas, migradas_anteriormente, excluidos))
		self.write_log(MSG_TOTAL_NEW_ACT_EXC % (UserD.__name__, migradas_nuevas, migradas_anteriormente, excluidos), LOG_INFO)
		self.write_log(MSG_END % (UserD.__name__), LOG_INFO)

		# ------
		# migrar users_roles
		self.write_log(MSG_START % (UserRoleD.__name__), LOG_INFO)
		migradas_nuevas = 0
		migradas_anteriormente = 0
		excluidos = 0
		ori_users_roles_result = self.ori_session.query(UserRoleO).all()
		self.write_log(MSG_DISP % (UserRoleO.__name__, len(ori_users_roles_result)), LOG_INFO)
		output_ui.append(MSG_DISP % (UserRoleO.__name__, len(ori_users_roles_result)))
		for ori_user_role in ori_users_roles_result:

			#los roles tienen el mismo id en todas las basde de endosys
			# por lo tanto no es necesario buscarlos en destino para mapearlos con origen

			# comprobar si esta excluido
			exclude_user = False
			if ori_user_role.user_id in user_id_excludes:
				exclude_user = True

			if not exclude_user:
				# buscar el id de usuario en bd destino
				des_user = self.get_row_des_from_ori_id(UserD, ori_user_role.user_id)

				#buscar el rol por el nombre del role ya que los id pueden ser distinos
				ori_role = self.ori_session.query(RoleO).filter(RoleO.id == ori_user_role.role_id).first()
				name = ori_role.name
				des_role = self.des_session.query(RoleD).filter(RoleD.name == name).first()

				#checkear si el user_role ya existe
				des_user_role = self.des_session.query(UserRoleD) \
									.filter(and_(UserRoleD.role_id == des_role.id, \
												 UserRoleD.user_id == des_user.id))

				if des_user_role.count() == 0 and not exclude_user:
					#no existe, crear
					user_role = UserRoleD()
					user_role.role_id = des_role.id
					user_role.user_id = des_user.id
					user_role.data_origen_uid = self.uid_origen

					self.save_new_row_destino(user_role)
					self.update_data_destino_uid(ori_user_role)

					self.write_log("Nuevo user_role [user_id= " + str(user_role.user_id) + \
								   ",role_id=" + str(user_role.role_id) + "]" ,LOG_INFO)
					migradas_nuevas += 1
				else:
					self.write_log("Ya existe el user_role en Destino [user_id= " + str(des_user.id) + \
								   ",role_id=" + str(ori_user_role.role_id) + "]" ,LOG_INFO)
					migradas_anteriormente += 1
			else:
				self.write_log("No se migro el user_role con user_id: " + str(ori_user_role.user_id) + \
							   " porque esta exluido" ,LOG_INFO)
				excluidos += 1

		output_ui.append(MSG_TOTAL_NEW_ACT_EXC % (UserRoleD.__name__, migradas_nuevas, migradas_anteriormente, excluidos))
		self.write_log(MSG_TOTAL_NEW_ACT_EXC % (UserRoleD.__name__, migradas_nuevas, migradas_anteriormente, excluidos), LOG_INFO)
		self.write_log(MSG_END % (UserRoleD.__name__), LOG_INFO)

		# ------
		# migrar usuarios
		self.write_log(MSG_START % (UsuarioD.__name__), LOG_INFO)
		migradas_nuevas = 0
		migradas_anteriormente = 0
		excluidos = 0
		ori_usuarios_result = self.ori_session.query(UsuarioO).all()
		self.write_log(MSG_DISP % (UsuarioO.__name__, len(ori_usuarios_result)), LOG_INFO)
		output_ui.append(MSG_DISP % (UsuarioO.__name__, len(ori_usuarios_result)))
		for ori_usuario in ori_usuarios_result:
			if ori_usuario.username not in USERNAME_EXCLUDES:
				# buscar el nombre de usuario asignado al user en destino. puede ser distinto al
				# nombre de usuario que tiene en la bd original
				ori_user = self.ori_session.query(UserO).filter(UserO.username==ori_usuario.username).first()
				des_user = self.get_row_des_from_ori_id(UserD, ori_user.id)

				# verifica que ese nombre de usuario ya no este creado en destino y migrado
				existe = False
				if des_user:
					des_usuario =  self.des_session.query(UsuarioD) \
									.filter(and_(UsuarioD.username == des_user.username, \
										 		 UsuarioD.data_origen_uid == self.uid_origen))
					if des_usuario.count() !=0:
						#eencotro ese usuario por lo tanto ya esta migrado
						existe = True
				# el else de des_user nunca deberia pasar, ya q seria un error


				if not existe:
					#crear el usuario
					usuario = UsuarioD()
					usuario.username = des_user.username
					usuario.ldap = ori_usuario.ldap
					usuario.activo = ori_usuario.activo
					usuario.tipo = ori_usuario.tipo
					usuario.clave = ori_usuario.clave
					usuario.data_origen_uid = self.uid_origen
					
					self.save_new_row_destino(usuario)
					self.update_data_destino_uid(ori_usuario)

					self.write_log("Nuevo usuario en Destino, username: " + \
							   		usuario.username ,LOG_INFO)
					migradas_nuevas += 1
				else:
					self.write_log("Ya existe el user en Destino. username: " + \
							   		ori_usuario.username ,LOG_INFO)
					migradas_anteriormente += 1
			else:
				excluidos +=1

		output_ui.append(MSG_TOTAL_NEW_ANT_EXC % (UsuarioD.__name__, migradas_nuevas, migradas_anteriormente, excluidos))
		self.write_log(MSG_TOTAL_NEW_ANT_EXC % (UsuarioD.__name__, migradas_nuevas, migradas_anteriormente, excluidos), LOG_INFO)
		self.write_log(MSG_END % (UsuarioD.__name__), LOG_INFO)

		# ------
		# migrar medicos
		self.write_log(MSG_START % (MedicoD.__name__), LOG_INFO)
		excludes_medico_id = []
		migradas_nuevas = 0
		migradas_anteriormente = 0
		excluidos = 0
		ori_medicos_result = self.ori_session.query(MedicoO).all()
		self.write_log(MSG_DISP % (MedicoO.__name__, len(ori_medicos_result)), LOG_INFO)
		output_ui.append(MSG_DISP % (MedicoO.__name__, len(ori_medicos_result)))
		for ori_medico in ori_medicos_result:
			if ori_medico.username not in USERNAME_EXCLUDES:
				#compobar si se migro anteriormente
				des_medico = self.des_session.query(MedicoD) \
									.filter(and_(MedicoD.data_origen_reg_id == ori_medico.id, \
										 		 MedicoD.data_origen_uid == self.uid_origen))
				if des_medico.count() == 0:
					#busca el nombre de usuario correcto ya que puede ser distinot al original.
					ori_user = self.ori_session.query(UserO).filter(UserO.username==ori_medico.username).first()
					des_user = self.get_row_des_from_ori_id(UserD, ori_user.id)

					#crear el medico
					medico = MedicoD()
					medico.username = des_user.username
					medico.nombre = ori_medico.nombre 
					medico.apellido1 = ori_medico.apellido1
					medico.apellido2 = ori_medico.apellido2
					medico.colegiado = ori_medico.colegiado
					medico.data_origen_uid = self.uid_origen
					medico.data_origen_reg_id = ori_medico.id
					
					self.save_new_row_destino(medico)
					self.update_data_destino_uid(ori_medico)

					self.write_log("Nuevo medico en Destino, username: " + \
							   		medico.username ,LOG_INFO)
					migradas_nuevas += 1
				else:
					self.write_log("Ya existe el medico en Destino. username: " + \
							   		ori_medico.username ,LOG_INFO)
					migradas_anteriormente += 1
			else:
				excluidos +=1
				excludes_medico_id.append(ori_medico.id)

		output_ui.append(MSG_TOTAL_NEW_ACT_EXC % (MedicoD.__name__, migradas_nuevas, migradas_anteriormente, excluidos))
		self.write_log(MSG_TOTAL_NEW_ACT_EXC % (MedicoD.__name__, migradas_nuevas, migradas_anteriormente, excluidos), LOG_INFO)
		self.write_log(MSG_END % (MedicoD.__name__), LOG_INFO)

		# ------
		# migrar rel_medicos_servicios
		self.write_log(MSG_START % (Rel_Medicos_ServiciosD.__name__), LOG_INFO)
		migradas_nuevas = 0
		migradas_anteriormente = 0
		excluidos += 1
		ori_rel_medicos_servicios_result = self.ori_session.query(Rel_Medicos_ServiciosO).all()
		self.write_log(MSG_DISP % (Rel_Medicos_ServiciosO.__name__, len(ori_rel_medicos_servicios_result)), LOG_INFO)
		output_ui.append(MSG_DISP % (Rel_Medicos_ServiciosO.__name__, len(ori_rel_medicos_servicios_result)))
		for ori_rel_medico_servicio in ori_rel_medicos_servicios_result:

			exclude_medico = False
			if ori_rel_medico_servicio.medico_id in excludes_medico_id:
				exclude_medico = True

			if not exclude_medico:
				medico_des = self.get_row_des_from_ori_id(MedicoD, ori_rel_medico_servicio.medico_id)

				# buscar servicio en destino
				servicio_des = self.get_row_des_from_ori_id(ServicioD, ori_rel_medico_servicio.servicio_id)

				# comprobar si existe o no
				des_rel_medico_servicio = self.des_session.query(Rel_Medicos_ServiciosD) \
										.filter(and_(Rel_Medicos_ServiciosD.medico_id == medico_des.id, \
											         Rel_Medicos_ServiciosD.servicio_id == servicio_des.id))

				if des_rel_medico_servicio.count() == 0:
					rel_medico_servicio = Rel_Medicos_ServiciosD()
					rel_medico_servicio.servicio_id = servicio_des.id
					rel_medico_servicio.medico_id = medico_des.id
					rel_medico_servicio.data_origen_uid = self.uid_origen
					
					self.save_new_row_destino(rel_medico_servicio)
					self.update_data_destino_uid(ori_rel_medico_servicio)

					self.write_log("Nuevo rel_medico_servicio en Destino [servicio_id= " + \
							   str(rel_medico_servicio.servicio_id) + ",medico_id=" + \
							   str(rel_medico_servicio.medico_id) + "]" ,LOG_INFO)
					migradas_nuevas += 1
				else:
					# ya existe, no hago nada
					self.write_log("Ya existe rel_medico_servicio en Destino [servicio_id= " + \
								   str(servicio_des.id) + ",medico_id=" + \
								   str(medico_des.id) + "]" ,LOG_INFO)
					migradas_anteriormente += 1
			else:
				excluidos +=1

		output_ui.append(MSG_TOTAL_NEW_ACT_EXC % (Rel_Medicos_ServiciosD.__name__, migradas_nuevas, migradas_anteriormente, excluidos))
		self.write_log(MSG_TOTAL_NEW_ACT_EXC % (Rel_Medicos_ServiciosD.__name__, migradas_nuevas, migradas_anteriormente, excluidos), LOG_INFO)
		self.write_log(MSG_END % (Rel_Medicos_ServiciosD.__name__), LOG_INFO)

		# ------
		# migrar rel_medicos_agendas
		self.write_log(MSG_START % (Rel_Medicos_AgendasD.__name__), LOG_INFO)
		migradas_nuevas = 0
		migradas_anteriormente = 0
		excluidos = 0
		ori_rel_medicos_agendas_result = self.ori_session.query(Rel_Medicos_AgendasO).all()
		self.write_log(MSG_DISP % (Rel_Medicos_AgendasO.__name__, len(ori_rel_medicos_agendas_result)), LOG_INFO)
		output_ui.append(MSG_DISP % (Rel_Medicos_AgendasO.__name__, len(ori_rel_medicos_agendas_result)))
		for ori_rel_medico_agenda in ori_rel_medicos_agendas_result:

			exclude_medico = False
			if ori_rel_medico_agenda.medico_id in excludes_medico_id:
				exclude_medico = True

			if not exclude_medico:
				medico_des = self.get_row_des_from_ori_id(MedicoD, ori_rel_medico_agenda.medico_id)

				# buscar agenda en destino
				agenda_des = self.get_row_des_from_ori_id(AgendaD, ori_rel_medico_agenda.agenda_id)

				# comprobar si existe o no
				des_rel_medico_agenda = self.des_session.query(Rel_Medicos_AgendasD) \
										.filter(and_(Rel_Medicos_AgendasD.medico_id == medico_des.id, \
											         Rel_Medicos_AgendasD.agenda_id == agenda_des.id))

				if des_rel_medico_agenda.count() == 0:
					rel_medico_agenda = Rel_Medicos_AgendasD()
					rel_medico_agenda.agenda_id = agenda_des.id
					rel_medico_agenda.medico_id = medico_des.id
					rel_medico_agenda.data_origen_uid = self.uid_origen
					
					self.save_new_row_destino(rel_medico_agenda)
					self.update_data_destino_uid(ori_rel_medico_agenda)

					self.write_log("Nuevo rel_medicos_agendas en Destino [agenda_id= " + \
							   str(rel_medico_agenda.agenda_id) + ",medico_id=" + \
							   str(rel_medico_agenda.medico_id) + "]" ,LOG_INFO)
					migradas_nuevas += 1
				else:
					# ya existe, no hago nada
					self.write_log("Ya existe rel_medicos_agendas en Destino [agenda_id= " + \
								   str(agenda_des.id) + ",medico_id=" + \
								   str(medico_des.id) + "]" ,LOG_INFO)
					migradas_anteriormente += 1
			else:
				excluidos +=1

		output_ui.append(MSG_TOTAL_NEW_ACT_EXC % (Rel_Medicos_AgendasD.__name__, migradas_nuevas, migradas_anteriormente, excluidos))
		self.write_log(MSG_TOTAL_NEW_ACT_EXC % (Rel_Medicos_AgendasD.__name__, migradas_nuevas, migradas_anteriormente, excluidos), LOG_INFO)
		self.write_log(MSG_END % (Rel_Medicos_AgendasD.__name__), LOG_INFO)

		# ------
		# migrar aseguradoras
		self.write_log(MSG_START % (AseguradoraD.__name__), LOG_INFO)
		migradas_nuevas = 0
		migradas_anteriormente = 0
		ori_aseguradoras_result = self.ori_session.query(AseguradoraO).all()
		self.write_log(MSG_DISP % (AseguradoraO.__name__, len(ori_aseguradoras_result)), LOG_INFO)
		output_ui.append(MSG_DISP % (AseguradoraO.__name__, len(ori_aseguradoras_result)))
		for ori_aseguradora in ori_aseguradoras_result:
			#compobar si se migro anteriormente
			des_aseguradora =  self.get_row_des_from_ori_id(AseguradoraD, ori_aseguradora.id, True)

			if not des_aseguradora:
				aseguradora = AseguradoraD()
				aseguradora.nombre = ori_aseguradora.nombre
				aseguradora.activo = ori_aseguradora.activo
				aseguradora.data_origen_reg_id = ori_aseguradora.id
				aseguradora.data_origen_uid = self.uid_origen
				self.save_new_row_destino(aseguradora)
				self.update_data_destino_uid(ori_aseguradora)
				
				self.write_log(MSG_NUEVA % (AseguradoraO.__name__, str(ori_aseguradora.id)), LOG_INFO)
				migradas_nuevas += 1

			else:
				self.write_log(MSG_MIGRADA % (AseguradoraO.__name__, str(ori_aseguradora.id)), LOG_INFO)
				migradas_anteriormente += 1

		output_ui.append(MSG_TOTAL_NEW_ACT % (AseguradoraD.__name__, migradas_nuevas, migradas_anteriormente))
		self.write_log(MSG_TOTAL_NEW_ACT % (AseguradoraD.__name__, migradas_nuevas, migradas_anteriormente), LOG_INFO)
		self.write_log(MSG_END % (AseguradoraD.__name__), LOG_INFO)

		# ------
		# migrar prioridades 
		self.write_log(MSG_START % (PrioridadD.__name__), LOG_INFO)
		migradas_nuevas = 0
		migradas_anteriormente = 0
		ori_prioridades_result = self.ori_session.query(PrioridadO).all()
		self.write_log(MSG_DISP % (PrioridadO.__name__, len(ori_prioridades_result)), LOG_INFO)
		output_ui.append(MSG_DISP % (PrioridadO.__name__, len(ori_prioridades_result)))
		for ori_prioridad in ori_prioridades_result:
			#compobar si se migro anteriormente
			des_prioridad = self.get_row_des_from_ori_id(PrioridadD, ori_prioridad.id, True)
			if not des_prioridad:
				prioridad = PrioridadD()
				prioridad.nombre = ori_prioridad.nombre
				prioridad.codigo = ori_prioridad.codigo
				prioridad.nivel = ori_prioridad.nivel
				prioridad.data_origen_reg_id = ori_prioridad.id
				prioridad.data_origen_uid = self.uid_origen
				self.save_new_row_destino(prioridad)
				self.update_data_destino_uid(ori_prioridad)
				
				self.write_log(MSG_NUEVA % (PrioridadO.__name__, str(ori_prioridad.id)), LOG_INFO)
				migradas_nuevas += 1
			else:
				self.write_log(MSG_MIGRADA % (PrioridadO.__name__, str(ori_prioridad.id)), LOG_INFO)
				migradas_anteriormente += 1

		output_ui.append(MSG_TOTAL_NEW_ACT % (PrioridadD.__name__, migradas_nuevas, migradas_anteriormente))
		self.write_log(MSG_TOTAL_NEW_ACT % (PrioridadD.__name__, migradas_nuevas, migradas_anteriormente), LOG_INFO)
		self.write_log(MSG_END % (PrioridadD.__name__), LOG_INFO)

		# ------
		# migrar motivos de cancelacion
		self.write_log(MSG_START % (MotivoCancelacionD.__name__), LOG_INFO)
		migradas_nuevas = 0
		migradas_anteriormente = 0
		ori_motivos_cancelacion_result = self.ori_session.query(MotivoCancelacionO).all()
		self.write_log(MSG_DISP % (MotivoCancelacionO.__name__, len(ori_motivos_cancelacion_result)), LOG_INFO)
		output_ui.append(MSG_DISP % (MotivoCancelacionO.__name__, len(ori_motivos_cancelacion_result)))
		for ori_motivo_cancelacion in ori_motivos_cancelacion_result:
			#compobar si se migro anteriormente
			des_motivo_cancelacion = self.get_row_des_from_ori_id(MotivoCancelacionD, \
																  ori_motivo_cancelacion.id, 
																  True)
			if not des_motivo_cancelacion:
				motivo_cancelacion = MotivoCancelacionD()
				motivo_cancelacion.nombre = ori_motivo_cancelacion.nombre
				motivo_cancelacion.codigo = ori_motivo_cancelacion.codigo
				motivo_cancelacion.data_origen_reg_id = ori_motivo_cancelacion.id
				motivo_cancelacion.data_origen_uid = self.uid_origen
				
				self.save_new_row_destino(motivo_cancelacion)
				self.update_data_destino_uid(ori_motivo_cancelacion)
				
				self.write_log(MSG_NUEVA % (MotivoCancelacionO.__name__, str(ori_motivo_cancelacion.id)), LOG_INFO)
				migradas_nuevas += 1
			else:
				self.write_log(MSG_MIGRADA % (MotivoCancelacionO.__name__, str(ori_motivo_cancelacion.id)), LOG_INFO)
				migradas_anteriormente += 1

		output_ui.append(MSG_TOTAL_NEW_ACT % (MotivoCancelacionD.__name__, migradas_nuevas, migradas_anteriormente))
		self.write_log(MSG_TOTAL_NEW_ACT % (MotivoCancelacionD.__name__, migradas_nuevas, migradas_anteriormente), LOG_INFO)
		self.write_log(MSG_END % (MotivoCancelacionD.__name__), LOG_INFO)

		# ------
		# migrar campos
		self.write_log(MSG_START % (CampoD.__name__), LOG_INFO)
		migradas_nuevas = 0
		migradas_anteriormente = 0
		ori_campos_result = self.ori_session.query(CampoO).all()
		self.write_log(MSG_DISP % (CampoO.__name__, len(ori_campos_result)), LOG_INFO)
		output_ui.append(MSG_DISP % (CampoO.__name__, len(ori_campos_result)))
		for ori_campo in ori_campos_result:

			# comprobar si ya esta migrado.
			des_campo = self.get_row_des_from_ori_id(CampoD, ori_campo.id, True)

			# check si nombre de campo esta usado y itera hasta conseguir un nombre
			# de campo que no este usado.
			nombre_campo = ori_campo.nombre
			numero_campo = 0
			nombre_numero = None
			nombre_cambiado = False
			# la primera busqueda es con el nombre igual
			count_campos = self.des_session.query(CampoD).filter(CampoD.nombre == nombre_campo).count()
			while count_campos != 0:
				# las proximas busquedas son con el nombre + un numero.
				numero_campo += 1
				nombre_numero = nombre_campo + str(numero_campo) 
				count_campos = self.des_session.query(CampoD).filter(CampoD.nombre == nombre_numero).count()

			# si el campo tiene que ser un nombre con un numero lo asigna.
			# si es none es pq nunca entro al primer while y esta disponible el nombre del campo original
			if nombre_numero:
				nombre_campo = nombre_numero
				nombre_cambiado = True

			if not des_campo:
				campo = CampoD()
				campo.nombre = nombre_campo
				campo.tipo = ori_campo.tipo
				campo.titulo = ori_campo.titulo
				campo.columnas = ori_campo.columnas
				campo.tipo_control = ori_campo.tipo_control
				campo.valorPorDefecto = ori_campo.valorPorDefecto
				campo.solo_lectura = ori_campo.solo_lectura
				campo.script = ori_campo.script
				campo.obligatorio = ori_campo.obligatorio
				campo.ambito = ori_campo.ambito
				campo.data_origen_uid = self.uid_origen
				campo.data_origen_reg_id = ori_campo.id
				self.save_new_row_destino(campo)
				self.update_data_destino_uid(ori_campo)

				self.write_log(MSG_NUEVA % (CampoO.__name__, str(ori_campo.id)), LOG_INFO)
				migradas_nuevas += 1

				#mesnaje avisando que se cambio el nombre
				if nombre_cambiado:
					msg = "Se cambio el nombre del campo %s -> %s (ID origen: %s)" % (ori_campo.nombre, nombre_campo, str(ori_campo.id))
					output_ui.append(msg)
					self.write_log(msg, LOG_WARNING)
			else:
				self.write_log(MSG_MIGRADA % (CampoO.__name__, str(ori_campo.id)), LOG_INFO)
				migradas_anteriormente += 1

		output_ui.append(MSG_TOTAL_NEW_ACT % (CampoD.__name__, migradas_nuevas, migradas_anteriormente))
		self.write_log(MSG_TOTAL_NEW_ACT % (CampoD.__name__, migradas_nuevas, migradas_anteriormente), LOG_INFO)
		self.write_log(MSG_END % (CampoD.__name__), LOG_INFO)

		# ------
		# migrar textos predefinidos
		self.write_log(MSG_START % (TextoPredefinidoD.__name__), LOG_INFO)
		migradas_nuevas = 0
		migradas_anteriormente = 0
		ori_textos_predefinidos_result = self.ori_session.query(TextoPredefinidoO).all()
		self.write_log(MSG_DISP % (TextoPredefinidoO.__name__, len(ori_textos_predefinidos_result)), LOG_INFO)
		output_ui.append(MSG_DISP % (TextoPredefinidoO.__name__, len(ori_textos_predefinidos_result)))
		for ori_texto_predefinido in ori_textos_predefinidos_result:

			# comprobar si ya esta migrado.
			des_texto_predefinido =  self.get_row_des_from_ori_id(TextoPredefinidoD, \
																  ori_texto_predefinido.id, \
																  True)
			if not des_texto_predefinido:
				campo_id = None
				if ori_texto_predefinido.campo_id:
					campo_des = self.get_row_des_from_ori_id(CampoD, ori_texto_predefinido.campo_id)
					campo_id = campo_des.id

				# crear el texto predefindo
				texto_predefinido = TextoPredefinidoD()
				texto_predefinido.nombre = ori_texto_predefinido.nombre
				texto_predefinido.texto = ori_texto_predefinido.texto
				texto_predefinido.activo = ori_texto_predefinido.activo
				texto_predefinido.campo_id = campo_id
				texto_predefinido.data_origen_uid = self.uid_origen
				texto_predefinido.data_origen_reg_id = ori_texto_predefinido.id
				self.save_new_row_destino(texto_predefinido)
				self.update_data_destino_uid(ori_texto_predefinido)

				self.write_log(MSG_NUEVA % (TextoPredefinidoO.__name__, str(ori_texto_predefinido.id)), LOG_INFO)
				migradas_nuevas += 1
			else:
				self.write_log(MSG_MIGRADA % (TextoPredefinidoO.__name__, str(ori_texto_predefinido.id)), LOG_INFO)
				migradas_anteriormente += 1

		output_ui.append(MSG_TOTAL_NEW_ACT % (TextoPredefinidoD.__name__, migradas_nuevas, migradas_anteriormente))
		self.write_log(MSG_TOTAL_NEW_ACT % (TextoPredefinidoD.__name__, migradas_nuevas, migradas_anteriormente), LOG_INFO)
		self.write_log(MSG_END % (TextoPredefinidoD.__name__), LOG_INFO)

		# ------
		# migrar gruposcampos
		self.write_log(MSG_START % (GrupoCamposD.__name__), LOG_INFO)
		migradas_nuevas = 0
		migradas_anteriormente = 0
		ori_grupos_campos_result = self.ori_session.query(GrupoCamposO).all()
		self.write_log(MSG_DISP % (GrupoCamposO.__name__, len(ori_grupos_campos_result)), LOG_INFO)
		output_ui.append(MSG_DISP % (GrupoCamposO.__name__, len(ori_grupos_campos_result)))
		for ori_grupo_campo in ori_grupos_campos_result:

			# comprobar si ya esta migrado.
			des_grupo_campo = self.get_row_des_from_ori_id(GrupoCamposD, ori_grupo_campo.id, True)
			if not des_grupo_campo:
				grupo_campo = GrupoCamposD()
				grupo_campo.nombre = ori_grupo_campo.nombre
				grupo_campo.columnas = ori_grupo_campo.columnas
				grupo_campo.data_origen_uid = self.uid_origen
				grupo_campo.data_origen_reg_id = ori_grupo_campo.id
				self.save_new_row_destino(grupo_campo)
				self.update_data_destino_uid(ori_grupo_campo)

				self.write_log(MSG_NUEVA % (GrupoCamposO.__name__, str(ori_grupo_campo.id)), LOG_INFO)
				migradas_nuevas += 1
			else:
				self.write_log(MSG_MIGRADA % (GrupoCamposO.__name__, str(ori_grupo_campo.id)), LOG_INFO)
				migradas_anteriormente += 1

		output_ui.append(MSG_TOTAL_NEW_ACT % (GrupoCamposD.__name__, migradas_nuevas, migradas_anteriormente))
		self.write_log(MSG_TOTAL_NEW_ACT % (GrupoCamposD.__name__, migradas_nuevas, migradas_anteriormente), LOG_INFO)
		self.write_log(MSG_END % (GrupoCamposD.__name__), LOG_INFO)

		# ------
		# migrar elementos 
		self.write_log(MSG_START % (ElementoD.__name__), LOG_INFO)
		migradas_nuevas = 0
		migradas_anteriormente = 0
		ori_elementos_result = self.ori_session.query(ElementoO).all()
		self.write_log(MSG_DISP % (ElementoO.__name__, len(ori_elementos_result)), LOG_INFO)
		output_ui.append(MSG_DISP % (ElementoO.__name__, len(ori_elementos_result)))
		for ori_elemento in ori_elementos_result:
			# comprobar si ya esta migrado.
			des_elemento = self.get_row_des_from_ori_id(ElementoD, ori_elemento.id, True)
			if not des_elemento:

				# buscar el campo en destino
				campo_des = self.get_row_des_from_ori_id(CampoD, ori_elemento.campo_id)

				# crear el elemento
				elemento = ElementoD()
				elemento.campo_id = campo_des.id
				elemento.nombre = ori_elemento.nombre
				elemento.codigo = ori_elemento.codigo
				elemento.activo = ori_elemento.activo
				elemento.servicio_id = ori_elemento.servicio_id
				elemento.orden = ori_elemento.orden
				elemento.data_origen_uid = self.uid_origen
				elemento.data_origen_reg_id = ori_elemento.id

				self.save_new_row_destino(elemento)
				self.update_data_destino_uid(ori_elemento)

				self.write_log(MSG_NUEVA % (ElementoO.__name__, str(ori_elemento.id)), LOG_INFO)
				migradas_nuevas += 1
			else:
				self.write_log(MSG_MIGRADA % (ElementoO.__name__, str(ori_elemento.id)), LOG_INFO)
				migradas_anteriormente += 1

		output_ui.append(MSG_TOTAL_NEW_ACT % (ElementoD.__name__, migradas_nuevas, migradas_anteriormente))
		self.write_log(MSG_TOTAL_NEW_ACT % (ElementoD.__name__, migradas_nuevas, migradas_anteriormente), LOG_INFO)
		self.write_log(MSG_END % (ElementoD.__name__), LOG_INFO)

		# ------
		# migrar formularios
		self.write_log(MSG_START % (FormularioD.__name__), LOG_INFO)
		migradas_nuevas = 0
		migradas_anteriormente = 0
		ori_formularios_result = self.ori_session.query(FormularioO).all()
		self.write_log(MSG_DISP % (FormularioO.__name__, len(ori_formularios_result)), LOG_INFO)
		output_ui.append(MSG_DISP % (FormularioO.__name__, len(ori_formularios_result)))
		for ori_formulario in ori_formularios_result:

			# comprobar si ya esta migrado.
			des_formulario = self.get_row_des_from_ori_id(FormularioD, ori_formulario.id, True)
			if not des_formulario:
				formulario = FormularioD()
				formulario.titulo = ori_formulario.titulo
				formulario.data_origen_uid = self.uid_origen
				formulario.data_origen_reg_id = ori_formulario.id
				self.save_new_row_destino(formulario)
				self.update_data_destino_uid(ori_formulario)

				self.write_log(MSG_NUEVA % (FormularioO.__name__, str(ori_formulario.id)), LOG_INFO)
				migradas_nuevas += 1
			else:
				self.write_log(MSG_MIGRADA % (FormularioO.__name__, str(ori_formulario.id)), LOG_INFO)
				migradas_anteriormente += 1

		output_ui.append(MSG_TOTAL_NEW_ACT % (FormularioD.__name__, migradas_nuevas, migradas_anteriormente))
		self.write_log(MSG_TOTAL_NEW_ACT % (FormularioD.__name__, migradas_nuevas, migradas_anteriormente), LOG_INFO)
		self.write_log(MSG_END % (FormularioD.__name__), LOG_INFO)

		# ----- 
		# migrar valores por defecto
		self.write_log(MSG_START % (ValorPorDefectoD.__name__), LOG_INFO)
		migradas_nuevas = 0
		migradas_anteriormente = 0
		ori_valores_por_defecto_result = self.ori_session.query(ValorPorDefectoO).all()
		self.write_log(MSG_DISP % (ValorPorDefectoO.__name__, len(ori_valores_por_defecto_result)), LOG_INFO)
		output_ui.append(MSG_DISP % (ValorPorDefectoO.__name__, len(ori_valores_por_defecto_result)))
		for ori_valor_por_defecto in ori_valores_por_defecto_result:
			
			des_campo = self.get_row_des_from_ori_id(CampoD, ori_valor_por_defecto.campo_id)
			des_formulario = self.get_row_des_from_ori_id(FormularioD, ori_valor_por_defecto.formulario_id)

			# comprobar si ya esta migrado
			des_valor_por_defecto = self.des_session.query(ValorPorDefectoD) \
										.filter(and_(ValorPorDefectoD.campo_id==des_campo.id, \
													 ValorPorDefectoD.formulario_id ==des_formulario.id))
			if des_valor_por_defecto.count() == 0:
				valor_por_defecto =  ValorPorDefectoD()
				valor_por_defecto.campo_id = des_campo.id
				valor_por_defecto.formulario_id = des_formulario.id
				valor_por_defecto.valor = ori_valor_por_defecto.valor
				valor_por_defecto.data_origen_uid = self.uid_origen
				self.save_new_row_destino(valor_por_defecto)
				self.update_data_destino_uid(ori_valor_por_defecto)

				self.write_log("Nuevo valor por defecto en Destino [campo oigen id=%s, formulario origen id = %s]" \
							   	% (str(ori_valor_por_defecto.campo_id),str(ori_valor_por_defecto.formulario_id)) ,LOG_INFO)	
				migradas_nuevas += 1	
			else:
				self.write_log("Ya esta migrado el valor por defecto en Destino [campo oigen id=%s, formulario origen id = %s]" \
							   	% (str(ori_valor_por_defecto.campo_id),str(ori_valor_por_defecto.formulario_id)) ,LOG_INFO)
				migradas_anteriormente += 1
		
		output_ui.append(MSG_TOTAL_NEW_ACT % (ValorPorDefectoD.__name__, migradas_nuevas, migradas_anteriormente))
		self.write_log(MSG_TOTAL_NEW_ACT % (ValorPorDefectoD.__name__, migradas_nuevas, migradas_anteriormente), LOG_INFO)
		self.write_log(MSG_END % (ValorPorDefectoD.__name__), LOG_INFO)

		# ------
		# migrar rel_campos_formularios
		self.write_log(MSG_START % (Rel_Campos_FormulariosD.__name__), LOG_INFO)
		migradas_nuevas = 0
		migradas_anteriormente = 0
		ori_campos_formularios_result = self.ori_session.query(Rel_Campos_FormulariosO).all()
		self.write_log(MSG_DISP % (Rel_Campos_FormulariosO.__name__, len(ori_campos_formularios_result)), LOG_INFO)
		output_ui.append(MSG_DISP % (Rel_Campos_FormulariosO.__name__, len(ori_campos_formularios_result)))
		for ori_campo_formulario in ori_campos_formularios_result:
			
			des_campo = self.get_row_des_from_ori_id(CampoD, ori_campo_formulario.campo_id)

			des_campo_rel_id = None
			if ori_campo_formulario.campo_rel_id != None:
				des_campo_rel = self.get_row_des_from_ori_id(CampoD, ori_campo_formulario.campo_rel_id)
				des_campo_rel_id = des_campo_rel.id
				
			des_formulario = self.get_row_des_from_ori_id(FormularioD, ori_campo_formulario.formulario_id)
			des_grupo_campo = self.get_row_des_from_ori_id(GrupoCamposD, ori_campo_formulario.grupoCampos_id)
			# comprobar si ya esta migrado
			des_rel_campo_formulario = self.des_session.query(Rel_Campos_FormulariosD) \
										.filter(and_(Rel_Campos_FormulariosD.campo_id == des_campo.id, \
													 Rel_Campos_FormulariosD.formulario_id == des_formulario.id, \
													 Rel_Campos_FormulariosD.grupoCampos_id == des_grupo_campo.id))
			if des_rel_campo_formulario.count() == 0:
				rel_campo_formulario =  Rel_Campos_FormulariosD()
				rel_campo_formulario.campo_id = des_campo.id
				rel_campo_formulario.formulario_id = des_formulario.id
				rel_campo_formulario.grupoCampos_id = des_grupo_campo.id
				rel_campo_formulario.orden = ori_campo_formulario.orden
				rel_campo_formulario.ancho = ori_campo_formulario.ancho
				rel_campo_formulario.alto = ori_campo_formulario.alto
				rel_campo_formulario.posx = ori_campo_formulario.posx
				rel_campo_formulario.posy = ori_campo_formulario.posy
				rel_campo_formulario.campo_rel_id = des_campo_rel_id
				rel_campo_formulario.data_origen_uid = self.uid_origen
				self.save_new_row_destino(rel_campo_formulario)
				self.update_data_destino_uid(ori_campo_formulario)

				self.write_log("Nuevo rel_campo_formulario en destino " + \
							   " [campo oigen id=%s,  formulario origen id = %s, grupoCampo_id= %s ]" \
							   	% (str(ori_campo_formulario.campo_id), \
							   	   str(ori_campo_formulario.formulario_id), \
							   	   str(ori_campo_formulario.grupoCampos_id)) ,LOG_INFO)
				migradas_nuevas += 1
			else:
				self.write_log("Ya esta migrado el rel_campo_formulario en destino " + \
							   " [campo oigen id=%s,  formulario origen id = %s, grupoCampo_id= %s ]" \
							   	% (str(ori_campo_formulario.campo_id), \
							   	   str(ori_campo_formulario.formulario_id), \
							   	   str(ori_campo_formulario.grupoCampos_id)) ,LOG_INFO)
				migradas_anteriormente += 1
		
		output_ui.append(MSG_TOTAL_NEW_ACT % (Rel_Campos_FormulariosD.__name__, migradas_nuevas, migradas_anteriormente))
		self.write_log(MSG_TOTAL_NEW_ACT % (Rel_Campos_FormulariosD.__name__, migradas_nuevas, migradas_anteriormente), LOG_INFO)
		self.write_log(MSG_END % (Rel_Campos_FormulariosD.__name__), LOG_INFO)

		# ------
		# migrar rel_grupocampos_formularios
		self.write_log(MSG_START % (Rel_GruposCampos_FormulariosD.__name__), LOG_INFO)
		migradas_nuevas = 0
		migradas_anteriormente = 0
		ori_grupocampos_formularios_result = self.ori_session.query(Rel_GruposCampos_FormulariosO).all()
		self.write_log(MSG_DISP % (Rel_GruposCampos_FormulariosO.__name__, len(ori_grupocampos_formularios_result)), LOG_INFO)
		output_ui.append(MSG_DISP % (Rel_GruposCampos_FormulariosO.__name__, len(ori_grupocampos_formularios_result)))
		for ori_grupocampo_formulario in ori_grupocampos_formularios_result:
			
			des_formulario = self.get_row_des_from_ori_id(FormularioD, ori_grupocampo_formulario.formulario_id)
			des_grupo_campo = self.get_row_des_from_ori_id(GrupoCamposD, ori_grupocampo_formulario.grupoCampos_id)
			# comprobar si ya esta migrado
			des_rel_grupocampo_formulario = self.des_session.query(Rel_GruposCampos_FormulariosD) \
										.filter(and_(Rel_GruposCampos_FormulariosD.formulario_id == des_formulario.id, \
													 Rel_GruposCampos_FormulariosD.grupoCampos_id == des_grupo_campo.id))
			if des_rel_grupocampo_formulario.count() == 0:
				rel_grupocampo_formulario =  Rel_GruposCampos_FormulariosD()
				rel_grupocampo_formulario.formulario_id = des_formulario.id
				rel_grupocampo_formulario.grupoCampos_id = des_grupo_campo.id
				rel_grupocampo_formulario.orden = ori_grupocampo_formulario.orden
				rel_grupocampo_formulario.data_origen_uid = self.uid_origen
				self.save_new_row_destino(rel_grupocampo_formulario)
				self.update_data_destino_uid(ori_grupocampo_formulario)

				self.write_log("Nuevo rel_grupocampo_formulario en destino " + \
							   " [formulario origen id = %s, grupoCampo_id= %s ]" \
							   	% (str(ori_grupocampo_formulario.formulario_id), \
							   	   str(ori_grupocampo_formulario.grupoCampos_id)) ,LOG_INFO)
				migradas_nuevas += 1
			else:
				self.write_log("Ya esta migrado el rel_grupocampo_formulario en destino " + \
							   " [formulario origen id = %s, grupoCampo_id= %s ]" \
							   	% (str(ori_grupocampo_formulario.formulario_id), \
							   	   str(ori_grupocampo_formulario.grupoCampos_id)) ,LOG_INFO)
				migradas_anteriormente += 1
		
		output_ui.append(MSG_TOTAL_NEW_ANT % (Rel_GruposCampos_FormulariosD.__name__, migradas_nuevas, migradas_anteriormente))
		self.write_log(MSG_TOTAL_NEW_ANT % (Rel_GruposCampos_FormulariosD.__name__, migradas_nuevas, migradas_anteriormente), LOG_INFO)
		self.write_log(MSG_END % (Rel_GruposCampos_FormulariosD.__name__), LOG_INFO)

		# ------
		# migrar tipos de exploracion
		self.write_log(MSG_START % (TipoExploracionD.__name__), LOG_INFO)
		migradas_nuevas = 0
		migradas_anteriormente = 0
		ori_tipos_exploracion_result = self.ori_session.query(TipoExploracionO).all()
		self.write_log(MSG_DISP % (TipoExploracionO.__name__, len(ori_tipos_exploracion_result)), LOG_INFO)
		output_ui.append(MSG_DISP % (TipoExploracionO.__name__, len(ori_tipos_exploracion_result)))
		for ori_tipo_exploracion in ori_tipos_exploracion_result:

			# comprobar si ya esta migrado.
			des_tipo_exploracion = self.get_row_des_from_ori_id(TipoExploracionD, ori_tipo_exploracion.id, True)
			if not des_tipo_exploracion:
				tipo_exploracion = TipoExploracionD()
				tipo_exploracion.codigo = ori_tipo_exploracion.codigo
				tipo_exploracion.nombre = ori_tipo_exploracion.nombre
				tipo_exploracion.color = ori_tipo_exploracion.color
				tipo_exploracion.activo = False #ori_tipo_exploracion.activo
				tipo_exploracion.orden = ori_tipo_exploracion.orden
				tipo_exploracion.duracion = ori_tipo_exploracion.duracion
				tipo_exploracion.data_origen_uid = self.uid_origen
				tipo_exploracion.data_origen_reg_id = ori_tipo_exploracion.id
				self.save_new_row_destino(tipo_exploracion)
				self.update_data_destino_uid(ori_tipo_exploracion)

				self.write_log(MSG_NUEVA % (TipoExploracionD.__name__, str(ori_tipo_exploracion.id)), LOG_INFO)
				migradas_nuevas += 1
			else:
				self.write_log(MSG_MIGRADA % (TipoExploracionD.__name__, str(ori_tipo_exploracion.id)), LOG_INFO)
				migradas_anteriormente += 1

		output_ui.append(MSG_TOTAL_NEW_ACT % (TipoExploracionD.__name__, migradas_nuevas, migradas_anteriormente))
		self.write_log(MSG_TOTAL_NEW_ACT % (TipoExploracionD.__name__, migradas_nuevas, migradas_anteriormente), LOG_INFO)
		self.write_log(MSG_END % (TipoExploracionD.__name__), LOG_INFO)

		# -------
		# migrar rel formularios tipos de exploracion
		self.write_log(MSG_START % (Rel_Formularios_TiposExploracionD.__name__), LOG_INFO)
		migradas_nuevas = 0
		migradas_anteriormente = 0
		ori_rel_form_tipoexpl_result = self.ori_session.query(Rel_Formularios_TiposExploracionO).all()
		self.write_log(MSG_DISP % (Rel_Formularios_TiposExploracionO.__name__, len(ori_rel_form_tipoexpl_result)), LOG_INFO)
		output_ui.append(MSG_DISP % (Rel_Formularios_TiposExploracionO.__name__, len(ori_rel_form_tipoexpl_result)))
		for ori_rel_form_tipoexpl in ori_rel_form_tipoexpl_result:

			des_tipo_exploracion = self.get_row_des_from_ori_id(TipoExploracionD, \
																ori_rel_form_tipoexpl.tipoExploracion_id)

			des_formulario = self.get_row_des_from_ori_id(FormularioD, \
														  ori_rel_form_tipoexpl.formulario_id)

			# comprobar si ya esta migrado
			des_rel_form_tipoexpl = self.des_session.query(Rel_Formularios_TiposExploracionD) \
										.filter(and_(Rel_Formularios_TiposExploracionD.formulario_id == des_formulario.id, \
													 Rel_Formularios_TiposExploracionD.tipoExploracion_id ==des_tipo_exploracion.id))
			if des_rel_form_tipoexpl.count() == 0:
				rel_form_tipoexpl = Rel_Formularios_TiposExploracionD()
				rel_form_tipoexpl.tipoExploracion_id = des_tipo_exploracion.id
				rel_form_tipoexpl.formulario_id = des_formulario.id
				rel_form_tipoexpl.orden = ori_rel_form_tipoexpl.orden
				rel_form_tipoexpl.predefinido = ori_rel_form_tipoexpl.predefinido
				rel_form_tipoexpl.data_origen_uid = self.uid_origen
				self.save_new_row_destino(rel_form_tipoexpl)
				self.update_data_destino_uid(ori_rel_form_tipoexpl)

				self.write_log("Nuevo rel_formulario_tipoexpl en destino " + \
							   " [formulario oigen id=%s,  tipo_exporacion origen id = %s ]" \
							   	% (str(ori_rel_form_tipoexpl.formulario_id), \
							   	   str(ori_rel_form_tipoexpl.tipoExploracion_id)), \
							   	   LOG_INFO)
				migradas_nuevas += 1
			else:
				self.write_log("Ya esta migrado la rel_formulario_tipoexpl en destino " + \
							   " [formulario oigen id=%s,  tipo_exporacion origen id = %s ]" \
							   	% (str(ori_rel_form_tipoexpl.formulario_id), \
							   	   str(ori_rel_form_tipoexpl.tipoExploracion_id)), \
							   	   LOG_INFO)
				migradas_anteriormente += 1

		output_ui.append(MSG_TOTAL_NEW_ANT % (Rel_Formularios_TiposExploracionD.__name__, migradas_nuevas, migradas_anteriormente))
		self.write_log(MSG_TOTAL_NEW_ANT % (Rel_Formularios_TiposExploracionD.__name__, migradas_nuevas, migradas_anteriormente), LOG_INFO)
		self.write_log(MSG_END % (Rel_Formularios_TiposExploracionD.__name__), LOG_INFO)

		# -------
		# migrar rel servicios tipos de exploracion
		self.write_log(MSG_START % (Rel_Servicios_TiposExploracionD.__name__), LOG_INFO)
		migradas_nuevas = 0
		migradas_anteriormente = 0
 		ori_rel_serv_tipoexpl_result = self.ori_session.query(Rel_Servicios_TiposExploracionO).all()
 		self.write_log(MSG_DISP % (Rel_Servicios_TiposExploracionO.__name__, len(ori_rel_serv_tipoexpl_result)), LOG_INFO)
		output_ui.append(MSG_DISP % (Rel_Servicios_TiposExploracionO.__name__, len(ori_rel_serv_tipoexpl_result)))
		for ori_rel_serv_tipoexpl in ori_rel_serv_tipoexpl_result:

			des_tipo_exploracion = self.get_row_des_from_ori_id(TipoExploracionD, \
																ori_rel_serv_tipoexpl.tipoExploracion_id)

			des_servicio = self.get_row_des_from_ori_id(ServicioD, \
														  ori_rel_serv_tipoexpl.servicio_id)

			# comprobar si ya esta migrado
			des_rel_serv_tipoexpl = self.des_session.query(Rel_Servicios_TiposExploracionD) \
										.filter(and_(Rel_Servicios_TiposExploracionD.servicio_id == des_servicio.id, \
													 Rel_Servicios_TiposExploracionD.tipoExploracion_id ==des_tipo_exploracion.id))
			if des_rel_serv_tipoexpl.count() == 0:
				rel_serv_tipoexpl = Rel_Servicios_TiposExploracionD()
				rel_serv_tipoexpl.tipoExploracion_id = des_tipo_exploracion.id
				rel_serv_tipoexpl.servicio_id = des_servicio.id
				rel_serv_tipoexpl.data_origen_uid = self.uid_origen
				self.save_new_row_destino(rel_serv_tipoexpl)
				self.update_data_destino_uid(ori_rel_serv_tipoexpl)

				self.write_log("Nuevo rel_servicio_tipoexpl en destino " + \
							   " [servicio oigen id=%s,  tipo_exporacion origen id = %s ]" \
							   	% (str(ori_rel_serv_tipoexpl.servicio_id), \
							   	   str(ori_rel_serv_tipoexpl.tipoExploracion_id)), \
							   	   LOG_INFO)
				migradas_nuevas += 1
			else:
				self.write_log("Ya esta migrado la rel_servicio_tipoexpl en destino " + \
							   " [servicio oigen id=%s,  tipo_exporacion origen id = %s ]" \
							   	% (str(ori_rel_serv_tipoexpl.servicio_id), \
							   	   str(ori_rel_serv_tipoexpl.tipoExploracion_id)), \
							   	   LOG_INFO)
				migradas_anteriormente += 1

		output_ui.append(MSG_TOTAL_NEW_ANT % (Rel_Servicios_TiposExploracionD.__name__, migradas_nuevas, migradas_anteriormente))
		self.write_log(MSG_TOTAL_NEW_ANT % (Rel_Servicios_TiposExploracionD.__name__, migradas_nuevas, migradas_anteriormente), LOG_INFO)
		self.write_log(MSG_END % (Rel_Servicios_TiposExploracionD.__name__), LOG_INFO)

		# ------
		# migrar poblaciones
		self.write_log(MSG_START % (PoblacionD.__name__), LOG_INFO)
		migradas_nuevas = 0
		migradas_anteriormente = 0
		existentes = 0
		ori_poblaciones_result = self.ori_session.query(PoblacionO).all()
		self.write_log(MSG_DISP % (PoblacionO.__name__, len(ori_poblaciones_result)), LOG_INFO)
		output_ui.append(MSG_DISP % (PoblacionO.__name__, len(ori_poblaciones_result)))
		for ori_poblacion in ori_poblaciones_result:

			#buscar la poblacion pero por el nombre en destino
			des_poblacion = self.des_session.query(PoblacionD) \
								.filter(PoblacionD.nombre == ori_poblacion.nombre)
			if des_poblacion.count() > 0:
				des_poblacion = des_poblacion.one()
				if des_poblacion.data_origen_uid == self.uid_origen and \
				   des_poblacion.data_origen_reg_id == ori_poblacion.id:

					#ya esta migrado.
					self.write_log(MSG_MIGRADA % (PoblacionO.__name__, str(ori_poblacion.id)), LOG_INFO)
					migradas_anteriormente += 1
				else:
					# no esta migrado pero hay una poblacion con el mismo nombre.
					# actualizo el data origen solamente
					des_poblacion.data_origen_uid = self.uid_origen
					des_poblacion.data_origen_reg_id = ori_poblacion.id
					self.des_session.update(des_poblacion)
					self.update_data_destino_uid(ori_poblacion)

					self.write_log("Se migro la poblacion en una existente en destino " + \
							   	  " [origen id=%s]" \
							   	  % (str(ori_poblacion.id)), LOG_INFO)
					existentes += 1
			else:
				# no existe en destino, se crea una nueva.
				poblacion = PoblacionD()
				poblacion.codigo = ori_poblacion.codigo
				poblacion.nombre = ori_poblacion.nombre
				poblacion.data_origen_uid = self.uid_origen
				poblacion.data_origen_reg_id = ori_poblacion.id
				self.save_new_row_destino(poblacion)
				self.update_data_destino_uid(ori_poblacion)

				self.write_log(MSG_NUEVA % (PoblacionO.__name__, str(ori_poblacion.id)), LOG_INFO)
				migradas_nuevas += 1

		output_ui.append(MSG_TOTAL_NEW_ANT_EXI % (PoblacionD.__name__, migradas_nuevas, migradas_anteriormente,existentes))
		self.write_log(MSG_TOTAL_NEW_ANT_EXI % (PoblacionD.__name__, migradas_nuevas, migradas_anteriormente,existentes), LOG_INFO)
		self.write_log(MSG_END % (PoblacionD.__name__), LOG_INFO)

		# ------
		# migrar provincias
		self.write_log(MSG_START % (ProvinciaD.__name__), LOG_INFO)
		migradas_nuevas = 0
		migradas_anteriormente = 0
		existentes = 0
		ori_provincias_result = self.ori_session.query(ProvinciaO).all()
		self.write_log(MSG_DISP % (ProvinciaO.__name__, len(ori_provincias_result)), LOG_INFO)
		output_ui.append(MSG_DISP % (ProvinciaO.__name__, len(ori_provincias_result)))
		for ori_provincia in ori_provincias_result:

			#buscar la provincia pero por el nombre en destino
			des_provincia = self.des_session.query(ProvinciaD) \
								.filter(ProvinciaD.nombre == ori_provincia.nombre)
			if des_provincia.count() > 0:
				des_provincia = des_provincia.one()
				if des_provincia.data_origen_uid == self.uid_origen and \
				   des_provincia.data_origen_reg_id == ori_provincia.id:

					#ya esta migrado.
					self.write_log(MSG_MIGRADA % (ProvinciaO.__name__, str(ori_provincia.id)), LOG_INFO)
					migradas_anteriormente += 1
				else:
					# no esta migrado pero hay una provincia con el mismo nombre.
					# actualizo el data origen solamente
					des_provincia.data_origen_uid = self.uid_origen
					des_provincia.data_origen_reg_id = ori_provincia.id
					self.des_session.update(des_provincia)
					self.update_data_destino_uid(ori_provincia)

					self.write_log(MSG_NUEVA % (ProvinciaO.__name__, str(ori_provincia.id)), LOG_INFO)
					existentes += 1
			else:
				# no existe en destino, se crea una nueva.
				provincia = ProvinciaD()
				provincia.codigo = ori_provincia.codigo
				provincia.nombre = ori_provincia.nombre
				provincia.data_origen_uid = self.uid_origen
				provincia.data_origen_reg_id = ori_provincia.id
				self.save_new_row_destino(provincia)
				self.update_data_destino_uid(ori_provincia)
				self.write_log("Nueva provincia en destino " + \
							   	  " [origen id=%s]" \
							   	  % (str(ori_provincia.id)), LOG_INFO)
				migradas_nuevas += 1

		output_ui.append(MSG_TOTAL_NEW_ANT_EXI % (ProvinciaD.__name__, migradas_nuevas, migradas_anteriormente,existentes))
		self.write_log(MSG_TOTAL_NEW_ANT_EXI % (ProvinciaD.__name__, migradas_nuevas, migradas_anteriormente,existentes), LOG_INFO)
		self.write_log(MSG_END % (ProvinciaD.__name__), LOG_INFO)

		self.ori_session.close()
		self.des_session.close()

		return output_ui

	def obtener_crear_paciente(self, ori_paciente_id):
		paciente = None
		# busco si el objeto paciente en origen.
		ori_paciente = self.ori_session.query(PacienteO).filter(PacienteO.id == ori_paciente_id).first()

		# busco si existe en destino por su id unico
		des_paciente = get_by_idunico_generic(self.des_session, PacienteD, ori_paciente.idunico, True)
		if not des_paciente or ori_paciente.deshabilitado:
			# si es deshabilitado, no importa que exista el mismo idunico, lo crea igual.
			# si no es deshabilidado, entonces para crear no tiene que existir el paciente en destino.

			str_desh = ""
			if ori_paciente.deshabilitado:
				str_desh = "[Deshabilitado]"

			# si el paciente no esta en destino se migra poc completo	
			paciente = self.crear_obj_paciente(ori_paciente)
			paciente.data_origen_uid = self.uid_origen
			paciente.data_origen_reg_id = ori_paciente.id
			self.save_new_row_destino(paciente)
			self.update_data_destino_uid(ori_paciente)
			self.pacientes_dict.append({'origen_id':ori_paciente.id, 'destino_id':paciente.id})

			self.write_log(MSG_NUEVA % (PacienteO.__name__+str_desh, str(ori_paciente.id)), LOG_INFO)
		else:
			# si el paciente si esta en destino entonces
			if xstr(des_paciente.nombre).lower() == xstr(ori_paciente.nombre).lower() and \
			   xstr(des_paciente.apellido1).lower() == xstr(ori_paciente.apellido1).lower() and \
			   xstr(des_paciente.apellido2).lower() == xstr(ori_paciente.apellido2).lower():

				# paciente encontrado en destino con el mismo id unico y mismos nombres.
				self.write_log("Paciente existe en destino " + \
						   	  "[origen id=%s]" \
						   	  % (str(ori_paciente.id)), LOG_INFO)
				paciente = des_paciente
				self.pacientes_dict.append({'origen_id':ori_paciente.id, 'destino_id':des_paciente.id})

			else:
				# no coinciden nombre y apellido, no se hace nada, solo un warning
				msg = "Paciente con mismo idunico en destino pero diferentes nombres" + \
						   	  " [origen id=%s]" \
						   	  % (str(ori_paciente.id))
				self.write_log(msg, LOG_WARNING)
				
		if paciente:
			# si el paciente existe entonces agrego la relacion de centros pacientes.
			ori_rel_pacientes_centros_result = self.ori_session.query(Rel_Pacientes_CentrosO) \
												   .filter(Rel_Pacientes_CentrosO.paciente_id == ori_paciente_id) \
												   .all()

			for ori_rel_paciente_centro in ori_rel_pacientes_centros_result:
			
			
				centro_des = self.get_row_des_from_ori_id(CentroD, ori_rel_paciente_centro.centro_id)

				des_rel_paciente_centro = self.des_session.query(Rel_Pacientes_CentrosD) \
											  .filter(and_(Rel_Pacientes_CentrosD.paciente_id == paciente.id,\
												 		   Rel_Pacientes_CentrosD.centro_id == centro_des.id))

				if des_rel_paciente_centro.count() == 0:
					# si no existe, crea la relacion.
					rel_paciente_centro = Rel_Pacientes_CentrosD()
					rel_paciente_centro.paciente_id = paciente.id
					rel_paciente_centro.centro_id = centro_des.id
					rel_paciente_centro.nhc = ori_rel_paciente_centro.nhc
					rel_paciente_centro.data_origen_uid = self.uid_origen
					self.save_new_row_destino(rel_paciente_centro)
					self.update_data_destino_uid(ori_rel_paciente_centro)
					self.write_log("Se creo la relacion de paciente-centro en destino " + \
							   	  " [paciente origen id=%s, centro origen id=%s]" \
							   	  % (str(ori_rel_paciente_centro.paciente_id),str(ori_rel_paciente_centro.centro_id)), LOG_INFO)
					
				else:
					des_rel_paciente_centro = des_rel_paciente_centro.one()
					if des_rel_paciente_centro.nhc != ori_rel_paciente_centro.nhc:
						# esto es un error pq ya existe la relacion pero es distinta en origen y destino.
						msg = "Error al crear Rel_Pacientes_Centros en destino (NHC es distinto en origen y destino para el mismo centro) " + \
							   	  " [paciente origen id=%s, centro origen id=%s]" \
							   	  % (str(ori_rel_paciente_centro.paciente_id),str(ori_rel_paciente_centro.centro_id))
						self.write_log(msg, LOG_ERROR)
					else:
						# ya esta migrado, no hago nada.
						self.write_log("Ya existe la relacion de paciente-centro en destino " + \
							   	  " [paciente origen id=%s, centro origen id=%s]" \
							   	  % (str(ori_rel_paciente_centro.paciente_id),str(ori_rel_paciente_centro.centro_id)), LOG_INFO)
		return paciente

	def preparar_datos_migrar_datos(self):
		rangos = {}
		rangos["max_exploracion"] = self.des_session.query(ExploracionD).max(ExploracionD.numero)
		rangos["min_exploracion"] = self.des_session.query(ExploracionD).min(ExploracionD.numero)
		rangos["max_informe"] = self.des_session.query(InformeD).max(InformeD.numero)
		rangos["min_informe"] = self.des_session.query(InformeD).min(InformeD.numero)
		return rangos

	def migrar_exploraciones(self, request):
		output = []
		self.write_log("Exploraciones: Comienzo de la migracion", LOG_INFO)
		
		# migrar exploraciones
		if 'prefijo_exploracion' in request.params:
			self.prefijo_exploracion = int(request.params.get("prefijo_exploracion"))

		'''
		filtrar_fecha = False
		if 'fecha_ini' in request.params:
			self.fecha_ini = datetime.strptime(request.params.get("fecha_ini"))
			self.fecha_fin = datetime.strptime(request.params.get("fecha_fin"))
			filtrar_fecha = True
		'''

		migradas_nuevas = 0
		migradas_anteriormente = 0

		ori_exploraciones = self.ori_session.query(ExploracionO)
		'''
		if filtrar_fecha:
			ori_exploraciones = ori_exploraciones.filter(ExploracionO.fecha >= self.fecha_ini)
			ori_exploraciones = ori_exploraciones.filter(ExploracionO.fecha <= self.fecha_fin)
		'''
		ori_exploraciones = ori_exploraciones.all()

		output.append("Exploraciones: Disponibles para migrar(%s)" % (str(len(ori_exploraciones))))
		for ori_exploracion in ori_exploraciones:
			
			#checkear si esta ya migrada.
			des_exploracion = self.get_dest_id(self.exploraciones_hash, ori_exploracion.id)
			if not des_exploracion:
				# no esta migrada entonces la creo:

				# si el paciente tiene conflicto entonces devuevle error y no sigue porque
				# sino se hace muy complejo el codigo para controlar que exploraciones no migrar y cuales si

				# primero busca si ya se creo en esta migracion que se esta ejecutando para 
				# evitar tener que hacer una nueva consulta.
				paciente_id = None
				paciente_dict = self.get_dest_id(self.pacientes_dict, ori_exploracion.paciente_id)
				if paciente_dict:
					paciente_id = paciente_dict
				else:
					# si no se creo en esta migracion que se esta ejecutando se intenta crearlo o obtenerlo
					des_paciente = self.obtener_crear_paciente(ori_exploracion.paciente_id)
					if not des_paciente:
						raise ConflictoPacienteError("Paciente ID Origen: %s existe en destino pero tiene diferente nombre" % (str(ori_exploracion.paciente_id)))
					paciente_id = des_paciente.id

				#buscar las foreign key mapeadas en destino not null
				des_tipo_expl = self.get_dest_id(self.tipos_exploraciones_hash, ori_exploracion.tipoExploracion_id)
				if not des_tipo_expl:
					raise_error_one_line("No se encontro el tipo de exploracion origen: %s" % (str(ori_exploracion.tipoExploracion_id)))
				
				# obtiene el medico id
				medico_id = self.get_dest_id(self.medicos_hash, ori_exploracion.medico_id)
				if not medico_id:
					# puede ser que sea uno de los excluidos o que no se haya migrado correctamente.
					ori_medico = self.ori_session.query(MedicoO).filter(MedicoO.id == ori_exploracion.medico_id).one()
					if ori_medico.username in USERNAME_EXCLUDES:
						des_user = self.des_session.query(UserD).filter(UserD.username == ori_medico.username)
						if des_user.count() == 0:
							raise Exception("No se puede migrar la exploracion porque el medico no existe en destino (%s)" % (ori_medico.username))
						else:
							des_user = des_user.one()
							des_medico = self.des_session.query(MedicoD).filter(MedicoD.username == des_user.username).one()
							medico_id = des_medico.id
					else:
						raise Exception("No se puede migrar la exploracion porque el medico no existe en destino (%s)" % (ori_medico.username))
				
				
				# pueden ser null
				centro_id = None
				if ori_exploracion.centro_id:	
					centro_id = self.get_dest_id(self.centros_hash, ori_exploracion.centro_id)

				motivo_id = None
				if ori_exploracion.motivo_id:
					motivo_id = self.get_dest_id(self.motivos_hash, ori_exploracion.motivo_id)

				servicio_id = None
				if ori_exploracion.servicio_id:
					servicio_id = self.get_dest_id(self.servicios_hash, ori_exploracion.servicio_id)

				aseguradora_id = None
				if ori_exploracion.aseguradora_id:
					aseguradora_id = self.get_dest_id(self.aseguradora_hash, ori_exploracion.aseguradora_id)

				# crear la exploracion
				exploracion = ExploracionD()
				exploracion.centro_id = centro_id
				exploracion.tipoExploracion_id = des_tipo_expl
				exploracion.numero = self.prefijo_exploracion + ori_exploracion.numero
				exploracion.estado = ori_exploracion.estado
				exploracion.medico_id = medico_id
				exploracion.paciente_id = paciente_id
				exploracion.fecha = ori_exploracion.fecha
				exploracion.hora = ori_exploracion.hora
				exploracion.StudyInstanceUID = ori_exploracion.StudyInstanceUID
				exploracion.SeriesInstanceUID = ori_exploracion.SeriesInstanceUID
				exploracion.motivo_id = motivo_id
				exploracion.edad_paciente = ori_exploracion.edad_paciente
				exploracion.servicio_id = servicio_id
				exploracion.aseguradora_id = aseguradora_id
				borrado = ori_exploracion.borrado
				if borrado == None:
					borrado = False
				exploracion.borrado = borrado
				exploracion.borrado_motivo = ori_exploracion.borrado_motivo
				exploracion.data_origen_uid = self.uid_origen
				exploracion.data_origen_reg_id = ori_exploracion.id
				self.save_new_row_destino(exploracion)
				self.update_data_destino_uid(ori_exploracion)
				#actualizar la tabla hash opara despues usarla en exploraciones dicom y en rel_form_expl
				self.exploraciones_hash.append({"origen_id": exploracion.data_origen_reg_id, "destino_id": exploracion.id})

				self.write_log(MSG_NUEVA % (ExploracionO.__name__, str(ori_exploracion.id)), LOG_INFO)
				migradas_nuevas += 1
			else:
				self.write_log(MSG_MIGRADA % (ExploracionO.__name__, str(ori_exploracion.id)), LOG_INFO)
				migradas_anteriormente +=1

		self.del_hash_tables()

		output.append("Exploraciones: Nuevas(%d) / Migradas anteriomente(%d)" \
						% (migradas_nuevas, migradas_anteriormente))
		self.write_log("Exploraciones: Fin de la migracion", LOG_INFO)
		return output

	def migrar_exploraciones_dicom(self):
		output = []
		self.write_log(MSG_START % (Exploracion_dicomD.__name__), LOG_INFO)

		self.def_exploraciones_dicom_d = sa.Table('Exploraciones_dicom', self.db_destino['metadata'], autoload=True)
		self.def_exploraciones_dicom_o = sa.Table('Exploraciones_dicom', self.db_origen['metadata'], autoload=True)

		# Definicion del insert y update masivo
		i = self.def_exploraciones_dicom_d.insert()
		u = self.def_exploraciones_dicom_o.update() \
				.where(self.def_exploraciones_dicom_o.c.exploracion_id == bindparam("_exploracion_id")) \
				.values({"data_destino_uid": bindparam('data_destino_uid')})

		# reset los data_destino_uid de origen si ya se migraron. Se hace todo de nuevo.
		self.def_exploraciones_dicom_o.update() \
								.where(self.def_exploraciones_dicom_o.c.data_destino_uid == self.uid_destino) \
								.values({"data_destino_uid": None}) \
								.execute()
		self.write_log(MSG_ACT_NULL % (Exploracion_dicomO.__name__, self.uid_destino), LOG_INFO)
		
		# delete las relaciones creadas en destino con el data origen uid de esta migracion
		self.def_exploraciones_dicom_d.delete() \
								.where(self.def_exploraciones_dicom_d.c.data_origen_uid == self.uid_origen) \
								.execute()
		self.write_log(MSG_DEL % (Exploracion_dicomO.__name__, self.uid_origen), LOG_INFO)

		migradas_nuevas = 0
		ori_expl_dicom_result = self.ori_session.query(Exploracion_dicomO).all()
		output.append(MSG_DISP % (Exploracion_dicomO, len(ori_expl_dicom_result)))
		self.write_log(MSG_DISP % (Exploracion_dicomO, len(ori_expl_dicom_result)), LOG_INFO)

		rows_to_add = []
		rows_to_update = []
		for ori_expl_dicom in ori_expl_dicom_result:
			#obtener id de exploracion destino
			des_exploracion = self.get_dest_id(self.exploraciones_hash, ori_expl_dicom.exploracion_id)
			if not des_exploracion:
				raise_error_one_line(MSG_NOT_FOUND % ("Exploracion", ori_expl_dicom.exploracion_id))

			rows_to_add.append({"exploracion_id": des_exploracion, \
								"stored": ori_expl_dicom.stored, \
								"accessionNumber": ori_expl_dicom.accessionNumber, \
								"studyInstanceUID": ori_expl_dicom.studyInstanceUID, \
								"studyID": ori_expl_dicom.studyID, \
								"studyDate": ori_expl_dicom.studyDate, \
								"studyTime": ori_expl_dicom.studyTime, \
								"stationName": ori_expl_dicom.stationName, \
								"patientName": ori_expl_dicom.patientName, \
								"patientBirthDate": ori_expl_dicom.patientBirthDate, \
								"patientSex": ori_expl_dicom.patientSex, \
								"studyDescription": ori_expl_dicom.studyDescription, \
								"data_origen_reg_id": ori_expl_dicom.exploracion_id, \
								"data_origen_uid": self.uid_origen })
			rows_to_update.append({"data_destino_uid": self.uid_destino, \
								   "_exploracion_id": ori_expl_dicom.exploracion_id})
			
			migradas_nuevas += 1
			# cada vez que el dict llega a 500 se insertan y actualizan
			if migradas_nuevas % 500 == 0:
				i.execute(rows_to_add)
				rows_to_add = []
				u.execute(rows_to_update)
				rows_to_update = []
				self.write_log(MSG_STATUS % (Exploracion_dicomD, migradas_nuevas), LOG_INFO)

		# se insertan y actualizan las restantes que no dan resto = 0 en la cuenta % 500
		if len(rows_to_add) > 0:
			i.execute(rows_to_add)
			rows_to_add = []
			u.execute(rows_to_update)
			rows_to_update = []
			self.write_log(MSG_STATUS % (Exploracion_dicomD, migradas_nuevas), LOG_INFO)

		# Borrar por que no se necesitan mas
		self.del_hash_tables()

		output.append(MSG_TOTAL_NEW % (Exploracion_dicomD.__name__, migradas_nuevas))
		self.write_log(MSG_TOTAL_NEW % (Exploracion_dicomD.__name__, migradas_nuevas), LOG_INFO)
		self.write_log(MSG_END % (Exploracion_dicomD.__name__), LOG_INFO)
		return output

	def migrar_rel_formularios_exploraciones(self):
		output = []
		self.write_log(MSG_START % (Rel_Formularios_ExploracionesD.__name__), LOG_INFO)
		
		self.def_rel_form_expl_d = sa.Table('rel_Formularios_Exploraciones', self.db_destino['metadata'], autoload=True)
		self.def_rel_form_expl_o = sa.Table('rel_Formularios_Exploraciones', self.db_origen['metadata'], autoload=True)
		
		# Definicion del insert y update masivo
		i = self.def_rel_form_expl_d.insert()
		u = self.def_rel_form_expl_o.update() \
				.where(and_(self.def_rel_form_expl_o.c.exploracion_id == bindparam("_exploracion_id"), \
							self.def_rel_form_expl_o.c.formulario_id == bindparam("_formulario_id"))) \
				.values({"data_destino_uid": bindparam('data_destino_uid')})

		# reset los data_destino_uid de origen si ya se migraron. Se hace todo de nuevo.
		self.def_rel_form_expl_o.update() \
								.where(self.def_rel_form_expl_o.c.data_destino_uid == self.uid_destino) \
								.values({"data_destino_uid": None}) \
								.execute()
		self.write_log(MSG_ACT_NULL % (Rel_Formularios_ExploracionesO.__name__, self.uid_destino), LOG_INFO)

		# delete las relaciones creadas en destino con el data origen uid de esta migracion
		self.def_rel_form_expl_d.delete() \
								.where(self.def_rel_form_expl_d.c.data_origen_uid == self.uid_origen) \
								.execute()
		self.write_log(MSG_DEL % (Rel_Formularios_ExploracionesD.__name__, self.uid_destino), LOG_INFO)

		# recorrer las no migradas y agregarlas
		migradas_nuevas = 0
		ori_rel_form_expl_result = self.ori_session.query(Rel_Formularios_ExploracionesO).all()
		output.append(MSG_DISP % (Rel_Formularios_ExploracionesO, len(ori_rel_form_expl_result)))
		self.write_log(MSG_DISP % (Rel_Formularios_ExploracionesO, len(ori_rel_form_expl_result)), LOG_INFO)

		# insertar en destino y actualizar origen
		rows_to_add = []
		rows_to_update = []
		for ori_rel_form_expl in ori_rel_form_expl_result:
			
			rows_to_add.append({"exploracion_id": self.get_dest_id(self.exploraciones_hash, ori_rel_form_expl.exploracion_id), \
								"formulario_id": self.get_dest_id(self.formularios_hash, ori_rel_form_expl.formulario_id), \
								"data_origen_uid": self.uid_origen})
			rows_to_update.append({"data_destino_uid": self.uid_destino, \
								   "_formulario_id": ori_rel_form_expl.formulario_id, \
								   "_exploracion_id": ori_rel_form_expl.exploracion_id })

			migradas_nuevas += 1

			# cada vez que el dict llega a 500 se insertan y actualizan
			if migradas_nuevas % 500 == 0:
				i.execute(rows_to_add)
				rows_to_add = []
				u.execute(rows_to_update)
				rows_to_update = []
				self.write_log(MSG_STATUS % (Rel_Formularios_ExploracionesD, migradas_nuevas), LOG_INFO)

		# se insertan y actualizan las restantes que no dan resto = 0 en la cuenta % 500
		if len(rows_to_add) > 0:
			i.execute(rows_to_add)
			rows_to_add = []
			u.execute(rows_to_update)
			rows_to_update = []
			self.write_log(MSG_STATUS % (Rel_Formularios_ExploracionesD, migradas_nuevas), LOG_INFO)

		self.del_hash_tables()

		output.append(MSG_TOTAL_NEW % (Rel_Formularios_ExploracionesD.__name__, migradas_nuevas))
		self.write_log(MSG_TOTAL_NEW % (Rel_Formularios_ExploracionesD.__name__, migradas_nuevas), LOG_INFO)
		self.write_log(MSG_END % (Rel_Formularios_ExploracionesD.__name__), LOG_INFO)
		return output

	def migrar_valores_texto(self):
		# migrar valores texto
		output = []
		self.write_log(MSG_START % (ValorTextoD.__name__), LOG_INFO)
		
		self.def_valores_texto_d = sa.Table('ValoresTexto', self.db_destino['metadata'], autoload=True)
		self.def_valores_texto_o = sa.Table('ValoresTexto', self.db_origen['metadata'], autoload=True)

		# Definicion del insert y update masivo
		i = self.def_valores_texto_d.insert()
		u = self.def_valores_texto_o.update() \
				.where(and_(self.def_valores_texto_o.c.exploracion_id == bindparam("_exploracion_id"), \
							self.def_valores_texto_o.c.formulario_id == bindparam("_formulario_id"), \
							self.def_valores_texto_o.c.campo_id == bindparam("_campo_id"))) \
				.values({"data_destino_uid": bindparam('data_destino_uid')})

		# reset los data_destino_uid de origen si ya se migraron. Se hace todo de nuevo.
		self.def_valores_texto_o.update() \
								.where(self.def_valores_texto_o.c.data_destino_uid == self.uid_destino) \
								.values({"data_destino_uid": None}) \
								.execute()
		self.write_log(MSG_ACT_NULL % (ValorTextoO.__name__, self.uid_destino), LOG_INFO)
		
		# delete las creadas en destino con el data origen uid de esta migracion
		self.def_valores_texto_d.delete() \
								.where(self.def_valores_texto_d.c.data_origen_uid == self.uid_origen) \
								.execute()
		self.write_log(MSG_DEL % (ValorTextoD.__name__, self.uid_destino), LOG_INFO)

		migradas_nuevas = 0
		ori_valores_texto_result = self.ori_session.query(ValorTextoO).all()
		output.append("ValoresTexto: Disponibles para migrar(%s)" % (str(len(ori_valores_texto_result))))

		rows_to_add = []
		rows_to_update = []
		for ori_valor_texto in ori_valores_texto_result:

			# obtener exploracion
			des_exploracion = self.get_dest_id(self.exploraciones_hash, ori_valor_texto.exploracion_id)
			if not des_exploracion:
				raise_error_one_line("No se encontro la exploracion: %s" % (str(ori_valor_texto.exploracion_id)))
			
			# obtener formulario
			des_formulario = self.get_dest_id(self.formularios_hash, ori_valor_texto.formulario_id)
			if not des_formulario:
				raise_error_one_line("No se encontro el formulario: %s" % (str(ori_valor_texto.formulario_id)))
			
			# obtener campo
			des_campo = self.get_dest_id(self.campos_hash, ori_valor_texto.campo_id)
			if not des_campo:
				raise_error_one_line("No se encontro el campo: %s" % (str(ori_valor_texto.campo_id)))

			rows_to_add.append({"exploracion_id": des_exploracion, \
								"formulario_id": des_formulario, \
								"campo_id": des_campo, \
								"valor": ori_valor_texto.valor, \
								"data_origen_uid": self.uid_origen })

			rows_to_update.append({"data_destino_uid": self.uid_destino, \
								   "_formulario_id": ori_valor_texto.formulario_id, \
								   "_exploracion_id": ori_valor_texto.exploracion_id, \
								   "_campo_id": ori_valor_texto.campo_id})
			
			migradas_nuevas += 1
			if migradas_nuevas % 500 == 0:
				i.execute(rows_to_add)
				rows_to_add = []
				u.execute(rows_to_update)
				rows_to_update = []
				self.write_log(MSG_STATUS % (ValorTextoD, migradas_nuevas), LOG_INFO)

		if len(rows_to_add) > 0:
			i.execute(rows_to_add)
			rows_to_add = []
			u.execute(rows_to_update)
			rows_to_update = []
			self.write_log(MSG_STATUS % (ValorTextoD, migradas_nuevas), LOG_INFO)
			
		output.append("ValoresTexto: Nuevas(%s) " \
						% (str(migradas_nuevas)))
		self.del_hash_tables()
		self.write_log(MSG_END % (ValorTextoD.__name__), LOG_INFO)
		return output

	def migrar_valores_selec(self):
		# migrar valores selec
		output = []
		self.write_log(MSG_START % (ValorSelecD.__name__), LOG_INFO)
		
		self.def_valores_selec_d = sa.Table('ValoresSelec', self.db_destino['metadata'], autoload=True)
		self.def_valores_selec_o = sa.Table('ValoresSelec', self.db_origen['metadata'], autoload=True)

		# Definicion del insert y update masivo
		i = self.def_valores_selec_d.insert()
		u = self.def_valores_selec_o.update() \
				.where(and_(self.def_valores_selec_o.c.exploracion_id == bindparam("_exploracion_id"), \
							self.def_valores_selec_o.c.formulario_id == bindparam("_formulario_id"), \
							self.def_valores_selec_o.c.campo_id == bindparam("_campo_id"))) \
				.values({"data_destino_uid": bindparam('data_destino_uid')})

		# reset los data_destino_uid de origen si ya se migraron. Se hace todo de nuevo.
		self.def_valores_selec_o.update() \
								.where(self.def_valores_selec_o.c.data_destino_uid == self.uid_destino) \
								.values({"data_destino_uid": None}) \
								.execute()
		self.write_log(MSG_ACT_NULL % (ValorSelecO.__name__, self.uid_destino), LOG_INFO)
		
		# delete las creadas en destino con el data origen uid de esta migracion
		self.def_valores_selec_d.delete() \
								.where(self.def_valores_selec_d.c.data_origen_uid == self.uid_origen) \
								.execute()
		self.write_log(MSG_DEL % (ValorSelecD.__name__, self.uid_destino), LOG_INFO)

		migradas_nuevas = 0
		ori_valores_selec_result = self.ori_session.query(ValorSelecO).all()
		output.append("ValoresSelec: Disponibles para migrar(%s)" % (str(len(ori_valores_selec_result))))

		rows_to_add = []
		rows_to_update = []
		for ori_valor_selec in ori_valores_selec_result:

			# obtener exploraicon
			des_exploracion = self.get_dest_id(self.exploraciones_hash, ori_valor_selec.exploracion_id)
			if not des_exploracion:
				raise_error_one_line("No se encontro la exploracion: %s" % (str(ori_valor_selec.exploracion_id)))
			
			# obtener formulario
			des_formulario = self.get_dest_id(self.formularios_hash, ori_valor_selec.formulario_id)
			if not des_formulario:
				raise_error_one_line("No se encontro el formulario: %s" % (str(ori_valor_selec.formulario_id)))
			
			# obtener campo
			des_campo = self.get_dest_id(self.campos_hash, ori_valor_selec.campo_id)
			if not des_campo:
				raise_error_one_line("No se encontro el campo: %s" % (str(ori_valor_selec.campo_id)))
			
			# obtener elemento
			des_elemento = None
			if ori_valor_selec.elemento_id:
				des_elemento = self.get_dest_id(self.elementos_hash, ori_valor_selec.elemento_id)

			rows_to_add.append({"exploracion_id": des_exploracion, \
								"formulario_id": des_formulario, \
								"campo_id": des_campo, \
								"elemento_id": des_elemento, \
								"data_origen_uid": self.uid_origen })

			rows_to_update.append({"data_destino_uid": self.uid_destino, \
								   "_formulario_id": ori_valor_selec.formulario_id, \
								   "_exploracion_id": ori_valor_selec.exploracion_id, \
								   "_campo_id": ori_valor_selec.campo_id})
			
			migradas_nuevas += 1
			if migradas_nuevas % 500 == 0:
				i.execute(rows_to_add)
				rows_to_add = []
				u.execute(rows_to_update)
				rows_to_update = []
				self.write_log(MSG_STATUS % (ValorSelecD, migradas_nuevas), LOG_INFO)

		if len(rows_to_add) > 0:
			i.execute(rows_to_add)
			rows_to_add = []
			u.execute(rows_to_update)
			rows_to_update = []
			self.write_log(MSG_STATUS % (ValorSelecD, migradas_nuevas), LOG_INFO)

		output.append("ValoresSelec: Nuevas(%s) " \
						% (str(migradas_nuevas)))
		self.del_hash_tables()
		self.write_log(MSG_END % (ValorSelecD.__name__), LOG_INFO)
		return output

	def migrar_valores_multi(self):
		output = []
		self.write_log(MSG_START % (ValorMultiD.__name__), LOG_INFO)

		self.def_valores_multi_d = sa.Table('ValoresMulti', self.db_destino['metadata'], autoload=True)
		self.def_valores_multi_o = sa.Table('ValoresMulti', self.db_origen['metadata'], autoload=True)

		# Definicion del insert y update masivo
		i = self.def_valores_multi_d.insert()
		u = self.def_valores_multi_o.update() \
				.where(and_(self.def_valores_multi_o.c.exploracion_id == bindparam("_exploracion_id"), \
							self.def_valores_multi_o.c.formulario_id == bindparam("_formulario_id"), \
							self.def_valores_multi_o.c.elemento_id == bindparam("_elemento_id"), \
							self.def_valores_multi_o.c.campo_id == bindparam("_campo_id"))) \
				.values({"data_destino_uid": bindparam('data_destino_uid')})

		# reset los data_destino_uid de origen si ya se migraron. Se hace todo de nuevo.
		self.def_valores_multi_o.update() \
								.where(self.def_valores_multi_o.c.data_destino_uid == self.uid_destino) \
								.values({"data_destino_uid": None}) \
								.execute()
		self.write_log(MSG_ACT_NULL % (ValorMultiO.__name__, self.uid_destino), LOG_INFO)
		
		# delete las creadas en destino con el data origen uid de esta migracion
		self.def_valores_multi_d.delete() \
								.where(self.def_valores_multi_d.c.data_origen_uid == self.uid_origen) \
								.execute()
		self.write_log(MSG_DEL % (ValorMultiD.__name__, self.uid_destino), LOG_INFO)

		migradas_nuevas = 0
		ori_valores_multi_result = self.ori_session.query(ValorMultiO).all()
		output.append("ValoresMulti: Disponibles para migrar(%s)" % (str(len(ori_valores_multi_result))))

		rows_to_add = []
		rows_to_update = []
		for ori_valor_multi in ori_valores_multi_result:

			# obtener exploraicon
			des_exploracion = self.get_dest_id(self.exploraciones_hash, ori_valor_multi.exploracion_id)
			if not des_exploracion:
				raise_error_one_line("No se encontro la exploracion: %s" % (str(ori_valor_multi.exploracion_id)))
			
			# obtener formulario
			des_formulario = self.get_dest_id(self.formularios_hash, ori_valor_multi.formulario_id)
			if not des_formulario:
				raise_error_one_line("No se encontro el formulario: %s" % (str(ori_valor_multi.formulario_id)))
			
			# obtener campo
			des_campo = self.get_dest_id(self.campos_hash, ori_valor_multi.campo_id)
			if not des_campo:
				raise_error_one_line("No se encontro el campo: %s" % (str(ori_valor_multi.campo_id)))
			
			# obtener elemento
			des_elemento = self.get_dest_id(self.elementos_hash, ori_valor_multi.elemento_id)
			if not des_elemento:
				raise_error_one_line("No se encontro el elemento: %s" % (str(ori_valor_multi.elemento_id)))

			rows_to_add.append({"exploracion_id": des_exploracion, \
								"formulario_id": des_formulario, \
								"campo_id": des_campo, \
								"elemento_id": des_elemento, \
								"orden": ori_valor_multi.orden, \
								"cantidad": ori_valor_multi.cantidad, \
								"data_origen_uid": self.uid_origen })

			rows_to_update.append({"data_destino_uid": self.uid_destino, \
								   "_formulario_id": ori_valor_multi.formulario_id, \
								   "_exploracion_id": ori_valor_multi.exploracion_id, \
								   "_elemento_id": ori_valor_multi.elemento_id, \
								   "_campo_id": ori_valor_multi.campo_id})
			
			migradas_nuevas += 1
			if migradas_nuevas % 500 == 0:
				i.execute(rows_to_add)
				rows_to_add = []
				u.execute(rows_to_update)
				rows_to_update = []
				self.write_log(MSG_STATUS % (ValorMultiD, migradas_nuevas), LOG_INFO)

		if len(rows_to_add) > 0:
			i.execute(rows_to_add)
			rows_to_add = []
			u.execute(rows_to_update)
			rows_to_update = []
			self.write_log(MSG_STATUS % (ValorMultiD, migradas_nuevas), LOG_INFO)

		output.append("ValoresMulti: Nuevas(%s) / " \
						% (str(migradas_nuevas)))
		self.del_hash_tables()
		self.write_log(MSG_END % (ValorMultiD.__name__), LOG_INFO)
		return output

	def migrar_valores_bool(self):
		output = []
		self.write_log(MSG_START % (ValorBoolD.__name__), LOG_INFO)

		self.def_valores_bool_d = sa.Table('ValoresBool', self.db_destino['metadata'], autoload=True)
		self.def_valores_bool_o = sa.Table('ValoresBool', self.db_origen['metadata'], autoload=True)

		# Definicion del insert y update masivo
		i = self.def_valores_bool_d.insert()
		u = self.def_valores_bool_o.update() \
				.where(and_(self.def_valores_bool_o.c.exploracion_id == bindparam("_exploracion_id"), \
							self.def_valores_bool_o.c.formulario_id == bindparam("_formulario_id"), \
							self.def_valores_bool_o.c.campo_id == bindparam("_campo_id"))) \
				.values({"data_destino_uid": bindparam('data_destino_uid')})

		# reset los data_destino_uid de origen si ya se migraron. Se hace todo de nuevo.
		self.def_valores_bool_o.update() \
								.where(self.def_valores_bool_o.c.data_destino_uid == self.uid_destino) \
								.values({"data_destino_uid": None}) \
								.execute()
		self.write_log(MSG_ACT_NULL % (ValorBoolO.__name__, self.uid_destino), LOG_INFO)
		
		# delete las creadas en destino con el data origen uid de esta migracion
		self.def_valores_bool_d.delete() \
								.where(self.def_valores_bool_d.c.data_origen_uid == self.uid_origen) \
								.execute()
		self.write_log(MSG_DEL % (ValorBoolD.__name__, self.uid_destino), LOG_INFO)

		migradas_nuevas = 0
		ori_valores_bool_result = self.ori_session.query(ValorBoolO).all()
		output.append("ValoresBool: Disponibles para migrar(%s)" % (str(len(ori_valores_bool_result))))

		rows_to_add = []
		rows_to_update = []
		for ori_valor_bool in ori_valores_bool_result:

			# obtener exploraicon
			des_exploracion = self.get_dest_id(self.exploraciones_hash, ori_valor_bool.exploracion_id)
			if not des_exploracion:
				raise_error_one_line("No se encontro la exploracion: %s" % (str(ori_valor_bool.exploracion_id)))
			
			# obtener formulario
			des_formulario = self.get_dest_id(self.formularios_hash, ori_valor_bool.formulario_id)
			if not des_formulario:
				raise_error_one_line("No se encontro el formulario: %s" % (str(ori_valor_bool.formulario_id)))
			
			# obtener campo
			des_campo = self.get_dest_id(self.campos_hash, ori_valor_bool.campo_id)
			if not des_campo:
				raise_error_one_line("No se encontro el campo: %s" % (str(ori_valor_bool.campo_id)))

			rows_to_add.append({"exploracion_id": des_exploracion, \
								"formulario_id": des_formulario, \
								"campo_id": des_campo, \
								"valor": ori_valor_bool.valor, \
								"data_origen_uid": self.uid_origen })

			rows_to_update.append({"data_destino_uid": self.uid_destino, \
								   "_formulario_id": ori_valor_bool.formulario_id, \
								   "_exploracion_id": ori_valor_bool.exploracion_id, \
								   "_campo_id": ori_valor_bool.campo_id})
			
			migradas_nuevas += 1
			if migradas_nuevas % 500 == 0:
				i.execute(rows_to_add)
				rows_to_add = []
				u.execute(rows_to_update)
				rows_to_update = []
				self.write_log(MSG_STATUS % (ValorBoolD, migradas_nuevas), LOG_INFO)

		if len(rows_to_add) > 0:
			i.execute(rows_to_add)
			rows_to_add = []
			u.execute(rows_to_update)
			rows_to_update = []
			self.write_log(MSG_STATUS % (ValorBoolD, migradas_nuevas), LOG_INFO)

		output.append("ValoresBool: Nuevas(%s)" \
						% (str(migradas_nuevas)))
		self.del_hash_tables()
		self.write_log(MSG_END % (ValorBoolD.__name__), LOG_INFO)
		return output

	def migrar_capturas_bd(self):
		# migrar capturas
		output = []
		self.write_log(MSG_START % (CapturaD.__name__), LOG_INFO)

		self.def_capturas_d = sa.Table('Capturas', self.db_destino['metadata'], autoload=True)
		self.def_capturas_o = sa.Table('Capturas', self.db_origen['metadata'], autoload=True)
		i = self.def_capturas_d.insert()
		u = self.def_capturas_o.update() \
				.where(self.def_capturas_o.c.id == bindparam("_id")) \
				.values({"data_destino_uid": bindparam('data_destino_uid')})

		# reset los data_destino_uid de origen si ya se migraron. Se hace todo de nuevo.
		self.def_capturas_o.update() \
							.where(self.def_capturas_o.c.data_destino_uid == self.uid_destino) \
							.values({"data_destino_uid": None}) \
							.execute()
		self.write_log(MSG_ACT_NULL % (CapturaO.__name__, self.uid_destino), LOG_INFO)
		
		# delete las creadas en destino con el data origen uid de esta migracion
		self.def_capturas_d.delete() \
						   .where(self.def_capturas_d.c.data_origen_uid == self.uid_origen) \
						   .execute()
		self.write_log(MSG_DEL % (CapturaD.__name__, self.uid_destino), LOG_INFO)

		migradas_nuevas = 0
		migradas_anteriormente = 0
		ori_capturas_result = self.ori_session.query(CapturaO).all()
		output.append("Capturas: Disponibles para migrar(%s)" % (str(len(ori_capturas_result))))
		rows_to_add = []
		rows_to_update = []
		for ori_captura in ori_capturas_result:

			
				
			# Buscar la exploracion ID
			des_exploracion = self.get_dest_id(self.exploraciones_hash, ori_captura.exploracion_id)
			if not des_exploracion:
				raise_error_one_line("No se encontro la exploracion: %s" % (str(ori_captura.exploracion_id)))

			borrado = ori_captura.borrado
			if borrado == None:
				borrado = False

			rows_to_add.append({"seleccionada": ori_captura.seleccionada, \
							   "SeriesInstanceUID":ori_captura.SeriesInstanceUID, \
							   "SOPInstanceUID": ori_captura.SOPInstanceUID, \
							   "exploracion_id": des_exploracion, \
							   "comentario": ori_captura.comentario, \
							   "orden": ori_captura.orden,\
							   "posx": ori_captura.posx,\
							   "posy": ori_captura.posy,\
							   "tipo": ori_captura.tipo,\
							   "uuid": ori_captura.uuid,\
							   "disponible": ori_captura.disponible,\
							   "borrado": borrado,\
							   "borrado_motivo": ori_captura.borrado_motivo,\
							   "dicom_stored": ori_captura.dicom_stored,\
							   "dicom_stgcmt": ori_captura.dicom_stgcmt,\
							   "data_origen_uid": self.uid_origen,\
							   "data_origen_reg_id": ori_captura.id,\
							   "updated_at": ori_captura.updated_at\
			})

			rows_to_update.append({"data_destino_uid": self.uid_destino, \
							 	  "_id": ori_captura.id })

			migradas_nuevas += 1
			if migradas_nuevas % 500 == 0:
				i.execute(rows_to_add)
				u.execute(rows_to_update)
				rows_to_add = []
				rows_to_update = []	
				self.write_log(MSG_STATUS % (CapturaO.__name__, migradas_nuevas), LOG_INFO)

		if len(rows_to_add)>0:
			i.execute(rows_to_add)
			u.execute(rows_to_update)
			rows_to_add = []
			rows_to_update = []	
			self.write_log(MSG_STATUS % (CapturaO.__name__, migradas_nuevas), LOG_INFO)

		output.append("Capturas: Nuevas(%s) / Migradas anteriomente(%s) / " \
						% (str(migradas_nuevas), str(migradas_anteriormente)))
		self.del_hash_tables()
		self.write_log(MSG_END % (CapturaD.__name__), LOG_INFO)
		return output

	def migrar_informes_bd(self,request):
		output = []
		self.write_log(MSG_START % (InformeD.__name__), LOG_INFO)

		self.def_informes_d = sa.Table('Informes', self.db_destino['metadata'], autoload=True)
		self.def_informes_o = sa.Table('Informes', self.db_origen['metadata'], autoload=True)
		i = self.def_informes_d.insert()
		u = self.def_informes_o.update() \
				.where(self.def_informes_o.c.id == bindparam("_id")) \
				.values({"data_destino_uid": bindparam('data_destino_uid')})

		if 'prefijo_informe' in request.params:
				self.prefijo_informe = int(request.params.get("prefijo_informe"))

		# reset los data_destino_uid de origen si ya se migraron. Se hace todo de nuevo.
		self.def_informes_o.update() \
							.where(self.def_informes_o.c.data_destino_uid == self.uid_destino) \
							.values({"data_destino_uid": None}) \
							.execute()
		self.write_log(MSG_ACT_NULL % (InformeO.__name__, self.uid_destino), LOG_INFO)
		
		# delete las creadas en destino con el data origen uid de esta migracion
		self.def_informes_d.delete() \
						   .where(self.def_informes_d.c.data_origen_uid == self.uid_origen) \
						   .execute()
		self.write_log(MSG_DEL % (InformeD.__name__, self.uid_destino), LOG_INFO)

		migradas_nuevas = 0
		migradas_anteriormente = 0
		ori_informes_result = self.ori_session.query(InformeO).all()
		output.append("Informes: Disponibles para migrar(%s)" % (str(len(ori_informes_result))))
		rows_to_add = []
		rows_to_update = []
		for ori_informe in ori_informes_result:

			#busca el id de la exploracion destino en la hash table
			des_exploracion = self.get_dest_id(self.exploraciones_hash, ori_informe.exploracion_id)
			if not des_exploracion:
				msg = "No se encontro la exploracion: " + str(ori_informe.exploracion_id)
				self.write_log(msg, LOG_ERROR)
				raise Exception(msg)

			# Campo borrado. si es None, le pone False
			borrado = ori_informe.borrado
			if borrado == None:
				borrado = False

			# obtiene el medico para verificar si esta excluido
			# el medico sera sysadmin o admin, busca ese medico en destino y le asigna la exploracion.
			medico_id = None
			if ori_informe.medico_id != None:
				medico_id = self.get_dest_id(self.medicos_hash, ori_informe.medico_id)
				if not medico_id:
					# puede ser que sea uno de los excluidos o que no se haya migrado correctamente.
					ori_medico = self.ori_session.query(MedicoO).filter(MedicoO.id == ori_informe.medico_id).one()
					if ori_medico.username in USERNAME_EXCLUDES:
						des_user = self.des_session.query(UserD).filter(UserD.username == ori_medico.username)
						if des_user.count() == 0:
							raise Exception("No se puede migrar la exploracion porque el medico no existe en destino (%s)" % (ori_medico.username))
						else:
							des_user = des_user.one()
							des_medico = self.des_session.query(MedicoD).filter(MedicoD.username == des_user.username).one()
							medico_id = des_medico.id
					else:
						raise Exception("No se puede migrar la exploracion porque el medico no existe en destino (%s)" % (ori_medico.username))

			rows_to_add.append({"numero": self.prefijo_informe + ori_informe.numero, \
							   "exploracion_id": des_exploracion, \
							   "plantilla": ori_informe.plantilla, \
							   "tipo": ori_informe.tipo, \
							   "fecha": ori_informe.fecha, \
							   "enviado": ori_informe.enviado,\
							   "comentarios": ori_informe.comentarios,\
							   "borrado": borrado,\
							   "borrado_motivo": ori_informe.borrado_motivo,\
							   "medico_id": medico_id,\
							   "data_origen_uid": self.uid_origen,\
							   "data_origen_reg_id": ori_informe.id \
			})

			rows_to_update.append({"data_destino_uid": self.uid_destino, \
							 	  "_id": ori_informe.id })
			
			migradas_nuevas += 1
			if migradas_nuevas % 500 == 0:
				i.execute(rows_to_add)
				u.execute(rows_to_update)
				rows_to_add = []
				rows_to_update = []
				self.write_log(MSG_STATUS % (InformeO.__name__, migradas_nuevas), LOG_INFO)	


		if len(rows_to_add)>0:
			i.execute(rows_to_add)
			u.execute(rows_to_update)
			rows_to_add = []
			rows_to_update = []
			self.write_log(MSG_STATUS % (InformeO.__name__, migradas_nuevas), LOG_INFO)	

		self.del_hash_tables()

		output.append("Informes: Nuevas(%s) / Migradas anteriomente(%s) / " \
						% (str(migradas_nuevas), str(migradas_anteriormente)))
		self.del_hash_tables()
		self.write_log(MSG_END % (InformeD.__name__), LOG_INFO)
		return output

	def migrar_rel_capturas_informes(self):
		output = []
		self.write_log(MSG_START % (Rel_Capturas_InformesD.__name__), LOG_INFO)

		# migrar valores rel_capturas_informes
		self.def_rel_capturas_informes_d = sa.Table('rel_Capturas_Informes', self.db_destino['metadata'], autoload=True)
		self.def_rel_capturas_informes_o = sa.Table('rel_Capturas_Informes', self.db_origen['metadata'], autoload=True)
		
		# Definicion del insert y update masivo
		i = self.def_rel_capturas_informes_d.insert()
		u = self.def_rel_capturas_informes_o.update() \
				.where(and_(self.def_rel_capturas_informes_o.c.informe_id == bindparam("_informe_id"), \
							self.def_rel_capturas_informes_o.c.captura_id == bindparam("_captura_id"))) \
				.values({"data_destino_uid": bindparam('data_destino_uid')})

		# reset los data_destino_uid de origen si ya se migraron. Se hace todo de nuevo.
		self.def_rel_capturas_informes_o.update() \
								.where(self.def_rel_capturas_informes_o.c.data_destino_uid == self.uid_destino) \
								.values({"data_destino_uid": None}) \
								.execute()
		self.write_log(MSG_ACT_NULL % (Rel_Capturas_InformesO.__name__, self.uid_destino), LOG_INFO)
		
		# delete las relaciones creadas en destino con el data origen uid de esta migracion
		self.def_rel_capturas_informes_d.delete() \
								.where(self.def_rel_capturas_informes_d.c.data_origen_uid == self.uid_origen) \
								.execute()
		self.write_log(MSG_DEL % (Rel_Capturas_InformesD.__name__, self.uid_destino), LOG_INFO)

		# recorrer las no migradas y agregarlas
		migradas_nuevas = 0
		ori_rel_capturas_informes_result = self.ori_session.query(Rel_Capturas_InformesO).all()
		output.append("Rel_Capturas_Informes: Disponibles para migrar(%s)" % (str(len(ori_rel_capturas_informes_result))))

		# insertar en destino y actualizar origen
		rows_to_add = []
		rows_to_update = []
		for ori_rel_captura_informe in ori_rel_capturas_informes_result:
			
			des_captura = self.get_dest_id(self.capturas_hash, ori_rel_captura_informe.captura_id)
			if not des_captura:
				raise_error_one_line("No se encontro la captura: %s" % (str(ori_rel_captura_informe.captura_id)))

			des_informe = self.get_dest_id(self.informes_hash, ori_rel_captura_informe.informe_id)
			if not des_informe:
				raise_error_one_line("No se encontro la informe: %s" % (str(ori_rel_captura_informe.informe_id)))

			rows_to_add.append({"captura_id": des_captura, \
								"informe_id": des_informe, \
								"orden": ori_rel_captura_informe.orden, \
								"data_origen_uid": self.uid_origen})
			rows_to_update.append({"data_destino_uid": self.uid_destino, \
								   "_informe_id": ori_rel_captura_informe.informe_id, \
								   "_captura_id": ori_rel_captura_informe.captura_id })

			migradas_nuevas += 1

			# cada vez que el dict llega a 500 se insertan y actualizan
			if migradas_nuevas % 500 == 0:
				i.execute(rows_to_add)
				rows_to_add = []
				u.execute(rows_to_update)
				rows_to_update = []
				self.write_log(MSG_STATUS % (Rel_Capturas_InformesD, migradas_nuevas), LOG_INFO)

		# se insertan y actualizan las restantes que no dan resto = 0 en la cuenta % 500
		if len(rows_to_add) > 0:
			i.execute(rows_to_add)
			rows_to_add = []
			u.execute(rows_to_update)
			rows_to_update = []
			self.write_log(MSG_STATUS % (Rel_Capturas_InformesD, migradas_nuevas), LOG_INFO)


		output.append("Rel_Capturas_Informes: Nuevas(%s)  " \
						% (str(migradas_nuevas)))
		self.del_hash_tables()
		self.write_log(MSG_END % (Rel_Capturas_InformesD.__name__), LOG_INFO)
		return output

	def migrar_citas(self):
		output = []
		self.write_log(MSG_START % (CitaD.__name__), LOG_INFO)

		migradas_nuevas = 0
		migradas_anteriormente = 0
		ori_citas_result = self.ori_session.query(CitaO).all()

		output.append(MSG_DISP % (CitasO.__name__, len(ori_citas_result)))
		self.write_log(MSG_DISP % (CitasO.__name__, len(ori_citas_result)), LOG_INFO)
		for ori_cita in ori_citas_result:

			des_cita = self.get_row_des_from_ori_id(CitaD, ori_cita.id, True)
			if not des_cita:

				# primero busca si ya se creo en esta migracion que se esta ejecutando para 
				# evitar tener que hacer una nueva consulta.
				paciente_id = None
				paciente_dict = self.get_dest_id(self.pacientes_dict, ori_cita.paciente_id)
				if paciente_dict:
					paciente_id = paciente_dict
				else:
					# si no se creo en esta migracion que se esta ejecutando se intenta crearlo o obtenerlo
					des_paciente = self.obtener_crear_paciente(ori_cita.paciente_id)
					if not des_paciente:
						raise ConflictoPacienteError("Paciente ID Origen: %s existe en destino pero tiene diferente nombre" % (str(ori_exploracion.paciente_id)))
					paciente_id = des_paciente.id

				#aca no se excluye, se le asigan al admin o sysadmin (id 2 y 1 respectivamente)
				medico_id = None
				if ori_cita.medico_id:
					# obtiene el medico para verificar si esta excluido
					# el medico sera sysadmin o admin, busca ese medico en destino y le asigna la exploracion.
					ori_medico = self.ori_session.query(MedicoO).filter(MedicoO.id == ori_cita.medico_id).one()
					if ori_medico.username in USERNAME_EXCLUDES:
						des_user = self.des_session.query(UserD).filter(UserD.username == ori_medico.username)
						if des_user.count() == 0:
							raise Exception("No se puede migrar la cita porque el medico no existe en destino (%s)" % (ori_medico.username))
						else:
							des_user = des_user.one()
							des_medico = self.des_session.query(MedicoD).filter(MedicoD.username == des_user.username).one()
							medico_id = des_medico.id
					else:
						des_medico = self.get_row_des_from_ori_id(MedicoD, ori_cita.medico_id)
						medico_id = des_medico.id

				sala_id = None
				if ori_cita.sala_id:
					sala_id = self.get_dest_id(self.salas_hash, ori_cita.sala_id)
				
				tipo_expl_id = None
				if ori_cita.tipoExploracion_id:
					tipo_expl_id = self.get_dest_id(self.tipos_exploraciones_hash, ori_cita.tipoExploracion_id)

				exploracion_id = None
				if ori_cita.exploracion_id:
					exploracion_id = self.get_dest_id(self.exploraciones_hash, ori_cita.exploracion_id)

				motivo_id = None
				if ori_cita.motivo_id:
					motivo_id = self.get_dest_id(self.motivos_hash, ori_cita.motivo_id)

				prioridad_id = None
				if ori_cita.prioridad_id:
					prioridad_id = self.get_dest_id(self.prioridades_hash, ori_cita.prioridad_id)

				agenda_id = None
				if ori_cita.agenda_id:
					agenda_id = self.get_dest_id(self.agendas_hash, ori_cita.agenda_id)

				aseguradora_id = None
				if ori_cita.aseguradora_id:
					asguradora_id = self.self.get_dest_id(self.aseguradora_hash, ori_cita.aseguradora_id)

				cita = CitaD()
				cita.paciente_id = paciente_id
				cita.medico_id = medico_id
				cita.sala_id = sala_id
				cita.tipoExploracion_id = tipo_expl_id
				cita.exploracion_id = exploracion_id
				cita.motivo_id = motivo_id
				cita.fecha = ori_cita.fecha
				cita.hora = ori_cita.hora
				cita.observaciones = ori_cita.observaciones
				cita.prioridad_id = prioridad_id
				cita.cancelada = ori_cita.cancelada
				cita.agenda_id = agenda_id
				cita.duracion = ori_cita.duracion
				cita.aseguradora_id = ori_cita.aseguradora_id
				cita.data_origen_uid = self.uid_origen
				cita.data_origen_reg_id = ori_cita.id
				self.save_new_row_destino(cita)
				self.update_data_destino_uid(ori_cita)

				self.write_log(MSG_NUEVA % (CitaO.__name__, str(ori_cita.id)), LOG_INFO)
				migradas_nuevas += 1
			else:
				self.write_log(MSG_MIGRADA % (CitaO.__name__, str(ori_cita.id)), LOG_INFO)
				migradas_anteriormente +=1

		self.del_hash_tables()
		output.append(MSG_TOTAL_NEW_ACT % (CitasD.__name__, migradas_nuevas, migradas_anteriormente))
		self.write_log(MSG_TOTAL_NEW_ACT % (CitasD.__name__, migradas_nuevas, migradas_anteriormente), LOG_INFO)
		self.write_log(MSG_END % (CitaD.__name__), LOG_INFO)
		return output

	def copiar_mover_capturas(self, request):
		output = []

		# parametro que dice si se mueven o se copian
		mover_capturas = False
		if 'mover_capturas' in request.params:
			if request.params.get('mover_capturas') == 'on':
				mover_capturas = True

		capturas = self.des_session.query(CapturaD).filter(CapturaD.data_origen_uid==self.uid_origen).all()
		output.append("Archivos de capturas (en BD) a copiar/mover = %s" % (str(len(capturas))))

		capturas_origen = request.params.get('capturas_origen', None)
		capturas_destino = request.params.get('capturas_destino', None)

		# check si las rutas se enviaron
		if not capturas_origen or not capturas_destino:
			msg = "Las rutas de ubicacion de capturas no estan correctamente configuradas"
			self.write_log(msg, LOG_ERROR)
			raise Exception(msg)

		# check si las rutas existen
		if not os.path.exists(capturas_origen):
			msg = "La ruta de capturas origen no existe"
			self.write_log(msg, LOG_ERROR)
			raise Exception(msg)
		if not os.path.exists(capturas_destino):
			msg = "La ruta de capturas origen no existe"
			self.write_log(msg, LOG_ERROR)
			raise Exception(msg)


		# Solo test!!. para generar capturas falsos.
		# agarra un archivo que esta dentro de la carpeta capturas_origen/test/test.pdf
		# y los copia en las ubicaciones de los posibles capturas de la ase de datos origen
		# simulando que son capturas verdaderos. SOLO PARA TEST!
		if 'generate_capturas_test' in request.params \
			and request.params.get('generate_capturas_test') == 'on':
			for captura in capturas:
				#obtener anio/mes de la exploracion
				des_exploracion = self.get_expl_mes_anio_id(self.expl_mes_anio_dict, captura.exploracion_id)
				anio = des_exploracion['anio']
				mes = des_exploracion['mes']
				filename_origen = '.'.join( (str(captura.data_origen_reg_id), 'jpg') )
				ruta_anio_mes = os.path.join(capturas_origen, anio, mes, filename_origen)
				dir_destino = os.path.join(capturas_origen, anio, mes)
				if not os.path.exists(dir_destino):
					os.makedirs(dir_destino)
				test_copia = os.path.join(capturas_origen, 'test', 'test.jpg')
				shutil.copy2(test_copia, ruta_anio_mes)

			output.append("Se crearon %s capturas de test" % (str(len(capturas))))
			return output

		original_no_encontrado = 0
		copiados = 0
		ya_existe = 0
		error = 0
		for captura in capturas:
			
			#obtener anio/mes de la exploracion
			des_exploracion = self.get_expl_mes_anio_id(self.expl_mes_anio_dict, captura.exploracion_id)
			anio = des_exploracion['anio']
			mes = des_exploracion['mes']	

			# setear el tipo
			tipo = 'jpg'
			if captura.tipo:
				tipo = captura.tipo

			# setear filename, con el data origen reg id en origen y con id en destino
			filename_origen = '.'.join( (str(captura.data_origen_reg_id), tipo) ) 
			filename_destino = '.'.join( (str(captura.id), tipo) )
			
			# rutas completas de los archivos.
			ruta_archivo_origen = None
			ruta_archico_destino = None

			#verificar que captura no este en raiz
			ruta_raiz = os.path.join(capturas_origen, filename_origen)
			if os.path.exists(ruta_raiz):
				# copiar desde la raiz
				ruta_archivo_origen = ruta_raiz
			else:
				#tiene que estar dentro de estructura anio/mes
				ruta_anio_mes = os.path.join(capturas_origen, anio, mes, filename_origen)

				if os.path.exists(ruta_anio_mes):
					ruta_archivo_origen = ruta_anio_mes
				else:
					self.write_log("No se encontro archivo en %s" % (ruta_anio_mes), LOG_WARNING)
					original_no_encontrado += 1

			if ruta_archivo_origen:
				# si existe origen,entonces se procede a copiar.
					
				dir_destino = os.path.join(capturas_destino, anio, mes)
				if not os.path.exists(dir_destino):
					os.makedirs(dir_destino)

				ruta_archivo_destino = os.path.join(capturas_destino, anio, mes, filename_destino)
				
				#copiar 
				if not os.path.exists(ruta_archivo_destino):
					# si no existe copio directamente.
					try:
						msg = ''
						if mover_capturas:
							msg = "movio"
							shutil.move(ruta_archivo_origen, ruta_archivo_destino)
						else:
							msg = "copio"
							shutil.copy2(ruta_archivo_origen, ruta_archivo_destino)

						self.write_log("Se %s captura [%s -> %s]" % (msg,ruta_archivo_origen, ruta_archivo_destino), LOG_INFO)
						copiados += 1
					except Exception, e:
						# error al copiar
						self.write_log("Error al copiar captura: " + str(e), LOG_ERROR)
						error +=1
				else:
					# ya existe el archivo. SI existe no se copia.
					self.write_log("Ya existe la ruta destino %s " % (ruta_archivo_destino), LOG_WARNING)
					ya_existe +=1
			
			#thumbs
			if tipo == 'jpg':
				filename_origen_thumb = '.'.join( (str(captura.data_origen_reg_id), "thumb") )
				filename_destino_thumb = '.'.join( (str(captura.id), "thumb") )

				# rutas completas de los archivos.
				ruta_archivo_origen_thumb = None
				ruta_archivo_destino_thumb = None

				#verificar que captura no este en raiz
				ruta_raiz_thumb = os.path.join(capturas_origen, filename_origen_thumb)
				if os.path.exists(ruta_raiz_thumb):
					# copiar desde la raiz
					ruta_archivo_origen_thumb = ruta_raiz_thumb
				else:
					#tiene que estar dentro de estructura anio/mes
					ruta_anio_mes_thumb = os.path.join(capturas_origen, anio, mes, filename_origen_thumb)

					if os.path.exists(ruta_anio_mes_thumb):
						ruta_archivo_origen_thumb = ruta_anio_mes_thumb
					else:
						self.write_log("No se encontro archivo en %s" % (ruta_anio_mes_thumb), LOG_WARNING)
						#original_no_encontrado += 1

				if ruta_archivo_origen_thumb:
					# si existe origen,entonces se procede a copiar.
					
					dir_destino_thumb = os.path.join(capturas_destino, anio, mes)
					if not os.path.exists(dir_destino_thumb):
						os.makedirs(dir_destino_thumb)

					ruta_archivo_destino_thumb = os.path.join(capturas_destino, anio, mes, filename_destino_thumb)
				
					#copiar 
					if not os.path.exists(ruta_archivo_destino_thumb):
						# si no existe copio directamente.
						try:
							msg = ''
							if mover_capturas:
								msg = "movio"
								shutil.move(ruta_archivo_origen_thumb, ruta_archivo_destino_thumb)
							else:
								msg = "copio"
								shutil.copy2(ruta_archivo_origen_thumb, ruta_archivo_destino_thumb)

							self.write_log("Se %s captura (thumb) [%s -> %s]" % (msg,ruta_archivo_origen_thumb, ruta_archivo_destino_thumb), LOG_INFO)
							#copiados += 1
						except Exception, e:
							# error al copiar
							self.write_log("Error al copiar captura (thumb): " + str(e), LOG_ERROR)
							#error +=1
					else:
						# ya existe el archivo. SI existe no se copia.
						self.write_log("Ya existe la ruta destino (thumb) %s " % (ruta_archivo_destino_thumb), LOG_WARNING)
						#ya_existe +=1
			
		output.append("Archivos de capturas: movidos o copiados(%s) / Archivo ya existente(%s) / Error de copia(%s) / No se encontro el archivo (%s) " % (str(copiados), str(ya_existe), str(error), str(original_no_encontrado)))
		return output

	def copiar_mover_informes(self, request):
		
		output = []
		mover_informes = False
		if 'mover_informes' in request.params:
			if request.params.get('mover_informes') == 'on':
				mover_informes = True

		informes = self.des_session.query(InformeD).filter(InformeD.data_origen_uid==self.uid_origen).all()
		#informes = informes.filter(InformeD.id>=120353).all()
		output.append("Archivos de informes (en BD) a copiar/mover = %s" % (str(len(informes))))

		informes_origen = request.params.get('informes_origen', None)
		informes_destino = request.params.get('informes_destino', None)

		# check si las rutas se enviaron
		if not informes_origen or not informes_destino:
			msg = "Las rutas de ubicacion de informes no estan correctamente configuradas"
			self.write_log(msg, LOG_ERROR)
			raise Exception(msg)

		# check si las rutas existen
		if not os.path.exists(informes_origen):
			msg = "La ruta de informes origen no existe"
			self.write_log(msg, LOG_ERROR)
			raise Exception(msg)
		if not os.path.exists(informes_destino):
			msg = "La ruta de informes origen no existe"
			self.write_log(msg, LOG_ERROR)
			raise Exception(msg)

		# Solo test!!. para generar informes falsos.
		# agarra un archivo que esta dentro de la carpeta informes_origen/test/test.pdf
		# y los copia en las ubicaciones de los posibles informes de la ase de datos origen
		# simulando que son informes verdaderos. SOLO PARA TEST!
		if 'generate_informes_test' in request.params \
			and request.params.get('generate_informes_test') == 'on':
			for informe in informes:
				#obtener anio/mes de la exploracion
				des_exploracion = self.des_session.query(ExploracionD) \
								  .filter(ExploracionD.id == informe.exploracion_id).one()
				d = des_exploracion.fecha
				filename_origen = '.'.join( (str(informe.data_origen_reg_id), 'local.html') )
				ruta_anio_mes = os.path.join(informes_origen, str(d.year), str('%02d' % d.month), filename_origen)
				dir_destino = os.path.join(informes_origen, str(d.year), str('%02d' % d.month))
				if not os.path.exists(dir_destino):
					os.makedirs(dir_destino)
				test_copia = os.path.join(informes_origen, 'test', 'test.pdf')
				shutil.copy2(test_copia, ruta_anio_mes)
			
			output.append("Se crearon %s informes de test" % (str(len(informes))))
			return output

		original_no_encontrado = 0
		copiados = 0
		ya_existe = 0
		error = 0
		for informe in informes:
			
			#obtener anio/mes de la exploracion
			des_exploracion = self.des_session.query(ExploracionD) \
							  .filter(ExploracionD.id == informe.exploracion_id).one()
			d = des_exploracion.fecha
			dir_anio_mes_origen = os.path.join(informes_origen, str(d.year), str('%02d' % d.month))
			dir_anio_mes_destino = os.path.join(informes_destino, str(d.year), str('%02d' % d.month))
			
			# setear filename, con el data origen reg id en origen y con id en destino
			filename_origen_pdf = '.'.join( (str(informe.data_origen_reg_id), 'pdf') ) 
			filename_origen_html_local = '.'.join( (str(informe.data_origen_reg_id), 'local.html') ) 
			filename_origen_html = '.'.join( (str(informe.data_origen_reg_id), 'html') ) 
			filename_destino_pdf = None
			filename_destino_html = None
			filename_destino_html_local = None
			
			# verifica si existe el html
			ruta_archivo_origen_html = os.path.join(informes_origen, filename_origen_html)
			if os.path.exists(ruta_archivo_origen_html):
				filename_destino_html = '.'.join( (str(informe.id), 'html') )
			else:
				ruta_anio_mes_origen_html = os.path.join(dir_anio_mes_origen, filename_origen_html)
				if os.path.exists(ruta_anio_mes_origen_html):
					ruta_archivo_origen_html = ruta_anio_mes_origen_html
					filename_destino_html = '.'.join( (str(informe.id), 'html') )
					
			# verifica si existe el html.local
			ruta_archivo_origen_html_local = os.path.join(informes_origen, filename_origen_html_local)
			if os.path.exists(ruta_archivo_origen_html_local):
				filename_destino_html_local = '.'.join( (str(informe.id), 'local.html') )
			else:
				ruta_anio_mes_origen_html_local = os.path.join(dir_anio_mes_origen, filename_origen_html_local)
				if os.path.exists(ruta_anio_mes_origen_html_local):
					ruta_archivo_origen_html_local = ruta_anio_mes_origen_html_local
					filename_destino_html_local = '.'.join( (str(informe.id), 'local.html') )

			# verifica si existe el pdf
			ruta_archivo_origen_pdf = os.path.join(informes_origen, filename_origen_pdf)
			if os.path.exists(ruta_archivo_origen_pdf):
				filename_destino_pdf = '.'.join( (str(informe.id), 'pdf') )
			else:
				ruta_anio_mes_origen_pdf = os.path.join(dir_anio_mes_origen, filename_origen_pdf)
				if os.path.exists(ruta_anio_mes_origen_pdf):
					ruta_archivo_origen_pdf = ruta_anio_mes_origen_pdf
					filename_destino_pdf = '.'.join( (str(informe.id), 'pdf') )
			
			if not filename_destino_pdf and not filename_destino_html and not filename_destino_html_local:
				# Si no se creo el nombre del archivo destino en ninguno de sus 3 formatos entonces no existe
				self.write_log("No se encontro archivo en de informe con id %s" % (str(informe.id)), LOG_ERROR)
				original_no_encontrado += 1
			else:
				# si existe origen,entonces se procede a copiar.
				if not os.path.exists(dir_anio_mes_destino):
					os.makedirs(dir_anio_mes_destino)

				if filename_destino_html:
					ruta_archivo_destino_html = os.path.join(informes_destino, str(d.year), str('%02d' % d.month), filename_destino_html)
					if not os.path.exists(ruta_archivo_destino_html):
						# si no existe copio/muevo directamente.
						try:
							msg = ''
							if mover_informes:
								msg = "movio"
								shutil.move(ruta_archivo_origen_html, ruta_archivo_destino_html)
							else:
								msg = "copio"
								shutil.copy2(ruta_archivo_origen_html, ruta_archivo_destino_html)
							
							self.write_log("Se %s el informe [%s -> %s]" % (msg, ruta_archivo_origen_html, ruta_archivo_destino_html), LOG_INFO)
							copiados +=1
						except Exception, e:
							# error al copiar
							self.write_log("Error al copiar informe: " + str(e), LOG_ERROR)
							error +=1
					else:
						# ya existe el archivo. SI existe no se copia.
						self.write_log("Ya existe la ruta destino %s " % (ruta_archivo_destino_html), LOG_WARNING)
						ya_existe += 1
				
				if filename_destino_html_local:
					ruta_archivo_destino_html_local = os.path.join(informes_destino, str(d.year), str('%02d' % d.month), filename_destino_html_local)
					if not os.path.exists(ruta_archivo_destino_html_local):
						# si no existe copio/muevo directamente.
						try:
							msg = ''
							if mover_informes:
								msg = "movio"
								shutil.move(ruta_archivo_origen_html_local, ruta_archivo_destino_html_local)
							else:
								msg = "copio"
								shutil.copy2(ruta_archivo_origen_html_local, ruta_archivo_destino_html_local)
							
							self.write_log("Se %s el informe [%s -> %s]" % (msg, ruta_archivo_origen_html_local, ruta_archivo_destino_html_local), LOG_INFO)
							copiados +=1
						except Exception, e:
							# error al copiar
							self.write_log("Error al copiar informe: " + str(e), LOG_ERROR)
							error +=1
					else:
						# ya existe el archivo. SI existe no se copia.
						self.write_log("Ya existe la ruta destino %s " % (ruta_archivo_destino_html_local), LOG_WARNING)
						ya_existe += 1
				
				if filename_destino_pdf:
					ruta_archivo_destino_pdf = os.path.join(informes_destino, str(d.year), str('%02d' % d.month), filename_destino_pdf)
					if not os.path.exists(ruta_archivo_destino_pdf):
						# si no existe copio/muevo directamente.
						try:
							msg = ''
							if mover_informes:
								msg = "movio"
								shutil.move(ruta_archivo_origen_pdf, ruta_archivo_destino_pdf)
							else:
								msg = "copio"
								shutil.copy2(ruta_archivo_origen_pdf, ruta_archivo_destino_pdf)
							
							self.write_log("Se %s el informe [%s -> %s]" % (msg, ruta_archivo_origen_pdf, ruta_archivo_destino_pdf), LOG_INFO)
							copiados +=1
						except Exception, e:
							# error al copiar
							self.write_log("Error al copiar informe: " + str(e), LOG_ERROR)
							error +=1
					else:
						# ya existe el archivo. SI existe no se copia.
						self.write_log("Ya existe la ruta destino %s " % (ruta_archivo_destino_pdf), LOG_WARNING)
						ya_existe += 1
		
		output.append("Archivos de informes: movidos o copiados(%s) / Archivo ya existente(%s) / Error de copia(%s) / No se encontro el archivo (%s) " % (str(copiados), str(ya_existe), str(error), str(original_no_encontrado)))
		return output

	def get_hash_table(self, db_class):
		""" Crea una hash_table con todas las filas ya migradas
		""" 
		results = self.des_session.query(db_class) \
								  .filter(db_class.data_origen_uid == self.uid_origen) \
								  .all()
		hash_table = []
		for r in results:
			if db_class.__name__ == "Exploracion_dicomD":
				item = {'origen_id':r.data_origen_reg_id, 'destino_id':r.exploracion_id}
			else:
				item = {'origen_id':r.data_origen_reg_id, 'destino_id':r.id}
			hash_table.append(item)
		return hash_table

	def get_dest_id(self, hash_table, origen_id):
		""" dado una hash_table y un origen_id, devuelve el destino_id
		"""
		result = [i for i in hash_table if i['origen_id'] == origen_id]
		if len(result) > 0:
			return result[0]['destino_id']
		else:
			return None

	def get_expl_mes_anio(self):
		""" Crea una un dict con el id de exploracion, el mes y el anio
		""" 
		results = self.des_session.query(ExploracionD) \
								  .filter(ExploracionD.data_origen_uid == self.uid_origen) \
								  .all()
		expl_dict = []
		for r in results:
			item = {'id':r.id, 'mes':str('%02d' % r.fecha.month), 'anio': str(r.fecha.year)}
			expl_dict.append(item)
		return expl_dict

	def get_expl_mes_anio_id(self, dict_expl, id_expl):
		""" dado el array de dict de exploraciones con mes y anio retorna el dict del id
			pedido
		"""
		result = [i for i in dict_expl if i['id'] == id_expl]
		if len(result) > 0:
			return result[0]
		else:
			return None

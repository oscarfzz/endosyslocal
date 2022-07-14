"""
modulo standard de DICOM de endotools web.

	-acceso a worklist (filtro por fecha)
	-guardar el worklist en BBDD
	-enviar una captura al PACS
		-dicomizar la captura
			-a partir de los datos de un work
			-o a partir de los datos pasados como parametro
		-enviar al pacs
	-configuracion de conexion al pacs y worklist en .INI

mas:
	-vincular un work a un a cita o una exploracion
	-tener en cuenta la posibilidad de usar varios equipos (modalities?)
	-separar en modulo de worklist y modulo de pacs(store/retrieve)?
	-al generar uids (seriesInstanceUID y SOPInstanceUID) al dicomizar las
		imágenes, hacerlo flexible, por ejemplo todas las imagenes de una expl
		con el mismo seriesUID, etc...
	-mejorar notificacion de errores y logging

configurable:
	-plantilla para query worklist
	-campos a obtener del worklist
	-como identificar unicamente un work (ahora por el accessionnumber)
		se usaria en get_worklist, update_work y get_work
"""

from endosys.lib.misc import isint
from pylons import config
from endosys.model import meta
from datetime import datetime
import endosys.model.worklist

import logging
log = logging.getLogger(__name__)

# WORKLIST ################################
# No va vinculado directamente a las citas, ya que se podria dar el caso en
# una integracion, por ejemplo, que las citas se obtengan por HL7 y luego en el
# momento de hacer la exploración se recuperar el worklist para dicomizar las
# imágenes.
# igualmente, como el caso mas común es que el worklist se vincule directamente
# con las citas, hay ya un pluginCitas desarrollado para ello:
# (lib.plugins.base.citasWorklist)

"""
	obtiene el worklist segun la libreria y devuelve la lista sin guardarla en base de datos.
	
	params:
		* campos_cmdline:  [ {clase: kPatientName, valor: 'valor_ejemplo'}, ... ]
		* filtros: [ {clase: kModality, clase_padre: kScheduledProcedureStepSequence, valor: 'VL',}]
"""
def get_worklist_v2(modality=None, codigo_centro=None, campos=[], filtros_template=[], template_custom_path=None):
	
	# configuracion del worklist
	config_worklist = _config.worklist
	# configurar centro
	try:
		if codigo_centro:
			config_worklist = _config.worklist.centros[codigo_centro]
	except Exception as e:
		log.error(e)
	# configurar modality 
	if not modality:
		modality = config_worklist.modality	
		
	# Si se usa un template personalizado entonces, configurarlo
	template = 'plantilla_query_wl'
	if template_custom_path:
		template = template_custom_path     
		
	#hacer la llamada de worklist segun la liberia que se use
	if config_worklist.lib == 'DCMTK':
		import endosys.lib.pydcmtk.pydcmtk
		import endosys.lib.dicom.dcmtk
		if modality: # esto no se tendria que poner aca, pero se deja para no testear bien como funciona el modality
			filtros_template.append({'clase': kModality, 'clase_padre': kScheduledProcedureStepSequence,'valor': modality})
		worklist = endosys.lib.dicom.dcmtk.obtenerWorkList_v2(config_worklist, campos, filtros_template, template)
		
	elif config_worklist.lib == 'DCM4CHE': # No implementado ----------
		import endosys.lib.dicom.dcm4che
		error_str = u'No implementado'
		log.error(error_str)
		raise Exception(error_str)
	else:
		error_str = u'La configuración de WORKLIST_LIB es incorrecta'
		log.error(error_str)
		raise Exception(error_str)
		
	return worklist
	
def get_worklist(date=None, modality=None, codigo_centro=None):
	"""
	Se conecta a un servidor de worklist y guarda en BBDD los works descargados.

	párametros:
		date:   tipo datetime. para filtrar por fecha. Si no se indica no se
				filtra por fecha (cuidado!). (de momento NO puede ser un str con
				formato dicom (YYYYMMDD))

		modality:   tipo str, para filtrar por modality. Si no se indica nada
					se utiliza la modality por defecto del ini (WORKLIST_MODALITY)

		codigo_centro: tipo str, indica el centro. En bbdd este identificador es la
				columna "codigo". Cada centro puede tener una config. de conexión
				DICOM distinta.

	devuelve un list de registros de la tabla Worklist (objetos Work)
	"""

	config_worklist = _config.worklist
	try:
		if codigo_centro:
			config_worklist = _config.worklist.centros[codigo_centro]
	except Exception as e:
		log.error(e)

	if not modality:
		modality = config_worklist.modality

	# obtener el worklist
	if config_worklist.lib == 'DCMTK':
		import endosys.lib.pydcmtk.pydcmtk
		import endosys.lib.dicom.dcmtk
		worklist = endosys.lib.dicom.dcmtk.obtenerWorkList(
						config_worklist.callingAE,
						config_worklist.calledAE,
						config_worklist.server,
						config_worklist.port,
						date,
						modality,
						(   endosys.lib.pydcmtk.pydcmtk.kAccessionNumber,
							endosys.lib.pydcmtk.pydcmtk.kPatientID,
							endosys.lib.pydcmtk.pydcmtk.kPatientName,
							endosys.lib.pydcmtk.pydcmtk.kPatientBirthDate,
							endosys.lib.pydcmtk.pydcmtk.kPatientSex,
							#endotools.lib.pydcmtk.pydcmtk.kPlacerOrderNumberImagingServiceRequest,  # XXX   es necesario?
	##						kScheduledProcedureStepStartDate,
	##						kScheduledProcedureStepStartTime,
	##						kScheduledProcedureStepDescription,
	##						kScheduledProcedureStepID,
							endosys.lib.pydcmtk.pydcmtk.kStudyInstanceUID),
						'plantilla_query_wl')
	elif config_worklist.lib == 'DCM4CHE':
		import endosys.lib.dicom.dcm4che
		worklist = endosys.lib.dicom.dcm4che.obtenerWorkList(
						config_worklist.callingAE,
						config_worklist.calledAE,
						config_worklist.server,
						config_worklist.port,
						date,
						modality)
	else:
		raise Exception(u'La configuración de WORKLIST_LIB es incorrecta')

	# guardar el worklist en BBDD (si ya existe lo actualiza con los nuevos datos.
	# los identifica por el accessionNumber)
	l = []
	for work in worklist:
		r = get_work(work.accessionNumber)
		if r:
			#   actualiza la fecha del worklist query
			r.date_queried = date
			#   actualiza los datos del paciente, que pueden haber cambiado
			r.patientID =				work.patientID
			r.patientName =				work.patientName
			r.patientBirthDate =		work.patientBirthDate
			r.patientSex =				work.patientSex
			#   actualiza los datos de la programación
			r.schProcStepStartDate =	work.scheduledProcedureStepStartDate
			r.schProcStepStartTime =	work.scheduledProcedureStepStartTime
			r.studyInstanceUID =		work.studyInstanceUID
			r.schProcStepDescription =	work.scheduledProcedureStepDescription
			r.schProcStepID =			work.scheduledProcedureStepID
			r.reqPhysician =			work.requestingPhysician
			r.reqService =				work.requestingService
			r.refPhysicianName =		work.referringPhysiciansName
			r.placerOrderNumber =		work.placerOrderNumberImagingServiceRequest
			r.schProcStepLoc = 			work.scheduledProcedureStepLocation
			r.reqProcedureDesc =		work.requestedProcedureDescription
			r.schStationAETitle =		work.scheduledStationAETitle
			r.admissionID =				work.admissionID
			r.modality =				work.modality
			meta.Session.update(r)
			meta.Session.commit()
		else:
			r = endosys.model.worklist.Work()
			r.date_queried = date
			r.cita_id = None
			r.exploracion_id = None
			r.accessionNumber =			work.accessionNumber
			r.patientID =				work.patientID
			r.patientName =				work.patientName
			r.patientBirthDate =		work.patientBirthDate
			r.patientSex =				work.patientSex
			r.schProcStepStartDate =	work.scheduledProcedureStepStartDate
			r.schProcStepStartTime =	work.scheduledProcedureStepStartTime
			r.studyInstanceUID =		work.studyInstanceUID
			r.schProcStepDescription =	work.scheduledProcedureStepDescription
			r.schProcStepID =			work.scheduledProcedureStepID
			r.reqPhysician =			work.requestingPhysician
			r.reqService =				work.requestingService
			r.refPhysicianName =		work.referringPhysiciansName
			r.placerOrderNumber =		work.placerOrderNumberImagingServiceRequest
			r.schProcStepLoc = 			work.scheduledProcedureStepLocation
			r.reqProcedureDesc =		work.requestedProcedureDescription
			r.schStationAETitle =		work.scheduledStationAETitle
			r.admissionID =				work.admissionID
			r.modality =				work.modality
			meta.Session.save(r)
			meta.Session.commit()
		l.append(r)

	return l


def update_work(workid, **kwargs):
	"""
	añade información extra a un work del worklist (que ya estará en BBDD).
	puede ser un cita_id o exploracion_id.

	parámetros:
		workid:	 el identificador del work (accessionNumber). tambien puede
					ser un objeto model.worklist.Work
		kwargs:	 puede ser cita_id y exploracion_id. pueden
					tener el valor None

	devuelve el work (model.worklist.Work)
	"""
	if isinstance(workid, endosys.model.worklist.Work):
		w = workid
	else:
		w = endosys.model.worklist.get_work(accessionNumber=workid)
	if w:
		if 'cita_id' in kwargs:
			w.cita_id = kwargs['cita_id']
		if 'exploracion_id' in kwargs:
			w.cita_id = kwargs['exploracion_id']
		meta.Session.update(w)
		meta.Session.commit()
	return w


def get_work(workid):
	"""
	obtiene un work del worklist(de BBDD). devuelve el objeto del registro de la
	tabla o None si no existe.

	parámetros:
		workid:	 el identificador del work (accessionNumber)
	"""
	return endosys.model.worklist.get_work(accessionNumber=workid)


# PACS (STORE) ################################
# en este caso si que se vincula directamente a las exploraciones/capturas,
# ya que en principio siempre funcionará igual (envío de imágenes al PACS al
# finalizar una exploración).
# esta funcionalidad está integrada directamente en endoTools Web, y se puede
# activar/desactivar desde el .ini

class PACS:

	@staticmethod
	def _dicomize_image():
		"""
		dicomiza una imagen para poderla enviar al PACS
		"""
		pass

	@staticmethod
	def _store_image():
		"""
		envia una imagen al PACS mediante DICOM Store
		"""
		pass

	@staticmethod
	def store(exploracion):
		"""
		envía las imágenes de una exploración al PACS.
			-obtener datos para dicomizar
			-dicomizar las imágenes
			-enviar las imágenes al PACS
		"""
		pass

	@staticmethod
	def get_store_enabled():
		return _config.store.enabled


#   inicializar el modulo standard de DICOM.

#	   comprobar si está habilitado
#xxx


#	leer la configuracion de conexion del ini
#	   configuración genérica. Se utiliza si no hay configuración específica
#	   para un centro.
class _config:
	class worklist:
		lib =			config.get('WORKLIST_LIB', 'dcmtk').upper() # DCMTK o DCM4CHE
		callingAE =		config.get('WORKLIST_CALLING_AE', '')
		calledAE =		config.get('WORKLIST_CALLED_AE', '')
		server =		config.get('WORKLIST_SERVER', '')
		port =			config.get('WORKLIST_PORT', '')
		modality =		config.get('WORKLIST_MODALITY', '')
		centros =		{}
	class store:
		enabled =		config.get('PACS_STORE', '0');
		enabled =		bool(int(enabled)) if isint(enabled) else False
		callingAE =		config.get('PACS_CALLING_AE', '')
		calledAE =		config.get('PACS_CALLED_AE', '')
		server =		config.get('PACS_SERVER', '')
		port =			config.get('PACS_PORT', '')
	class retrieve:	 #   xxx ahora coge los mismos parametros que para el store.
						#   podria darse el caso de que use unos distintos
		callingAE =		config.get('PACS_CALLING_AE', '')
		calledAE =		config.get('PACS_CALLED_AE', '')
		server =		config.get('PACS_SERVER', '')
		port =			config.get('PACS_PORT', '')
		portmove =		config.get('PACS_PORTMOVE', '')

# aumentar la configuracion de worklist para varios centros. Si se define
# una configuración para un centro, tiene preferencia sobre la genérica.
"""
try:
	import endotools.lib.misc
	from endotools.lib.organizacion_centros import get_centros
	for centro in get_centros():
		r = endotools.lib.misc.record()
		r.lib =			_config.worklist.lib # la LIB es general, no por centro
		r.callingAE =	config.get('WORKLIST.%s.CALLING_AE' % centro.codigo, None)
		r.calledAE =	config.get('WORKLIST.%s.CALLED_AE' % centro.codigo, None)
		r.server =		config.get('WORKLIST.%s.SERVER' % centro.codigo,	None)
		r.port =		config.get('WORKLIST.%s.PORT' % centro.codigo,		None)
		r.modality =	config.get('WORKLIST.%s.MODALITY' % centro.codigo,	None)
		_config.worklist.centros[centro.codigo] = r
except Exception as e:
	log.error(e)
"""
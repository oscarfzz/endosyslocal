"""
Utilidades de acceso por dicom, mediante dcmtk.
"""
##  el nombre correcto de un registro del worklist puede ser "worklist item" o "task"
import logging
import sys
from os import path
from time import strptime
from datetime import date, time, datetime
from endosys.lib.pydcmtk.pydcmtk import *
import endosys.lib.dicom.util
try:
    import Image
except ImportError:
    from PIL import Image
log = logging.getLogger(__name__)
appPath = path.join(sys.path[0], 'endosys', 'lib', 'pydcmtk')
dcmConfig.binPath = path.join(appPath, 'dicom', 'bin') + '\\'
dcmConfig.tempPath = path.join(appPath, 'dicom', 'temp') + '\\'
dcmConfig.showExecute = '1'
SetLogDir(path.join(sys.path[0],"logs","dcmdll"))

import threading
worklist_lock = threading.Lock()

class WLWork(object):
	"""
	Son los objetos devueltos por obtenerWorkList().

	representa un item del worklist devuelto.

	XXX se podria definir en lib.dicom.util, y hacer una subclase...
	"""

	def __init__(self, dataset):
		self.patientName = None
		self.patientID = None
		self.patientBirthDate = None
		self.patientSex = None
		self.accessionNumber = None
		self.studyInstanceUID = None
		self.scheduledProcedureStepStartDate = None
		self.scheduledProcedureStepStartTime = None
		self.scheduledProcedureStepID = None
		self.scheduledProcedureStepDescription = None
		self.referringPhysiciansName = None
		self.requestingPhysician = None
		self.requestingService = None
		self.placerOrderNumberImagingServiceRequest = None
		self.requestedProcedureDescription = None
		self.scheduledStationAETitle = None
		self.scheduledProcedureStepLocation = None
		self.admissionID = None
		self.modality = None
		
		# inicializar a partir de un dataset
		if dataset:
			#   PatientName
			self.patientName = dataset.datasetValues[kPatientName] or None				  #   nombre y apellidos
			self.patientID = dataset.datasetValues[kPatientID] or None					  #   nhc
			self.patientBirthDate = dataset.datasetValues[kPatientBirthDate] or None		#   fecha de nacimiento
			self.patientSex = dataset.datasetValues[kPatientSex] or None					#   sexo
			self.accessionNumber = dataset.datasetValues[kAccessionNumber] or None		  #   "accession number" (identificador de la cita)
			self.studyInstanceUID = dataset.datasetValues[kStudyInstanceUID] or None		#   StudyInstanceUID

			self.referringPhysiciansName = dataset.datasetValues[kReferringPhysiciansName] or None	#   ...?
			self.requestingPhysician = dataset.datasetValues[kRequestingPhysician] or None			#   médico peticionario
			self.requestingService = dataset.datasetValues[kRequestingService] or None		   	#   servicio peticionario?
			self.requestedProcedureDescription = dataset.datasetValues[kRequestedProcedureDescription] or None
			self.admissionID = dataset.datasetValues[kAdmissionID] or None
			
			
			# valores dentro de ScheduledProcedureStepSequence
			n = dataset.getSequenceItem(kScheduledProcedureStepSequence)

			s = GetValueFromNode_firstchild(n, kScheduledProcedureStepStartDate)
			self.scheduledProcedureStepStartDate = s or None  #   fecha de la cita
			#t = strptime(s, "%Y%m%d")
			#c.fecha = date(t.tm_year, t.tm_mon, t.tm_mday)
			s = GetValueFromNode_firstchild(n, kScheduledProcedureStepStartTime)
			self.scheduledProcedureStepStartTime = s or None  #   hora de la cita
			#t = strptime(s, "%H%M%S")
			#c.hora = time(t.tm_hour, t.tm_min, t.tm_sec)

			# prestacion
			s = GetValueFromNode_firstchild(n, kScheduledProcedureStepID)
			self.scheduledProcedureStepID = s or None					#   ScheduledProcedureStepID
			s = GetValueFromNode_firstchild(n, kScheduledProcedureStepDescription)
			self.scheduledProcedureStepDescription = s or None	#   ScheduledProcedureStepDescription

			s = GetValueFromNode_firstchild(n, kScheduledProcedureStepLocation)
			self.scheduledProcedureStepLocation = s or None
			
			s = GetValueFromNode_firstchild(n, kScheduledStationAETitle)
			self.scheduledStationAETitle = s or None
			
			s = GetValueFromNode_firstchild(n, kModality)
			self.modality = s or None
			
			# order number (por si luego se ha de generar un ORU...)
			# (Probablemente el HIS se lo haya pasado al RIS, que lo incluye en el Woorklist en este campo)
			# Lo cojo de "fuera" del ScheduledProcedureStepSequence... no sé si es lo correcto
			# o es que el cliente (HUCA: AGFA) lo está haciendo mal.
			# s = GetValueFromNode_firstchild(n, kPlacerOrderNumberImagingServiceRequest)
			# self.placerOrderNumberImagingServiceRequest = s or None		#   PlacerOrderNumberImagingServiceRequest... el Order Number.
			self.placerOrderNumberImagingServiceRequest = dataset.datasetValues[kPlacerOrderNumberImagingServiceRequest] or None		#   PlacerOrderNumberImagingServiceRequest... el Order Number.

			# XXX
			# quedaria pendiente extraer (si es posible): el tipo de exploracion, la sala y el medico

			# prestacion
			# self.scheduledProcedureStepID = dataset.datasetValues[kScheduledProcedureStepID] or None					#   ScheduledProcedureStepID
			# self.scheduledProcedureStepDescription = dataset.datasetValues[kScheduledProcedureStepDescription] or None	#   ScheduledProcedureStepDescription


	def __str__(self):
		s = super(WLWork, self).__str__() + '\n'
		for k in self.__dict__:
			s += '\t' + k + '=' + str(self.__dict__[k]) + '\n'
		return s


def obtenerWorkList(callingAE, calledAE, server, port, fecha, modality, campos=None, nombre_plantilla=None):
	"""
	utilizando dcmtk

	se conecta al worklist mediante DICOM y obtiene las tasks, filtrando por fecha.

	parametros:
		callingAE, calledAE, server, port:
				config de conexión al servidor de worklist
		fecha:  La fecha de la que se quiere obtener el worklist.
				Puede ser de tipo datetime.date o str. Si es str tiene que ser con el formato "YYYYMMDD"
		campos: list de constantes indicando los campos que se quieren obtener (XXX documentar mejor)

	devuelve un list de WLWorks

	importante:
		caso multihilo: tener en cuenta que se crea un archivo .dcm de la plantilla
	"""
	global worklist_lock
	worklist_lock.acquire()
	try:
		log.debug('Ejecutar obtenerWorkList...');
		log.debug('parametro "fecha": ' + str(fecha) + ' (' + str(type(fecha)) + ')');
		log.debug('parametro "modality": ' + str(modality) + ' (' + str(type(modality)) + ')');
		log.debug('parametro "campos": ' + str(campos));
		log.debug('parametro "nombre_plantilla": ' + str(nombre_plantilla));

		dataSetList = None

		if not nombre_plantilla: nombre_plantilla = 'plantilla_query_wl'
		if not campos: campos = (kPatientName, kPatientID)

		dataset = DcmDataSet()
		try:
			dataset.loadFromFile(path.join(appPath, 'dicom', 'data', nombre_plantilla + '.xml'))
			#   filtrar por modality
			if modality:
	##			dataset.datasetValues[kModality] = modality
				n = dataset.getSequenceItem(kScheduledProcedureStepSequence)
				SetValueToNode_firstchild(n, kModality, modality)
			#   y por fecha
			if fecha:
				if isinstance(fecha, date): fecha = endosys.lib.dicom.util.date_to_DICOM(fecha)	#   si la fecha es tipo datetime.date, parsear como str
				n = dataset.getSequenceItem(kScheduledProcedureStepSequence)
				SetValueToNode_firstchild(n, kScheduledProcedureStepStartDate, fecha)
				
			dataset.saveToFileDCM(path.join(appPath, 'dicom', 'data', nombre_plantilla + '.dcm'))
			
			
		finally:
			dataset.free()

		# configurar
		log.debug(u'configuración: calling AE: %s, called AE: %s, server: %s, port: %s' % (callingAE, calledAE, server, port));
		dcmConfig.CallingAE = callingAE
		dcmConfig.CalledAE = calledAE
		dcmConfig.Server = server
		dcmConfig.Port = port

		dcmfile = path.join(appPath, 'dicom', 'data', nombre_plantilla + '.dcm')
		log.debug("campos: " + str(campos));
		log.debug("dcmQuery(imWorklist, '', <campos>, '" + str(dcmfile) + "')");
		dataSetList = dcmQuery(imWorklist, '', [(c, '') for c in campos], dcmfile)

		if dataSetList is None:
			log.debug('No se ha obtenido ningun item');
			return []

		# TODO estaria bien implementar DcmDataSetList como un iterable
		# XXX quitar prints
		tasks = []
		log.debug('total items obtenidos de worklist: ' + str(dataSetList.dataSetCount));
		for i in range(dataSetList.dataSetCount):
			dataset = dataSetList.getDataSet(i)
			w = WLWork(dataset)
			log.debug(str(w))
			tasks.append(w)
		if dataSetList:
			dataSetList.free()

		return tasks
	finally:
		worklist_lock.release()

'''
	----------------------
	VERSION 2 del WORKLIST
	----------------------
'''
		
class WLWork_v2(object):
	"""
	Son los objetos devueltos por obtenerWorkList().
	representa un item del worklist devuelto.
	"""
	
	def __init__(self, dataset):
		self.patientName = None
		self.patientID = None
		self.patientBirthDate = None
		self.patientSex = None
		self.accessionNumber = None
		self.studyInstanceUID = None
		self.modality = None
		self.scheduledProcedureStepStartDate = None
		self.scheduledProcedureStepStartTime = None
		self.scheduledProcedureStepID = None
		self.scheduledProcedureStepDescription = None
		self.referringPhysiciansName = None
		self.requestingPhysician = None
		self.requestingService = None
		self.requestedProcedureID = None
		self.requestedProcedureDescription = None
		self.placerOrderNumberImagingServiceRequest = None

		# inicializar a partir de un dataset
		if dataset:
			
			self.patientName = dataset.datasetValues[kPatientName] or None				  #   nombre y apellidos
			self.patientID = dataset.datasetValues[kPatientID] or None					  #   nhc
			self.patientBirthDate = dataset.datasetValues[kPatientBirthDate] or None		#   fecha de nacimiento
			self.patientSex = dataset.datasetValues[kPatientSex] or None					#   sexo
			self.accessionNumber = dataset.datasetValues[kAccessionNumber] or None		  #   "accession number" (identificador de la cita)
			self.studyInstanceUID = dataset.datasetValues[kStudyInstanceUID] or None		#   StudyInstanceUID
			self.referringPhysiciansName = dataset.datasetValues[kReferringPhysiciansName] or None	#   ...?
			self.requestingPhysician = dataset.datasetValues[kRequestingPhysician] or None			#   médico peticionario
			self.requestingService = dataset.datasetValues[kRequestingService] or None		   	#   servicio peticionario?
			self.requestedProcedureID = dataset.datasetValues[kRequestedProcedureID] or None	#  prestacion, si viene afuera del schedule
			self.requestedProcedureDescription = dataset.datasetValues[kRequestedProcedureDescription] or None	#  prestacion, si viene afuera del schedule
			self.placerOrderNumberImagingServiceRequest = dataset.datasetValues[kPlacerOrderNumberImagingServiceRequest] or None #   PlacerOrderNumberImagingServiceRequest... el Order Number.
			
			# valores dentro de ScheduledProcedureStepSequence
			n = dataset.getSequenceItem(kScheduledProcedureStepSequence)
			s = GetValueFromNode_firstchild(n, kScheduledProcedureStepStartDate)
			self.scheduledProcedureStepStartDate = s or None  #   fecha de la cita
			s = GetValueFromNode_firstchild(n, kScheduledProcedureStepStartTime)
			self.scheduledProcedureStepStartTime = s or None  #   hora de la cita
			s = GetValueFromNode_firstchild(n, kScheduledProcedureStepID)
			self.scheduledProcedureStepID = s or None					#   ScheduledProcedureStepID
			s = GetValueFromNode_firstchild(n, kScheduledProcedureStepDescription)
			self.scheduledProcedureStepDescription = s or None	#   ScheduledProcedureStepDescription
			s = GetValueFromNode_firstchild(n, kModality)
			self.modality = s or None	#   modality
					

	def __str__(self):
		s = super(WLWork_v2, self).__str__() + '\n'
		for k in self.__dict__:
			s += '\t' + k + '=' + str(self.__dict__[k]) + '\n'
		return s
		
		
'''
	Nueva version de obtenerWorkList
	--------------------------------
	config: los parametros de configuracion
	campos_cmdline:  [ {clase: kPatientName, valor: 'valor_ejemplo'}, ... ]
	filtros: [ {clase: kModality, clase_padre: kScheduledProcedureStepSequence, valor: 'VL',}]
'''
def obtenerWorkList_v2( config, campos_cmdline=[], filtros=[], template='plantilla_query_wl'):
	global worklist_lock
	worklist_lock.acquire()
	
	# configura la ruta del template
	if template[-3:] != "xml": # se usa el por defecto, construyo la ruta
		template = path.join(appPath, 'dicom', 'data', template + '.xml')
	if not path.exists(template):
		error_str = "WORKLIST: la plantilla " + template + " no existe"
		log.error(error_str)
		raise Exception(error_str)
	
	# configura el nombre que va a tener la plantilla .dcm
	now_time = datetime.now().strftime("%Y%m%d%H%M%S%f")
	template_dcm = path.join(appPath, 'dicom', 'data', now_time + '.dcm')
	
	
	try:
		dataSetList = None
		
		dataset = DcmDataSet()
		try:
			dataset.loadFromFile(template)
			
			# filtrar campos
			for campo in filtros:
				if isinstance(campo["valor"], date): campo["valor"] = endosys.lib.dicom.util.date_to_DICOM(campo["valor"])
				if "clase_padre" in campo:
					n = dataset.getSequenceItem(campo["clase_padre"])
					SetValueToNode_firstchild(n, campo["clase"], campo["valor"])
				else:
					dataset.datasetValues[campo["clase"]] = campo["valor"]
			
			# guardar dcm configurado
			dataset.saveToFileDCM(template_dcm)
		except Exception,e:
			log.error(str(e))
			raise Exception(str(e))
		finally:
			dataset.free()
		
		# configura los campos que se van a usar en la linea de comandos
		if campos_cmdline:
			campos_cmdline_list = []
			for campo in campos_cmdline:
				campos_cmdline_list.append((campo["clase"], campo["valor"]))
		else:	
			campos_cmdline = (kPatientName, kPatientID)
			campos_cmdline_list = [(c, '') for c in campos_cmdline]
		
		# configurar wl
		dcmConfig.CallingAE = config.callingAE
		dcmConfig.CalledAE = config.calledAE
		dcmConfig.Server = config.server
		dcmConfig.Port = config.port
		
		# hace el query al worklist
		#dataSetList = dcmQuery(imWorklist, '', campos_cmdline, template_dcm)
		dataSetList = dcmQuery(imWorklist, '', (), template_dcm)
		
		if dataSetList is None:
			log.debug('WORKLIST: No se ha obtenido ningun item');
			return []
			
		lista = []
		log.debug('WORKLIST: Total items obtenidos de worklist: ' + str(dataSetList.dataSetCount));
		for i in range(dataSetList.dataSetCount):
			dataset = dataSetList.getDataSet(i)
			w = WLWork_v2(dataset)
			lista.append(w)
		if dataSetList:
			dataSetList.free()
		return lista
	except Exception,e:
		log.error(str(e))
		raise Exception(str(e))
	finally:
		worklist_lock.release()

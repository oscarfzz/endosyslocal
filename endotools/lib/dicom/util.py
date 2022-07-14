"""
Utilidades de acceso por dicom. Utilizado por el modulo standard de DICOM. Opcionalmente,
para casos concretos de integracion se puede utilizar por un plugin, etc...

Son funciones genéricas, sin usar ni dcmtk ni dcm4che.
"""
##  el nombre correcto de un registro del worklist puede ser "worklist item" o "task"
import logging
import sys
from os import path
from time import strptime
from datetime import date, time, datetime
try:
    import Image
except ImportError:
    from PIL import Image

log = logging.getLogger(__name__)

class WLWork(object):
	"""
	Clase basica que representa un registro de un Worklist. Tanto la interfaz
	de dcmtk como la de dcm4che usan una subclase de ésta.

	"""
	def __init__(self):
		self.patientName =							None
		self.patientID =							None
		self.patientBirthDate =						None
		self.patientSex =							None
		self.accessionNumber =						None
		self.studyInstanceUID =						None
		self.scheduledProcedureStepStartDate =		None
		self.scheduledProcedureStepStartTime =		None
		self.scheduledProcedureStepID =				None
		self.scheduledProcedureStepDescription =	None
		self.referringPhysiciansName =				None
		self.requestingPhysician =					None
		self.requestingService =					None

	def __str__(self):
		s = super(WLWork, self).__str__() + '\n'
		for k in self.__dict__:
			s += '\t' + k + '=' + str(self.__dict__[k]) + '\n'
		return s


# Conversion de fechas y horas dicom <-> python

def DICOM_to_date(dicom_date):
	""" convierte una fecha en formato DICOM (string YYYYMMDD) a un fecha de tipo datetime.date """
	if not dicom_date: return None
##	log.debug('DICOM_to_date - ' + str(dicom_date))
	try:
		n = strptime(dicom_date, "%Y%m%d")
		return date(n.tm_year, n.tm_mon, n.tm_mday)
	except:
		return None


def date_to_DICOM(python_date):
	""" convierte una fecha de tipo datetime.date a un fecha en formato DICOM (string YYYYMMDD) """
	if not python_date: return ''
	return python_date.strftime("%Y%m%d")

def DICOM_to_time(dicom_time):
	""" convierte una hora en formato DICOM (string HHMMSS) a un hora de tipo datetime.time """
	if not dicom_time: return None
##	log.debug('DICOM_to_time - ' + str(dicom_time))
	dicom_time = dicom_time[:6]
	n = strptime(dicom_time, "%H%M%S")
	return time(n.tm_hour, n.tm_min, n.tm_sec)

def DICOM_to_datetime(dicom_date, dicom_time):
	""" convierte una fecha y hora en formato DICOM (string HHMMSS) a un fecha y hora de tipo datetime.datetime """
	if not dicom_date: return None
	if not dicom_time: return None
##	log.debug('DICOM_to_datetime - ' + str(dicom_date) + ' - ' + str(dicom_time))
	dicom_time = dicom_time[:6]
	n1 = strptime(dicom_date, "%Y%m%d")
	n2 = strptime(dicom_time, "%H%M%S")
	return datetime(n1.tm_year, n1.tm_mon, n1.tm_mday, n2.tm_hour, n2.tm_min, n2.tm_sec)

def time_to_DICOM(python_time):
	""" convierte una hora de tipo datetime.time a un fecha en formato DICOM (string HHMMSS) """
	if not python_time: return ''
	return python_time.strftime("%H%M%S")

def create_series_instance_uid(prefix="2.25.", num_digits = 39):
	"""
	2017a Part 5 - Data Structures and Encoding (B Creating a Privately Defined Unique Identifier (Informative))
	B.2 UUID Derived UID:
	UID may be constructed from the root "2.25." followed by a decimal representation of a Universally Unique Identifier (UUID).
	That decimal representation treats the 128 bit UUID as an integer, and may thus be up to 39 digits long (leading zeros must be suppressed).
	A UUID derived UID may be appropriate for dynamically created UIDs, such as SOP Instance UIDs, but is usually not appropriate 
	for UIDs determined during application software design, such as private SOP Class or Transfer Syntax UIDs, or Implementation Class UIDs.
	"""
	import random
	random_part = random.randint(int('1'+ '0'*(num_digits-1)),int('9'*(num_digits)))
	return prefix+str(random_part)
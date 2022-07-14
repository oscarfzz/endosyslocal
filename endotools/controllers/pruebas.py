import logging

import os
from endotools.lib.base import *
##import endotools.lib.dicom.thread
import endotools.lib.dicom.util
from endotools.lib.pydcmtk.pydcmtk import *
from pylons import config
from datetime import date

from endotools.lib.misc import *
import threading

from authkit.authorize.pylons_adaptors import authorize
from authkit.permissions import RemoteUser, ValidAuthKitUser, UserIn, HasAuthKitRole, And

log = logging.getLogger(__name__)

import threading
prueba_lock = threading.Lock()

# plantilla basica de html, que incluye jquery y permite poner un titulo,
# un script a ejecutar en el onReady, y el body.
_html_template = """
<html>
	<head>
		<title>%s</title>
		<script data-main="/web/" type="text/javascript" src="/lib/jquery/require-jquery.js"></script>
		<script type="text/javascript">
		$(function() {
			%s
		});
		</script>
	</head>
	<body>
		%s
	</body>
</html>
"""

class PruebasController(BaseController):

	@authorize(UserIn(['sysadmin']))
	def index(self):
		s = 'pruebas:<br>'
		s = s + '<a href="/pruebas/worklist">worklist</a><br>'
		s = s + 'pruebas/envia_imagen_pacs<br>'
		s = s + 'pruebas/obtiene_imagenes_pacs<br>'
		s = s + 'pruebas/obtiene_imagen_pacs<br>'
		s = s + '<a href="/pruebas/openoffice">OpenOffice</a><br>'
		s = s + '<a href="/pruebas/jpype">JPype</a><br>'
		s = s + '<a href="/pruebas/bloqueo">Bloqueo</a><br>'
		return s

	@authorize(UserIn(['sysadmin']))
	def procesar_imagen(self):
		endotools.lib.dicom.thread.procesar_imagen(
								os.path.join('C:\Proyectos\NUEVO ENDOTOOLS 2\proyecto Pylons\endotools\endotools\capturas',
											'142.bmp'),
								PatientName = 'juan',
								PatientID = '123',
								PatientBirthDate = '19951010',
								PatientSex = 'M',
								AccessionNumber = 'abc',
								StudyInstanceUID = '1.2.3.56546546.54654',
								StudyDate = '20091010',
								SeriesDate = '20091010',
								StudyTime = '1200',
								SeriesTime = '1200',
								Modality = 'VL',
							)

		return 'ok'

	@authorize(UserIn(['sysadmin']))
	def obtener_task_worklist(self):
		endotools.lib.dicom.thread._crear_tabla_Worklist_Tasks()
		endotools.lib.dicom.thread.obtener_task_worklist(36, '1', None)
		return 'ok'


	@authorize(UserIn(['sysadmin']))
	def obtiene_imagenes_pacs(self):
		# url de ejemplo:
		# http://localhost:8080/pruebas/obtiene_imagenes_pacs?StudyInstanceUID=1.2.826.0.1.3680043.8.272.1.4.1163419975.5488.1247574973.1&SeriesInstanceUID=1.2.826.0.1.3680043.8.272.1.3.1163419975.5288.1247576698.1

		if len(request.params) == 0:
			s = 'ejemplo:<br><code>'
			s = s + 'pruebas/obtiene_imagenes_pacs?StudyInstanceUID=xxx&SeriesInstanceUID=xxx'
			s = s + '</code>'
			return s

		StudyInstanceUID = str( request.params['StudyInstanceUID'] )
		SeriesInstanceUID = str( request.params['SeriesInstanceUID'] )
		dcmConfig.CallingAE = config.get('PACS_CALLING_AE', '')
		dcmConfig.CalledAE = config.get('PACS_CALLED_AE', '')
		dcmConfig.Server = config.get('PACS_SERVER', '')
		dcmConfig.Port = config.get('PACS_PORT', '')

		# XXX poner en una funcion dentro de dicom.util
		# XXX se ha de poder obtener todas las imagenes de un estudio (primero consultar las series del estudio y luego de cada uno, las imagenes)
		params = []
		params.append( (kStudyInstanceUID, StudyInstanceUID) )
		params.append( (kSeriesInstanceUID, SeriesInstanceUID) )
		params.append( (kTransferSyntaxUID, '') )
		params.append( (kSOPInstanceUID, '') )
		dataSetList = dcmQuery(imStudy, 'IMAGE', params, '')

		resultado = '<p>Total: %s</p>' % dataSetList.dataSetCount
		for i in range(dataSetList.dataSetCount):
			dataset = dataSetList.getDataSet(i)
			resultado += '<p>SOPInstanceUID: %s</p>' % dataset.datasetValues[kSOPInstanceUID]
##			dataset.datasetValues[kTransferSyntaxUID]

		return resultado


##	@authorize(UserIn(['sysadmin']))
##	def obtiene_imagen_pacs(self):
##		# url de ejemplo:
##		# http://localhost:8080/pruebas/obtiene_imagen_pacs?archivo_salida=c:\prueba\imagen.dcm&StudyInstanceUID=1.2.826.0.1.3680043.8.272.1.4.1163419975.5488.1247574973.1&SeriesInstanceUID=1.2.826.0.1.3680043.8.272.1.3.1163419975.5288.1247576698.1&SOPInstanceUID=1.2.826.0.1.3680043.8.272.1.4.1163419975.4340.1247576697.1
##
##		if len(request.params) == 0:
##			s = 'ejemplo:<br><code>'
##			s = s + 'pruebas/obtiene_imagen_pacs?archivo_salida=c:\prueba\imagen.dcm&StudyInstanceUID=xxx&SeriesInstanceUID=xxx&SOPInstanceUID=xxx'
##			s = s + '</code>'
##			return s
##
##		archivo_salida = str(request.params['archivo_salida'])
##		StudyInstanceUID = str( request.params['StudyInstanceUID'] )
##		SeriesInstanceUID = str( request.params['SeriesInstanceUID'] )
##		SOPInstanceUID = str( request.params['SOPInstanceUID'] )
##		dcmConfig.CallingAE = config.get('PACS_CALLING_AE', '')
##		dcmConfig.CalledAE = config.get('PACS_CALLED_AE', '')
##		dcmConfig.Server = config.get('PACS_SERVER', '')
##		dcmConfig.Port = config.get('PACS_PORT', '')
##		dcmConfig.PortMove = config.get('PACS_PORTMOVE', '6000')
##		endotools.lib.dicom.util.Retrieve_DCM(StudyInstanceUID, SeriesInstanceUID, SOPInstanceUID, archivo_salida)
##		return "ok"


	@authorize(UserIn(['sysadmin']))
	def genuid(self):
		uid_type = request.params.get('uid_type', utInstance)
		root_uid = request.params.get('root_uid', MedConn_Root_UID)
		return dcmGenUID(uid_type, root_uid)


	@authorize(UserIn(['sysadmin']))
	def upload_file_multipart(self):
		params = request.environ['webob._parsed_post_vars'][0]
		for k in params: log.debug(k)
		fieldstorage = params['archivo']

		permanent_file = open(os.path.join( 'c:\\', os.path.basename(fieldstorage.filename) ), 'wb')

		import shutil
		shutil.copyfileobj(fieldstorage.file, permanent_file)
		fieldstorage.file.close()
		permanent_file.close()

		return 'ok'


	@authorize(UserIn(['sysadmin']))
	def upload_file(self):
		""" sube un fichero directamente, sin ser multipart/form-data """
		log.debug(request.environ['CONTENT_TYPE'])
		permanent_file = open(os.path.join('c:\\', 'prueba.bmp'), 'wb')

		import shutil
		shutil.copyfileobj(request.environ['wsgi.input'], permanent_file)
		permanent_file.close()

		return 'ok'


	@authorize(UserIn(['sysadmin']))
	def test_upload_file_multipart(self):
##		s = """<form method='POST' enctype='multipart/form-data' action='/pruebas/upload_file_multipart'>
		s = """<form method='POST' enctype='multipart/form-data' action='/rest/capturas'>
				File to upload: <input type=file name=archivo><br>
				estudio_id: <input type=text name=estudio_id><br>
				<br>
				<input type=submit value=Press> to upload the file!
				</form>"""
		s = '<html><body>%s</body></html>' % s
		return s


	@authorize(UserIn(['sysadmin']))
	def prueba(self):
		return h.url_for(controller='rest/capturas', action='show', id=1, format='jpg')


	#   PRUEBA OPENOFFICE
	@authorize(UserIn(['sysadmin']))
	def openoffice(self):
		"""
		mas info:
        http://www.openoffice.org/udk/common/man/tutorial/office_automation.html
		"""
		title = 'Endosys App - Prueba de Automatización OLE de OpenOffice'
		readyscript = """
			$('#abrirdocumento').click(function(e) {
				$.ajax({
					type: 'POST',
					url: '/pruebas/openoffice_abrirdocumento',
					data: 'documento=' + $('#documento').val(),
					processData: false,
					contentType: 'application/x-www-form-urlencoded; charset=UTF-8',
					success: function(data) {
						$('#output').html(data);
					},
					error: function(data) {
						alert('ERROR');
					}
				});

				return false;
			});
		"""
		body = """
			<h1>Prueba de Automatización OLE de OpenOffice</h1>
			<p>Estas pruebas consisten en controlar OpenOffice mediante automatización
			OLE en el servidor de Endosys App. Debe estar instalado OpenOffice.
			La mayoría de pruebas tiene resultados solo visibles en el servidor.</p>
			<div>
			<p>Abrir un documento</p>
			<label for="documento">documento</label><input type="text" id="documento">
			<button id="abrirdocumento">Abrir</button>
			</div>
			<div>
				<textarea id="output" rows=10 cols=50></textarea>
			</div>
		"""
		return _html_template % (title, readyscript, body)


	@authorize(UserIn(['sysadmin']))
	def openoffice_abrirdocumento(self):
		"""
		el parametro "documento" debe ir con barras /, p.e.: "C:/prueba/archivo.odt"
		"""
		documento = request.params.get('documento', None)
		if not documento:
			abort_xml(400, 'No se ha indicado un documento')
		import pythoncom
		import win32com.client as win32

		pythoncom.CoInitialize()
		try:
			# Service Manager es un objeto OLE de OpenOffice, que hace de interfaz
			# con el API de OpenOffice "UNO".
			service_manager = win32.Dispatch("com.sun.star.ServiceManager")
			# para poder obtener structs que luego se han de pasar como parametros, se usa
			# una funcion especial "service_manager.Bridge_GetStruct()", y que antes
			#   http://forum.openoffice.org/en/forum/viewtopic.php?f=45&t=13125
			#   http://forum.openoffice.org/en/forum/viewtopic.php?f=44&t=33951&p=155727&hilit=createStruct#p155727
			# se tiene que inicializar de esta manera:
			service_manager._FlagAsMethod("Bridge_GetStruct")
			# crear objeto Desktop
			desktop = service_manager.createInstance("com.sun.star.frame.Desktop")
			# abrir un documento
			doc = desktop.loadComponentFromURL("file:///%s" % documento, "_blank", 0, [])

			# PRUEBA:
##			# Create a text object
##			text = doc.getText()
##			# Create a cursor object
##			cursor = text.createTextCursor()
##			# Inserting some Text
##			text.insertString(cursor, "The first line in the newly created text document.", False)

			# Guardar
##			doc.store()
##			doc.storeAsURL("file:///%s" % documento, [])
##			doc.storeAsURL("file:///%s" % (os.path.splitext(documento)[0] + '.PDF'), [])

##			valor
			propertyvalue = service_manager.Bridge_GetStruct("com.sun.star.beans.PropertyValue")
			propertyvalue.Name = "FilterName"
			#propertyvalue.Value = "MS Word 97"  # formato .DOC
			propertyvalue.Value = "writer_pdf_Export"   # formato .PDF
			storeProps = [propertyvalue]

#			doc.storeAsURL("file:///%s" % documento, storeProps)
#			doc.storeAsURL("file:///%s" % (os.path.splitext(documento)[0] + '.PDF'), storeProps)
			doc.storeToURL("file:///%s" % (os.path.splitext(documento)[0] + '.PDF'), storeProps)

		finally:
			pythoncom.CoUninitialize()

		return 'ok'


	@authorize(UserIn(['sysadmin']))
	def jpype(self):
		import jpype
		jvmPath = jpype.getDefaultJVMPath()
		jpype.startJVM(jvmPath)

		if not jpype.isThreadAttachedToJVM():
			jpype.attachThreadToJVM()

		JInteger = jpype.java.lang.Integer
		s = '<html><head/><body>'
		s = s + 'JInteger: ' + str(JInteger) + '<br>'
		int5 = JInteger(5)
		s = s + 'int5: ' + str(int5) + '<br>'
		s = s + 'type(int5.value): ' + str(type(int5.value)) + '<br>'
		s = s + 'int5.value: ' + str(int5.value) + '<br>'
		int8 = JInteger(8)
		s = s + 'int8: ' + str(int8) + '<br>'
		suma = int5.value + int8.value
		s = s + 'suma: ' + str(suma) + '<br>'
		s = s + '</body></html>'

##		jpype.java.lang.System.gc() # sugiere al garbage collector de Jaa que haga limpieza...

##		jpype.shutdownJVM()
		return s


	@authorize(UserIn(['sysadmin']))
	def bloqueo(self):
		"""
		Se trata de un simular un controlador que solo se puede ejecutar por
		un cliente a la vez. Si otro intenta hacer una petición, se espera
		a que termine el anterior.
		"""
		import time
		global prueba_lock
		log.debug(u'entra en bloqueo...')
		prueba_lock.acquire()
		log.debug(u'lock adquirido, esperar 5 segundos...')
		time.sleep(5)
		log.debug(u'ya está, lock liberado.')
		prueba_lock.release()

		return 'ok'


"""
INFORMACIÓN INTERESANTE, COM-OPENOFFICE:

http://www.openoffice.org/api/basic/man/tutorial/tutorial.pdf
http://www.openoffice.org/udk/common/man/tutorial/office_automation.html
http://www.openoffice.org/api/docs/common/ref/com/sun/star/frame/XStorable.html#storeAsURL
http://wiki.openoffice.org/wiki/Documentation/DevGuide/Text/Saving_Text_Documents

Extracto de una web ya no disponible:

	I used ADO 2.5 in my last Python project, and had no problems at all.
	Most of the time, ADO access in VB translates almost directly to python
	syntax. Features of ADO I used with no problem include parameterized
	commands, batch updating and client side cursors.

	One thing to keep in mind is the way pythoncom handles out-parameters of
	method calls: These values are returned as part of the method result,
	e.g the Execute method of the Connection object returns a tuple
	consisting of an RecordSet object and the RecordsAffected value (see
	MSDN):

	    recordset, affected = db_connect.Execute("select * from ...")

	In VB you would only get the recordset returned and RecordsAffected
	would get stuffed in a reference parameter of the call.

	Another point is handling of date values: They are returned as objects
	with type pywintypes.TimeType. The documentation for this type is very
	terse, and I had to dig into the pythoncom demos to find their
	interface: One useful method is Format(<formatstring>), which will
	return a string from TimeType:

	    import pywintypes
	    if type(x) == pywintypes.TimeType:
	        return x.Format("%d.%m.%Y")

	For more information on COM and Python I recommend Mark Hammond's
	"Python Programming on Win32" (which covers almost the entire COM body,
	albeit sometimes not too deeply: "Advanced Python Programming..." ?),
	which has a chapter on database programming.

"""
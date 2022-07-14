"""
XXX OJO: Controlar el hecho de que el programa MS Word podría estar abierto y en
uso en el equipo. Esto podría ocasionar por ejemplo que se cierre un documento
que el usuario estaba editando sin guardar los cambios, o que si de alguna forma
el programa está bloqueado (p.e. un dialogo que tiene abierto el usuario) no se
pueda generar el informe...
Se podría estudiar la opción de crear una instancia exclusiva para uso de
EndoTools, que no interfiera con la posible aplicación abierta por un usuario.

NOTA: Ya se controla, si hay algún otro documento abierto sin guardar no se cierra Word

información:
	Controlar MS Word desde Python:
    http://www.galalaly.me/index.php/2011/09/use-python-to-parse-microsoft-word-documents-using-pywin32-library/

	regex en MS Word:
    http://office.microsoft.com/en-us/support/add-power-to-word-searches-with-regular-expressions-HA001087305.aspx

	Tutorial API MS Word:
	http://msdn.microsoft.com/en-us/library/office/aa192495(v=office.11).aspx#wordobject_link8

	Referencia de API de MS Word:
    http://msdn.microsoft.com/en-us/library/bb244515(v=office.12).aspx

BUGS:
	Si la plantilla está abierta, y se están mostrando los códigos de campo
	de las imágenes, si se ejecuta la generación de un informe hace que se sustituyan
	los ${imagen_N} por "NO DEFINIDO"... SOLUCION: Desactivar al principio del
	proceso el mostrar códigos de campo.

	De momento no funcionan las imagenes en Shapes (en InlineShapes/Fields sí),
	parece un bug de word ya que lanza una excepcion al llamar a linkformat.Update().

IMPORTANTE: USAR MARCOS (FRAMES)!!! para meter dentro imágenes, en vez de TextBoxes.
			Están bastante escondidos dentro de Word.
			Ver: http://www.office-archive.com/8-microsoft-office/eea3a8c99c86dede.htm
"""

import os
from pylons import config
import pythoncom
import win32com.client as win32
from valores import get_valores, construir_objeto_exploracion_test, get_no_definido_value
import logging
##import re

log = logging.getLogger(__name__)

# CONSTANTES

#	WdExportFormat Enumeration
wdExportFormatPDF =		17
wdExportFormatXPS =		18

#	WdSaveOptions Enumeration
wdDoNotSaveChanges =	 0	# Do not save pending changes.
wdPromptToSaveChanges = -2  # Prompt the user to save pending changes.
wdSaveChanges =         -1  # Save pending changes automatically without prompting the user.

#   WdFieldType Enumeration
wdFieldIncludePicture = 67  # Fields de tipo INCLUDEPICTURE

#   msoShapeType Enumeration (ver http://msdn.microsoft.com/en-us/library/office/aa432678(v=office.12).aspx)
msoTextBox =            17  # un cuadro de texto
msoLinkedPicture =      11  # Linked Picture (imágenes tipo INCLUDEPICTURE pero "flotantes")


# Lista de variables de imagenes: IMAGEN_1...IMAGEN_64 y ${IMAGEN_1}...${IMAGEN_64}
LISTA_VARS_IMAGENES = map(lambda x: 'IMAGEN_%s' % x, range(1,65)) + map(lambda x: '${IMAGEN_%s}' % x, range(1,65))

# nombre de la imagen en blanco (blank.jpg...)
IMAGEN_EN_BLANCO = 'blank'

DEBUG_MOSTRAR_WORD =	False
DEBUG_GUARDAR_DOC =		False


def _get_msword():
	"""
	Obtiene una instancia de MS Word
	XXX se podria comprobar si ya estaba abierto de una vez anterior, para no
		tener que abrirlo de nuevo
	"""
	return win32.gencache.EnsureDispatch('Word.Application')


def generar_informe_msword(nombre_archivo, exploracion, plantilla, imagenes = None):
	"""
	Generar un informe desde una plantilla de MS Word, en formato DOC.
	El informe generado es directamente un archivo PDF.

	nombre_archivo: El nombre de archivo PDF

	exploracion: es la exploracion de la que se quiere generar el informe.
				 Ha de ser un objeto de tipo endosys.model.exploraciones.Exploracion
				 También puede ser un int, en este caso es el id. de un
				 tipo de exploración, y se utiliza para comprobar si una plantilla
				 se generaría correctamente (que no falten campos)

	plantilla: el nombre del archivo de plantilla de informe. Sin la ruta base pero
			   con la extensión. p.e: "GASTROSCOPIA 2 FOTOS.doc"

	imagenes: las imágenes a mostrar en el informe. Es un registro sqlalchemy de
			  rel_Capturas_Informes. También puede ser directamente una lista de
			  ids (int) de Capturas. Puede ser None.
	"""

	def actualizar_imagen(linkformat, shape_fn):
		"""
		Actualiza el link de una imagen.
		Sirve para inline y flotantes (Fields/InlineShapes y Shapes).
		Si ha actualizado algo devuelve True.

		linkformat:     objeto de word tipo LinkFormat
		shape_fn:       funcion que devuelve el objeto de word tipo Shape o InlineShape.
						Tiene que ser asi porque al modificarlo el objeto parece
						que se destruye y vuelve a crear...
		"""
		#   XXX recalcular dimensiones para que la relación de aspecto sea correcta!
		width = shape_fn().Width
		height = shape_fn().Height
        # utilizar SourceName en vez de SourceFullName porque a veces, al manipular
		# un documento, Word añade un path al ${imagen_N}, y SourceName devuelve solo
		# el "nombre de archivo" sin path.
		picture_source = str(linkformat.SourceName).upper()
##		print 'picture_source', picture_source
		# comprueba si es IMAGEN_N o ${IMAGEN_N} (de 1 hasta 64)
		if picture_source in LISTA_VARS_IMAGENES:
			# extrae el numero de imagen (una forma un tanto peculiar, pero correcta...)
			num = int( filter(lambda c: c in '0123456789', picture_source) or 0 )
			if num and imagenes and num <= len(imagenes):
				if isinstance(imagenes[num-1], int):
					captura_id = imagenes[num-1]
				else:
					captura_id = imagenes[num-1].captura_id
				s = os.path.join(config['pylons.paths']['capturas'], str(captura_id) + '.jpg')
			else:
				s = os.path.join(config['pylons.paths']['root'], 'res', '%s.jpg' % IMAGEN_EN_BLANCO)
			linkformat.SourceFullName = s
			linkformat.Update()
			shape_fn().Width = width
			shape_fn().Height = height
			return True
		else:
			return False

	def procesar_range(range_fn):
		"""
		Esta es la función que buscar variables y las sustituye por el valor.
		se usa para distintos ranges: documento, tablas, header, footer...

		range_fn    es una funcion que ha de devolver un Range. Se va ejecutando
					en un bucle hasta que ya no se encuentran mas variables.
		"""
		# VARIABLES: buscar ocurrencias de ${...}
		while True:
			# crear un rango de todo el documento
			rng = range_fn()
			# buscar usando una regex todos los ${...}
			rng.Find.ClearFormatting()
			rng.Find.MatchWildcards = True
			if rng.Find.Execute(regex_word):
				# recuperar el valor correspondiente al campo indicado y asignarlo
				campo = rng.Text[2:-1]
				campo = campo.upper()
				valor = valores.get(campo, get_no_definido_value)
##				print campo, valor
				# modificarlo en el documento
				rng.Text = valor
			else:
				break

		# IMAGENES: se definen mediante un campo (field) de tipo INCLUDEPICTURE. En vez de
		#           tener indicada la ruta de un archivo, tienen ${imagen_N}
		# XXX de momento solo funciona si estan las imagenes como JPGs! habria que controlar esto...
		#	buscar los FIELDS del tipo INCLUDEPICTURE, en el documento incluyendo tablas.
		#   son objetos tipo InlineShape... si son imágenes "flotantes" son tipo "Shape" y
		#   se buscan de una forma distinta.
		rng = range_fn()
		for field in filter(lambda f: f.Type == wdFieldIncludePicture, rng.Fields):
			actualizar_imagen(field.LinkFormat, lambda: field.InlineShape)


	#regex = r"\${([^{}]*)}"  # buscar patrones ${nombre_campo}
	regex_word = r'$\{*\}'		# la sintaxis de reg. exp. en la búsqueda de MS Word
								# es distinta, más simplificada

	if isinstance(exploracion, int):
		# se trata de id de un tipo de exploración, por lo tanto poner
		# datos ficticios, para chequear la plantilla.
		# En este caso no vendrán imágenes, asi que se generan también unas
		# de prueba.
		exploracion = construir_objeto_exploracion_test(exploracion)
		#imagen_en_blanco = 'test'
	valores = get_valores(exploracion, mays = True, formato = 'TEXT')

	pythoncom.CoInitialize()
	try:
		# Crear instancia de MS Word y ocultarla
		word = _get_msword()
		word.ScreenUpdating = False
	 	is_word_visible = word.Visible
	 	if DEBUG_MOSTRAR_WORD:
			word.ScreenUpdating =	True
			word.Visible =			True
		doc = None
		try:
			# abrir documento plantilla
			doc = word.Documents.Open(
				os.path.join(config['pylons.paths']['custom_informes_templ'], plantilla),
				False,				# ConfirmConversions
				True,				# ReadOnly
				False,				# AddToRecentFiles
				pythoncom.Empty,	# PasswordDocument
				pythoncom.Empty,	# PasswordTemplate
				True,				# Revert (True to discard any unsaved changes to the open document and reopen the file. False to activate the open document.)
				pythoncom.Empty,	# WritePasswordDocument
				pythoncom.Empty,	# WritePasswordTemplate
				pythoncom.Empty,	# Format
				pythoncom.Empty,	# Encoding
				False,				# Visible
				True,				# OpenAndRepair (True to repair the document to prevent document corruption.)
				pythoncom.Empty,	# DocumentDirection
				True,				# NoEncodingDialog (True to skip displaying the Encoding dialog box that Word displays if the text encoding cannot be recognized.)
				pythoncom.Empty		# XMLTransform
			)

			# Rellenar datos: variables e imágenes inline
			#	buscar en el cuerpo del documento
##			procesar_range( lambda: doc.Range(0, doc.Characters.Count) )
			#		Mejor llamar a Range() sin parametros para seleccionar todo el doc.
			#		Al pasar characters.count, a veces no devolvia todo el documento. Parece
			#       que tenía algo que ver con los Fields, segun si se muestran los
			#       códigos de campo o no el número de caracteres también cambia, y eso
			#       liaba las cosas.
			procesar_range( lambda: doc.Range() )

			#	buscar en Tablas
			for table in doc.Tables:
				procesar_range( lambda: table.Range )

			#	buscar en los Headers y Footers de las Sections
			for section in doc.Sections:
				for header in section.Headers:
					procesar_range( lambda: header.Range )
				for footer in section.Footers:
					procesar_range( lambda: footer.Range )

			#   buscar en Shapes de tipo textbox
			for shape in filter(lambda s: s.Type == msoTextBox, doc.Shapes):
				procesar_range( lambda: shape.TextFrame.TextRange )

			# Rellenar imágenes flotantes (shapes)
			#	buscar en todo el documento (parece que están todas aqui) los "linked Pictures"
			#   XXX desactivado de momento, no funciona por un bug de Word.
			#       usar imagenes inline dentro de TextBoxes o Frames (Marcos).
##			for shape in filter(lambda s: s.Type == msoLinkedPicture, doc.Shapes):
##				actualizar_imagen(shape.LinkFormat, lambda: shape)

			# Guardar como PDF
			#   ref de ExportAsFixedFormat: http://msdn.microsoft.com/en-us/library/bb256835(v=office.12).aspx
			#   Creo que se puede usar a partir de la versión 2007 (probado con la 2010)
			doc.ExportAsFixedFormat(nombre_archivo, wdExportFormatPDF, False)
			if DEBUG_GUARDAR_DOC: doc.SaveAs(nombre_archivo + '.doc')
		finally:
            # Cerrar el documento abierto por EndoTools
##			print 'word.Documents.Count', word.Documents.Count # xxx

			if not DEBUG_MOSTRAR_WORD:
				if doc: doc.Close(wdDoNotSaveChanges)
				# Cerrar MS Word si no hay mas documentos abiertos
		##		print 'word.Documents.Count', word.Documents.Count
		##		if word.Documents.Count <= 0:
		##			word.Application.Quit()
			# NO CERRAR WORD! dejarlo oculto si no se estaba usando
			word.Visible = is_word_visible
			word.ScreenUpdating = True
			if DEBUG_MOSTRAR_WORD:
				word.Visible = True
	finally:
		pythoncom.CoUninitialize()

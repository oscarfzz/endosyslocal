"""
TODO:
	Al generar el PDF a partir del local.html se podría guardar ya el archivo
	para no tener que volver a generarlo. Incluso se podria añadir una opción
	de "migración" que, una vez generado el PDF, elimine los HTML.

	Sacar fuera el guardado del informe en una carpeta, para que también se pueda
	hacer al usar MS Word.

"""
import os
from pylons import config
import logging
from endosys.lib.misc import *

log = logging.getLogger(__name__)

def html_to_pdf(informe):
	"""
	Convierte un informe HTML (local) a PDF, mediante la libreria pisa.
	Esto antes se hacía desde rest/informes.py, pero como ya no es necesario
	si se usa MS Word-PDF, se ha movido a "legacy".

	XXX la libreria pisa, al convertir el html a pdf, necesita acceder a las
	imagenes. Si en el html estan en la forma "http://server/rest/capturas/1.jpg", lo que hace
	es conectarse mediante httplib al server, pero al no tener opciones de autenticacion
	le devuelve error 401 o 403.
	por lo tanto la solucion es generar el pdf a partir de un html con las rutas locales
	ya que se genera desde el mismo servidor y puede acceder a los archivos del disco.
	lo que habra que tener en cuenta es si alguna imagen no esta en el servidor, si no
	en el pacs, o el formato (jpg, bmp...)
	ojo, el formato de las imagenes ha de ser jpg, que si no hace cosas raras!

    NUEVO:  el archivo PDF se guarda siempre junto al .local.html, asi no se tiene
			que generar cada vez.
			Se ha quitado de aqui la opción de guardar en una carpeta, ahora se hace
			a otro nivel para que lo haga también al generar mediante MS Word.

	XXX		se podría hacer que además elimine el .local.html, ya que una vez
			generado y guardado el .pdf ya  no se necesita para nada.
	"""

	# abrir el archivo html estatico
	ruta = config['pylons.paths']['informes']
	archivo = '.'.join( (str(informe.id), 'local', 'html') )
	fsrc = wpath = os.path.join(ruta, archivo)
	fsrc = open(fsrc, "rb")

	# convertir el archivo html estatico a pdf
	import sx.pisa3 as pisa # XXX   al final no uso la version de pisa "xhtml2pdf", sino la sx.pisa3...
	import StringIO
	result = StringIO.StringIO()
	pdf = pisa.CreatePDF(fsrc, result, wpath, debug = 1) # pasar una cadena en Unicode
	if pdf.err:
		raise Exception('Error convirtiendo el informe a formato PDF (%s)' % (str(informe.id)))

	# NUEVO: guardar ya el archivo .pdf junto al .local.html
	archivo = '.'.join( (str(informe.id), 'pdf') )
	f = file(os.path.join(ruta, archivo) , 'wb')
	f.write(result.getvalue())
	f.close()

##	# guardar en una carpeta, si esta configurado en el ini
##	# (XXX sacar de aqui para que tambien lo haga en Word!!!)
##	try:
##		guardar_pdf = config.get('INFORME_PDF.GUARDAR', '0')
##		guardar_pdf = bool(int(guardar_pdf)) if isint(guardar_pdf) else False
##		if guardar_pdf:
##			carpeta_pdf = config.get('INFORME_PDF.CARPETA', '')
##			nombre_pdf = config.get('INFORME_PDF.NOMBRE_ARCHIVO', '').replace('$', '%')
##			ruta = os.path.join(carpeta_pdf, '')
##			print 'ruta pdf: ', ruta
##
##			# GENERAR EL NOMBRE SEGUN EL INI
##			accessionNumber = '(SIN_CITA)'
##			if informe.exploracion.cita and informe.exploracion.cita.work:
##				accessionNumber = str(informe.exploracion.cita.work.accessionNumber)
##
##			nombre_params = {
##				'apellido1':		formatea_valor(informe.exploracion.paciente.apellido1).replace('/', '-'),
##				'apellido2':		formatea_valor(informe.exploracion.paciente.apellido2).replace('/', '-'),
##				'nombre':			formatea_valor(informe.exploracion.paciente.nombre).replace('/', '-'),
##				'historia':			formatea_valor(informe.exploracion.paciente.historia).replace('/', '-'),
##				'tipoExploracion':	formatea_valor(informe.exploracion.tipoExploracion.nombre).replace('/', '-'),
##				'numero':			formatea_valor(informe.exploracion.numero).replace('/', '-'),
##				'fecha':			formatea_valor(informe.exploracion.fecha).replace('/', '-'),
##                'accessionNumber':	accessionNumber
##			}
##
##			nombre_informe = nombre_pdf % nombre_params
##			# ###################################################
##
##			archivo = '.'.join( (str(nombre_informe), 'pdf') )
##			f = os.path.join(ruta, archivo)
##			f = open(f, "wb")
##			f.write(result.getvalue())
##			f.close()
####			except Exception as e:
##	except Exception, e:
##		log.debug('Ha ocurrido un error guardando el informe PDF:')
##		log.debug(e)
##	# #######

	# devolver el contenido del PDF
	return {'size': result.len, 'content': result.getvalue()}

"""
GENERAR INFORMES HTML. ES EL MÉTODO ANTIGUO (EL NUEVO ES MEDIANTE MS WORD)

Anteriormente este modulo estaba en lib/informes.py

get_plantillas()    					ya no se usa. Se usa lib/informes:get_plantillas(), que en principio hace lo mismos
generar_informe_html()  				solo se usa para generar el informe en HTML. Antes era generar_informe()
_construir_objeto_exploracion_test()    es privado de este modulo
"""
import os
try:
    import Image
except ImportError:
    from PIL import Image
import datetime

import logging
from endotools.model.informes import Informe, Rel_Capturas_Informes
from endotools.model.capturas import Captura
from endotools.model.exploraciones import Exploracion
from endotools.model.tiposExploracion import TipoExploracion
from endotools.model.pacientes import Paciente
from endotools.model.citas import Cita
from endotools.model.citas_ex import Cita_ex
from endotools.model.worklist import Work

from endotools.lib.base import render
from endotools.lib.formularios import FormExplData

from endotools.lib.misc import *
from pylons import config

import sqlalchemy
from sqlalchemy.orm.attributes import InstrumentedAttribute

log = logging.getLogger(__name__)


def _construir_objeto_exploracion_test(tipoExploracion_id):
	exploracion = record()
	tipoExploracion = registro_by_id(TipoExploracion, tipoExploracion_id)

	# datos del paciente
	exploracion.paciente = record()
	for campo in Paciente.__dict__:
		if campo == 'id': continue
		if isinstance(getattr(Paciente, campo), InstrumentedAttribute):
			setattr(exploracion.paciente, campo, campo)

	# datos de la exploración
	exploracion.numero = u'(núm. exploración)'
	exploracion.fecha = u'(fecha de la exploración)'
	exploracion.medico = record(nombre = u'(Nombre, médico)', apellido1 = u'(1er apellido, médico)', apellido2 = u'(2o apellido, médico)', colegiado = u'(N. de colegiado, médico)')
	exploracion.tipoExploracion = record(nombre = tipoExploracion.nombre)

	# formularios
	exploracion.formularios = []
	for f in tipoExploracion.formularios:
		exploracion.formularios.append(f.formulario)

	# datos de la cita
	exploracion.cita = record()
	#   cita
	exploracion.cita.sala = record(nombre = u'(sala cita)')
	exploracion.cita.servicio = record(nombre = u'(servicio cita)')
	exploracion.cita.fecha = u'(fecha cita)'
	exploracion.cita.hora = u'(hora cita)'
	exploracion.cita.observaciones = u'(observaciones cita)'
	exploracion.cita.prioridad = u'(prioridad cita)'
	#   cita_ex
	exploracion.cita.ex = record()
	for campo in Cita_ex.__dict__:
		if campo == 'cita_id': continue
		if isinstance(getattr(Cita_ex, campo), InstrumentedAttribute):
			setattr(exploracion.cita.ex, campo, campo)
	#   worklist
	exploracion.cita.work = record()
	for campo in Work.__dict__:
		if campo == 'cita_id': continue
		if isinstance(getattr(Work, campo), InstrumentedAttribute):
			setattr(exploracion.cita.work, campo, campo)

	return exploracion


def generar_informe_html(exploracion, plantilla, imagenes = None, local = False, carpeta_plantillas_alt = False, allow_undefined_vars = False):
	"""
	Devuelve el informe en formato string (html).

	PARAMS:

	local:	bool, indica si los links a las imágenes, a la ruta_base y a custom_res serán
			rutas locales o vinculos http al servidor. Sirve por ejemplo
			para generar el informe en local y crear el PDF.

	plantilla: el nombre del archivo de plantilla de informe. Sin la ruta base pero
			   con la extensión. p.e: "GASTROSCOPIA 2 FOTOS.htm"

	exploracion: es la exploracion de la que se quiere generar el informe.
				 Ha de ser un objeto de tipo endotools.model.exploraciones.Exploracion
				 También puede ser un int, en este caso es el id. de un
				 tipo de exploración, y se utiliza para comprobar si una plantilla
				 se generaría correctamente (que no falten campos)

    allow_undefined_vars: bool. Indica si se permite que hayan variables NO definidas.
						  en ese caso se asignará un valor vacío, o "NO DEFINIDO", en rojo.
						  Sirve para hacer pruebas.

	imagenes: las imágenes a mostrar en el informe. Es un registro sqlalchemy de
			  rel_Capturas_Informes. Puede ser None.

	carpeta_plantillas_alt: ...algo que ver con integración de Asturias (HUCA)

	"""
	imagen_en_blanco = 'blank'

	if isinstance(exploracion, int):
		# se trata de id de un tipo de exploración, por lo tanto poner
		# datos ficticios, para chequear la plantilla.
		# En este caso no vendrán imágenes, asi que se generan también unas
		# de prueba.
		exploracion = _construir_objeto_exploracion_test(exploracion)
		imagen_en_blanco = 'test'

	campos = {}
	# anadir los campos del paciente
	for c, v in vars(exploracion.paciente).iteritems():
		if not(c.startswith('_')):
			if c == 'sexo':
				if v == 0:
					v = 'Mujer'
				elif v == 1:
					v = 'Hombre'
				else:
					v = ''

				campos['paciente_' + c] = formatea_valor( v )
			else:
				campos['paciente_' + c] = formatea_valor( v )

	# codigo del centro
	if exploracion.servicio.centro:
		campos['exploracion_centro_codigo'] = formatea_valor( exploracion.servicio.centro.codigo )
	else:
		campos['exploracion_centro_codigo'] = ''

	# anadir los campos de la exploracion
	campos['exploracion_numero'] = formatea_valor( exploracion.numero )
	campos['exploracion_fecha'] = formatea_valor( exploracion.fecha )
	campos['exploracion_medico'] = formatea_valor( exploracion.medico.nombre )
	campos['exploracion_tipo_exploracion'] = formatea_valor( exploracion.tipoExploracion.nombre )

	# nuevos campos, MEDICO:
	campos['medico_nombre'] = formatea_valor( exploracion.medico.nombre )
	campos['medico_apellido1'] = formatea_valor( exploracion.medico.apellido1 )
	campos['medico_apellido2'] = formatea_valor( exploracion.medico.apellido2 )
	campos['medico_colegiado'] = formatea_valor( exploracion.medico.colegiado )


	# campos de la cita (tablas CITAS, CITAS_EX, WORKLIST...)
	#   cita
	campos['cita_sala'] = formatea_valor( '' )
	campos['cita_servicio'] = formatea_valor( '' )
	campos['cita_fecha'] = formatea_valor( '' )
	campos['cita_hora'] = formatea_valor( '' )
	campos['cita_observaciones'] = formatea_valor( '' )
	campos['cita_prioridad'] = formatea_valor( '' )
	#   cita_ex
	for campo in Cita_ex.__dict__:
		if campo == 'cita_id': continue
		if isinstance(getattr(Cita_ex, campo), InstrumentedAttribute):
			campos['cita_' + campo] = formatea_valor( '' )
	#   worklist
	for campo in Work.__dict__:
		if campo == 'cita_id': continue
		if isinstance(getattr(Work, campo), InstrumentedAttribute):
			campos['work_' + campo] = formatea_valor( '' )

	if exploracion.cita:
		#   cita
		if exploracion.cita.sala:
			campos['cita_sala'] = formatea_valor( exploracion.cita.sala.nombre )
		if exploracion.cita.servicio:
			campos['cita_servicio'] = formatea_valor( exploracion.cita.servicio.nombre )
		campos['cita_fecha'] = formatea_valor( exploracion.cita.fecha )
		campos['cita_hora'] = formatea_valor( exploracion.cita.hora )
		campos['cita_observaciones'] = formatea_valor( exploracion.cita.observaciones )
		campos['cita_prioridad'] = formatea_valor( exploracion.cita.prioridad ) # XXX La prioridad tiene un mapeo...
		#   cita_ex
		if exploracion.cita.ex:
			for c, v in vars(exploracion.cita.ex).iteritems():
				if c.startswith('_') or (c == 'cita_id'):
					continue
				campos['cita_' + c] = formatea_valor( v )
		#   work
		if exploracion.cita.work:
			for c, v in vars(exploracion.cita.work).iteritems():
				if c.startswith('_') or (c == 'cita_id'):
					continue
				campos['work_' + c] = formatea_valor( v )


	# anadir los campos de cada formulario
	if isinstance(exploracion, Exploracion):
		for formulario in exploracion.formularios:
			formexpldata = FormExplData(formulario)
			for grupoCampos in formexpldata.gruposCampos:
				for campo in grupoCampos.campos:
					campos[campo.nombre] = campo.valor.to_html()
	else:
		for formulario in exploracion.formularios:
			formexpldata = FormExplData(formulario)
			for grupoCampos in formexpldata.gruposCampos:
				for campo in grupoCampos.campos:
					campos[campo.nombre] = campo.valor.to_html()


	# anadir las imagenes (para poner en el atributo src de un tag img)
	if imagenes == None: imagenes = []
	for n, rel_captura in enumerate(imagenes):
		if local:
			campos['imagen_%d' % (n+1)] = os.path.join(config['pylons.paths']['capturas'], str(rel_captura.captura_id) + '.jpg')    # XXX de momento solo funciona si estan las imagenes como JPGs! habria que controlar esto...
		else:
			campos['imagen_%d' % (n+1)] = h.url_for(controller='rest/capturas', action='show', id=rel_captura.captura_id, format='auto')

	#   rellenar el resto de imagenes en blanco
	for n in range(len(imagenes), 32):
		if local:
			campos['imagen_%d' % (n+1)] = os.path.join(config['pylons.paths']['root'], 'res', '%s.jpg' % imagen_en_blanco)
		else:
			campos['imagen_%d' % (n+1)] = '/res/%s.png' % imagen_en_blanco

	#   un campo para acceder a la carpeta /public/ . La ruta será distinta segun si
	#   es en local o remoto, por eso se pone como campo. Sirve para poner imágenes
	#   estáticas (logos), etc... En la plantilla se pondrá por ejemplo asi:
	#   <img src="${ruta_base}logotipo.jpg">
	#   Evitar el uso de "ruta_base"!!! mejor usar "custom_res"
	if local:
		campos['ruta_base'] = config['pylons.paths']['static_files'] + '/'
	else:
		campos['ruta_base'] = '/'

	#   custom_res: acceso a recursos especificos (logo, fuentes...) del cliente
	#               para generar el informe
	if local:
		campos['custom_res'] = config['pylons.paths']['custom_informes_res'] + '/'
	else:
		campos['custom_res'] = '/custom/res/'


	# ATENCIÓN:
	# Cuando en mako no se encuentra una variable se le asigna mako.runtime.UNDEFINED.
	# esta variable esta asignada a un objeto de tipo Undefined, que lanza una excepción
	# en el str(). Por lo tanto, se puede cambiar Undefined.__str__ para que no lance
	# una excepción.
	import mako.runtime
	if allow_undefined_vars:
		mako_runtime_undefined_str = mako.runtime.Undefined.__str__
		mako.runtime.Undefined.__str__ = lambda self: '<span style="color: red;">(NO DEFINIDO)</span>'
	try:
		# XXX   se ha quitado la funcionalidad de CARPETA_PLANTILLAS_INFORMES_ALT !!!
##		CARPETA_PLANTILLAS_INFORMES = config.get('CARPETA_PLANTILLAS_INFORMES', 'informes')
##		if carpeta_plantillas_alt:
##			CARPETA_PLANTILLAS_INFORMES = config.get('CARPETA_PLANTILLAS_INFORMES_ALT', CARPETA_PLANTILLAS_INFORMES)
##		s = render('mako', '/' + CARPETA_PLANTILLAS_INFORMES + '/' + plantilla, **campos)
		s = render('mako', '/' + plantilla, **campos)
	finally:
		if allow_undefined_vars:
			mako.runtime.Undefined.__str__ = mako_runtime_undefined_str

	return s


def get_plantillas():
	"""
	devuelve un array con todas las plantillas de informe (nombres de archivo)
	"""
	lista = []
	# ya no se usa el valor de CARPETA_PLANTILLAS_INFORMES del .INI
##	CARPETA_PLANTILLAS_INFORMES = config.get('CARPETA_PLANTILLAS_INFORMES', 'informes')

    # en principio, parece que el mako siempre los coge de /templates
##	ruta = os.path.join(config['pylons.paths']['root'], 'templates', CARPETA_PLANTILLAS_INFORMES)
	ruta = config['pylons.paths']['custom_informes_templ']
	for dirpath, dirs, files in os.walk(ruta):
		if dirpath == ruta:
			for f in files:
				if not f.startswith('_'):
					lista.append(f)
	return lista

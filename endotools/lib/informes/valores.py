"""
"""

from pylons.i18n import _
import os
from pylons import config
from endotools.lib.misc import *
from endotools.model import Exploracion, \
							TipoExploracion, \
							Paciente, \
							Cita_ex, \
							Work
							
from sqlalchemy.orm.attributes import InstrumentedAttribute
from endotools.lib.formularios import FormExplData
from endotools.lib.exploraciones import *
import endotools.lib.capturas as lib_capturas
#from endotools.lib.capturas import _archivo, get_by_id
import logging
log = logging.getLogger(__name__)

def get_no_definido_value():
	no_definido = _('(No definido)')#IDIOMAOK
	return no_definido

def construir_objeto_exploracion_test(tipoExploracion_id):
	"""
	Construir un objeto "exploracion" para pruebas. Se utiliza para generar
	una previsualización de una plantilla, y en vez de valores reales tiene
	descripciones de cada campo.
	"""
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
	exploracion.edad_paciente = u'(edad del paciente)'

	# formularios
	exploracion.formularios = []
	for f in tipoExploracion.formularios:
		exploracion.formularios.append(f.formulario)

	# datos de la cita
	exploracion.cita = record()
	#   cita
	exploracion.cita.sala = record(nombre = u'(sala cita)')
##	exploracion.cita.servicio = record(nombre = u'(servicio cita)')
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



def get_valores(exploracion, mays = False, formato = 'HTML', informe = None):
	"""
	Obtiene un dict con los valores de cada campo para una determinada
	exploracion.

	formato:    puede ser 'HTML' o 'TEXT'. se tiene en cuenta por ejemplo para
				los saltos de linea, etc... (TEXT se usa para Word)
	"""
	formato = formato.upper()
	campos = {}
##	print "hola"
	# anadir los campos del paciente
	for c, v in vars(exploracion.paciente).iteritems():
		if not(c.startswith('_')):
			if c == 'sexo':
				if v == 0:
					v = _('Sexo:Mujer')#IDIOMAOK
				elif v == 1:
					v = _('Sexo:Hombre')#IDIOMAOK
				else:
					v = ''

				campos['paciente_' + c] = formatea_valor( v )
			else:
				campos['paciente_' + c] = formatea_valor( v )

	paciente_nhc_centro = None
	for centro in exploracion.paciente.centros:
		if centro.centro_id == exploracion.servicio.centro.id:
			paciente_nhc_centro = formatea_valor(centro.nhc)
			break

	if paciente_nhc_centro is not None:
		campos['paciente_nhc_centro'] = paciente_nhc_centro
	else:
		campos['paciente_nhc_centro'] = ''


	# AÃadimos paciente_historia como 'alias' de paciente_idunico por compatibilidad
	campos['paciente_historia'] = campos['paciente_idunico']

	# codigo del centro (en Word no es muy util, ya que se utiliza en HTML para
	#					indicar distintas rutas de logotipos según el centro)
	if exploracion.servicio.centro:
		campos['exploracion_centro_codigo'] = formatea_valor( exploracion.servicio.centro.codigo )
	else:
		campos['exploracion_centro_codigo'] = ''

	# anadir los campos de la exploracion
	campos['exploracion_numero'] = formatea_valor( exploracion.numero )
	campos['exploracion_fecha'] = formatea_valor( exploracion.fecha )
	campos['exploracion_medico'] = formatea_valor( exploracion.medico.nombre )
	campos['exploracion_tipo_exploracion'] = formatea_valor( exploracion.tipoExploracion.nombre )
	campos['exploracion_edad_paciente'] = formatea_valor( exploracion.edad_paciente )

	campos['exploracion_aseguradora'] = formatea_valor( '' )
	if exploracion.aseguradora:
		campos['exploracion_aseguradora'] = formatea_valor( exploracion.aseguradora.nombre )

	# campo del numero de la exploracion sobre el tipo de exploracion (No ID)
	contador_exploracion = formatea_valor(obtener_numero_tipo_exploracion(exploracion)["posicion"])
	campos['exploracion_numero_tipo_expl'] = contador_exploracion # obsoleto - se deja por compatibilidad
	campos['exploracion_contador'] = contador_exploracion

    # anadir los campos de informe
	if informe:
		campos['informe_numero'] = formatea_valor( informe.numero )
		campos['informe_fecha'] = formatea_valor( informe.fecha )
		campos['informe_medico_nombre'] = formatea_valor( informe.medico.nombre )
		campos['informe_medico_apellido1'] = formatea_valor( informe.medico.apellido1 )
		campos['informe_medico_apellido2'] = formatea_valor( informe.medico.apellido2 )
		campos['informe_medico_colegiado'] = formatea_valor( informe.medico.colegiado )
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
##		if exploracion.cita.servicio:
##			campos['cita_servicio'] = formatea_valor( exploracion.cita.servicio.nombre )
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
					if formato == 'TEXT':
						campos[campo.nombre] = campo.valor.to_text()
						campos[campo.nombre + "____TIPO"] = campo.tipo
						campos[campo.nombre + "____TITULO"] = unicode(campo.titulo, 'latin_1')
					else:
						campos[campo.nombre] = campo.valor.to_html()
						campos[campo.nombre + "____TIPO"] = campo.tipo
						campos[campo.nombre + "____TITULO"] = unicode(campo.titulo, 'latin_1')

	else:
		for formulario in exploracion.formularios:
			formexpldata = FormExplData(formulario)
			for grupoCampos in formexpldata.gruposCampos:
				for campo in grupoCampos.campos:
					if formato == 'TEXT':
						campos[campo.nombre] = campo.valor.to_text()
						campos[campo.nombre + "____TIPO"] = campo.tipo
						campos[campo.nombre + "____TITULO"] = unicode(campo.titulo, 'latin_1')
					else:
						campos[campo.nombre] = campo.valor.to_html()
						campos[campo.nombre + "____TIPO"] = campo.tipo
						campos[campo.nombre + "____TITULO"] = unicode(campo.titulo, 'latin_1')

##	# anadir las imagenes (para poner en el atributo src de un tag img)
##	if imagenes == None: imagenes = []
##	for n, rel_captura in enumerate(imagenes):
##		if local:
##			campos['imagen_%d' % (n+1)] = os.path.join(config['pylons.paths']['capturas'], str(rel_captura.captura_id) + '.jpg')    # XXX de momento solo funciona si estan las imagenes como JPGs! habria que controlar esto...
##		else:
##			campos['imagen_%d' % (n+1)] = h.url_for(controller='rest/capturas', action='show', id=rel_captura.captura_id, format='auto')
##
##	#   rellenar el resto de imagenes en blanco
##	for n in range(len(imagenes), 32):
##		if local:
##			campos['imagen_%d' % (n+1)] = os.path.join(config['pylons.paths']['root'], 'res', '%s.jpg' % imagen_en_blanco)
##		else:
##			campos['imagen_%d' % (n+1)] = '/res/%s.png' % imagen_en_blanco
##
##	#   un campo para acceder a la carpeta /public/ . La ruta será distinta segun si
##	#   es en local o remoto, por eso se pone como campo. Sirve para poner imágenes
##	#   estáticas (logos), etc... En la plantilla se pondrá por ejemplo asi:
##	#   <img src="${ruta_base}logotipo.jpg">
##	#   Evitar el uso de "ruta_base"!!! mejor usar "custom_res"
##	if local:
##		campos['ruta_base'] = config['pylons.paths']['static_files'] + '/'
##	else:
##		campos['ruta_base'] = '/'
##
##	#   custom_res: acceso a recursos especificos (logo, fuentes...) del cliente
##	#               para generar el informe
##	if local:
##		campos['custom_res'] = config['pylons.paths']['custom_informes_res'] + '/'
##	else:
##		campos['custom_res'] = '/custom/res/'

	#	devolver con las claves en MAYS.
	if mays:
		campos_temp = {}
		for k in campos:
			campos_temp[k.upper()] = campos[k]
		campos = campos_temp

	return campos

# recorre las imagenes y genera los valores para las plantillas
def get_valores_imagenes(imagenes):
	valores = {}

	# pone todos los comentarios en blanco
	for index in range(1,65):
		valores['IMAGEN_COMENTARIO_%s' % index] = u''

	# completa la ruta y el comentario si es que tiene
	for index in range(1,65):
		if imagenes and (index <= len(imagenes)):
			# crea la ruta de la imagen
			if type(imagenes[index-1])==int:
				# si es int es pq viene de una lista de index
				valores['IMAGEN_RUTA_%s' % index] = lib_capturas._archivo(imagenes[index-1])
				captura = lib_capturas.get_by_id(imagenes[index-1])
			else:
				# es una lista de obj alquemy
				valores['IMAGEN_RUTA_%s' % index] = lib_capturas._archivo(imagenes[index-1].captura.id)
				captura = imagenes[index-1].captura

			if captura.comentario:
				valores['IMAGEN_COMENTARIO_%s' % index] = unicode(captura.comentario,'latin_1')

	return valores

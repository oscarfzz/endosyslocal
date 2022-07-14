from pylons.i18n import _

import endotools.model as model
from endotools.model.meta import engine
from endotools.model import meta
from sqlalchemy.sql import and_, or_, not_, func
import sqlalchemy.databases.mssql as mssql
import sqlalchemy.databases.oracle as oracle
import sqlalchemy.databases.mysql as mysql
from endotools.model.exploraciones import Exploracion
from endotools.model.valores import ValorMulti
import os
from endotools.lib.misc import *
import csv
import gc
import sys

def obtener_numero_tipo_exploracion(exploracion):
	'''
	Desc: Obtiene que numero de exploracion sobre la cantidad total de exploraciones
	      de su tipo y con el paciente dado.

	Params: *exploracion: es el objeto exploracion de sqlalchemy
	Retorna: Un diccionario con 2 claves:
	         * "posicion" que corresponde al numero de exploracion de ese tipo y a ese paciente.
	         * "total" que corresponde al total de exploracions de ese tipo y a ese paciente.
	'''

	#obtiene todas las exploraciones del mismo tipo y de un paciente, que esten finalizadas.
	q = meta.Session.query(Exploracion)
	q = q.filter(Exploracion.tipoExploracion_id == exploracion.tipoExploracion_id)
	q = q.filter(Exploracion.paciente_id == exploracion.paciente_id)
	q = q.filter(Exploracion.estado == 1)
	q = q.filter(Exploracion.borrado == 0) #2.4.10 excluye las borradas

	#obtiene el numero
	i = 1
	encontrado = False
	total = q.count()
	for exp in q:
		if exp.id == exploracion.id:
			break
		i+=1

	data = {}
	data['total'] = q.count()
	data['posicion'] = i

	return data


def ampliar_data_exploraciones(exploraciones,data,format):

	# Este for es para eliminar los nodos citas de las exploraciones
	# ya que no son iguales en todas las exploraciones
	for item in data: del(item['cita'])

	columnas = {}
	headers = {}
	for expl in exploraciones:
		for rel in expl.formularios:
			for rel2 in rel.formulario.campos:
				columnas[rel.formulario.titulo + ' ' + rel2.campo.nombre] = None
				headers[rel.formulario.titulo + ' ' + rel2.campo.nombre] = rel.formulario.titulo + ": " +  rel2.campo.titulo
	
	for expl in exploraciones:
		a = filter(lambda i: str(i['id']) == str(expl.id), data)
		if len(a) > 0:
			expl_el = a[0]

		if expl.servicio:
			expl_el['centro'] = {
				'id': formatea_valor(expl.servicio.centro_id),
				'codigo': formatea_valor(expl.servicio.centro.codigo),
				'nombre': formatea_valor(expl.servicio.centro.nombre)
			}
		else:
			expl_el['centro'] = None

		if not expl_el: continue

		for k in columnas.iterkeys():
			expl_el[k] = ''

		for v in expl.valoresTexto:
			expl_el[v.formulario.titulo + ' ' + v.campo.nombre] = v.valor
			headers[v.formulario.titulo + ' ' + v.campo.nombre] = v.formulario.titulo + ": " + v.campo.titulo

		for v in expl.valoresSelec:

			if  v.elemento:
				valor = v.elemento.nombre
			else:
				valor = None
			expl_el[v.formulario.titulo + ' ' + v.campo.nombre] = valor
			headers[v.formulario.titulo + ' ' + v.campo.nombre] = v.formulario.titulo + ": " + v.campo.titulo


		for v in expl.valoresMulti:
			if getattr(v.campo, "tipo_control", 0) == 2:
				q = meta.Session.query(ValorMulti)
				q = q.filter(and_(ValorMulti.campo_id == v.campo_id,
								  ValorMulti.elemento_id == v.elemento_id,
								  ValorMulti.exploracion_id == v.exploracion_id))
				cantidad = " (" + str(q.one().cantidad or 1) + ")"
			else:
				cantidad = ""
			#TODO: Crear try - Causa error cuando quiero exportar con la base de datos de Ruben.
			if expl_el[v.formulario.titulo + ' ' + v.campo.nombre] != '':
				expl_el[v.formulario.titulo + ' ' + v.campo.nombre] = expl_el[v.formulario.titulo + ' ' + v.campo.nombre] + ','+ v.elemento.nombre + cantidad
				headers[v.formulario.titulo + ' ' + v.campo.nombre] = v.formulario.titulo + ": " + v.campo.titulo
			else:
				expl_el[v.formulario.titulo + ' ' + v.campo.nombre] = v.elemento.nombre + cantidad
				headers[v.formulario.titulo + ' ' + v.campo.nombre] = v.formulario.titulo + ": " + v.campo.titulo

		for v in expl.valoresBool:
			expl_el[v.formulario.titulo + ' ' + v.campo.nombre] = v.valor
			headers[v.formulario.titulo + ' ' + v.campo.nombre] = v.formulario.titulo + ": " + v.campo.titulo
	

	return data, headers


from endotools.lib.base import *
import random


def exportar(controller, params, format, session, nombre_fichero,username = None):
	# XXX es necesario mejorar esta funcion. El problema esta cuando la cantidad de datos es muy grande.
	#     La memoria usada se eleva mucho y puede pasar que alente todo el servidor mientras se esta exportando.
	#	  La idea para mejorarlo es hacerlo de a partes (lo ideal seria con el limit, pero tenemso que tener soporte)
	# 	  para mssql (y oracle?) o sino hacer una division por partes manual
	#	  Se podrian hacer 1000 rows y escribir en el archivo y luego cerrar y volver  a hacer 1000 rows.

	#import pdb
	#pdb.set_trace()
	q = session.query(controller.tabla)

	if username:
		params = controller._crear_parametros_medico(params,username)

	params = controller._procesar_params_especiales(params)

	lista = controller._genera_lista_filter(params)
	q = controller._aplicar_filtros(q, lista, format)
	
	headers = []
	registros = q.all()
	data = controller._crear_data(registros,format)
	if format=="csv":
		data, headers = ampliar_data_exploraciones(registros,data,format)
		nombre_fichero += ".csv"
	
	opciones = {}
	opciones["excluir"] = _completar_excluir()
	opciones["headers"] = _completar_headers_exportar(headers)
	opciones["order_columns"] = _definir_orden()

	csvdata = objeto_to_csv(data,'\n',opciones)
	
	#check si dir existe, si no existe crearlo
	directorio = "data/ficheros/"
	#print os.path.exists(directorio)
	if not os.path.exists(directorio):
		os.makedirs(directorio)

	f = open(directorio + nombre_fichero,'w')

	f.write(csvdata)
	f.close()

	gc.collect()

	return nombre_fichero

def is_exploracion_borrada(exploracion_id):
	exploracion = registro_by_id(Exploracion, exploracion_id)
	if exploracion.borrado:
		return True
	else:
		return False


def _completar_headers_exportar(headers = {}):

	headers_to_add = {
		'tipoExploracion__nombre': u'Tipo Exploración: Nombre',
		'medico__nombre': u'Médico: Nombre',
		'servicio__codigo': u'Servicio: Código',
		'centro__nombre': u'Centro: Nombre',
		'paciente__numAfiliacion': u'Paciente: Nro. Afiliación',
		'paciente__fechaNacimiento': u'Paciente: Fecha Nacimiento',
		'paciente__poblacion': u'Paciente: Población',
		'paciente__DNI': u'Paciente: DNI',
		'hora': u'Exploración: Hora',
		'aseguradora': u'Aseguradora',
		'medico__colegiado': u'Médico: Nro. Colegiado',
		'edad_paciente': u'Paciente: Edad',
		'paciente__sexo': u'Paciente: Sexo',
		'paciente__direccion': u'Paciente: Dirección',
		'paciente__numero_expediente': u'Paciente: Nro. Expediente',
		'paciente__codigoPostal': u'Paciente: Cod. Postal',
		'paciente__historia': u'Paciente: Historia',
		'paciente__telefono2': u'Paciente: Teléfono 2',
		'paciente__telefono1': u'Paciente: Teléfono 1',
		'numero': u'Nro. Exploración',
		'servicio__nombre': u'Servicio',
		'estado': u'Estado',
		'paciente__CIP': u'Paciente: CIP',
		'paciente__apellido1': u'Paciente: Apellido 1',
		'paciente__apellido2': u'Paciente: Apellido 2',
		'paciente__nombre': u'Paciente: Nombre',
		'fecha': u'Exploración: Fecha',
	}

	for k,v in headers_to_add.iteritems():
		headers[k] = v.encode("ISO-8859-1")

	return headers


def _completar_excluir():
	return [
		'id',
		'paciente_id',
		'motivo_id',
		'centro_id',
		'servicio_id',
		'borrado',
		'borrado_motivo',
		'aseguradora_id',
		'medico_id',
		'paciente__id',
		'motivo',
		'StudyInstanceUID',
		'href',
		'work',
		'exploracion_dicom',
		'paciente__deshabilitado',
		'paciente__aseguradora_id',
		'paciente__comentarios',
		'paciente__provincia',
		'medico__apellido1',
		'medico__apellido2',
		'medico__username',
		'medico__id',
		'centro__id',
		'centro__codigo',
		'tipoExploracion__id',
		'tipoExploracion__codigo',
		'tipoExploracion_id',
		'tipoExploracion__orden',
		'tipoExploracion__servicio_id',
		'tipoExploracion__activo',
		'tipoExploracion__duracion',
		'tipoExploracion__color',
		'servicio__id',
		'servicio__centro_id',
		'exploracion_dicom__stationName',
		'exploracion_dicom__patientBirthDate',
		'exploracion_dicom__stored',
		'exploracion_dicom__patientName',
		'exploracion_dicom__studyDescription',
		'exploracion_dicom__institutionName',
		'exploracion_dicom__exploracion_id',
		'exploracion_dicom__studyDate',
		'exploracion_dicom__patientSex',
		'exploracion_dicom__accessionNumber',
		'exploracion_dicom__studyTime',
		'exploracion_dicom__studyID',
		'exploracion_dicom__studyInstanceUID'
	]

def _definir_orden():

	#orden basico, los demas campos seran ordenados
	#alfabeticamente
	return [
		'numero',
		'tipoExploracion__nombre',
		'fecha',
		'hora',
		'medico__nombre',
		'edad_paciente',
		'aseguradora',
		'centro__nombre'
	]
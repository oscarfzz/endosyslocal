import logging
from pylons.i18n import _
from endotools.model import meta
from endotools.model.servicios import Servicio
from endotools.model.tiposExploracion import TipoExploracion, Rel_Formularios_TiposExploracion, Rel_Servicios_TiposExploracion
from xml.etree.ElementTree import Element, SubElement, tostring

from endotools.lib.genericREST import *

from authkit.authorize.pylons_adaptors import authorize
from authkit.permissions import RemoteUser, ValidAuthKitUser, UserIn, HasAuthKitRole, And
from endotools.lib.usuarios.seguridad import roles

from endotools.lib.plugins.base import *

from sqlalchemy.sql import and_, or_

from endotools.model.servicios import get_servicio_id

log = logging.getLogger(__name__)

class TiposexploracionController(GenericRESTController):

	def __init__(self, *args, **kwargs):
		GenericRESTController.__init__(self, *args, **kwargs)
		self.tabla = TipoExploracion
		self.nombre_recurso = 'tipoExploracion'
		self.nombre_recursos = 'tiposExploracion'
		self.campos_index = ('id', 'nombre', 'color', 'activo', 'orden', 'codigo', 'duracion')
		self.campo_orderby = TipoExploracion.orden, TipoExploracion.nombre


	def _doIndex(self, params, format='xml'):
		return GenericRESTController._doIndex(self, params, format)


	@authorize(RemoteUser())
	def index(self, format='xml'):

		p = request.params

		#si viene el parametro _all, entonces muestra todos los tipos de exploracion
		self.mostrar_todos = False
		if "_all" in p:
			self.mostrar_todos = True
			del p["_all"]

		self.servicio_activo_id = None
		if "servicio_id" in p:
			self.servicio_activo_id = p["servicio_id"]
			del p["servicio_id"]
		#	print "entraaaa"

		#print p["servicio_id"]
		#print "--------------"

		return self._doIndex(p, format)
#		return GenericRESTController.index(self, format)


	def _filtrar_index(self, query, format= None):
		if not self.mostrar_todos:

			#filtra todos los servicios que tiene ese medico
			medico = medico_from_user(request.environ['REMOTE_USER'])
			if len(medico.servicios) > 0:

				cond = [] #[ (TipoExploracion.servicio_id == None) ]
				query = query.join(TipoExploracion.servicios)

				for rel in medico.servicios:

					if self.servicio_activo_id != '':
						
						if self.servicio_activo_id is not None: 
							if int(rel.servicio_id) == int(self.servicio_activo_id):
			 					# filtra el tipo de exploracion q pertenece al servicio enviado por parametro
			 					cond.append( (Rel_Servicios_TiposExploracion.servicio_id == rel.servicio_id) )
						else:
							# si no se envia servicio se envian todas las expl de todos sus servicios
							cond.append( (Rel_Servicios_TiposExploracion.servicio_id == rel.servicio_id) )
					else:
						#condicion absurda para que no envie resultados.
						cond.append( (Rel_Servicios_TiposExploracion.servicio_id == -1) )

				if len(cond):
					query = query.filter( or_(*cond) )
							
		return query


	def _return_show(self, tipoExploracion, data):
		data["servicios"] = []
		for rel in tipoExploracion.servicios:
			data["servicios"].append({
				'id': formatea_valor(rel.servicio.id),
			})

		data['formularios'] = []
		for rel in tipoExploracion.formularios:
			data['formularios'].append({
				'id': formatea_valor(rel.formulario.id),
				'orden': formatea_valor(rel.orden),
				'titulo': formatea_valor(rel.formulario.titulo)
			})

	@authorize(RemoteUser())
	def show(self, id, format='xml'):
		return GenericRESTController.show(self, id, format)

	@authorize(HasAuthKitRole([roles.admin_tipos_exploracion]))
	def create(self, format='xml'):
		return GenericRESTController.create(self, format)

	def _doCreate(self, params, format='xml'):

		self.servicios = None
		if "servicios" in params:
			self.servicios = params["servicios"]
			del params["servicios"]

		return GenericRESTController._doCreate(self, params, format)

	def _created(self, registro):

		#crea los servicios seleccionados
		if self.servicios:
			ids = map( lambda x: int(x) if x else 0, self.servicios.split(',') )
			for servicio_id in ids:
				if (servicio_id == 0) or (servicio_id in [rel.servicio_id for rel in registro.servicios]): continue
				log.debug("entra  a crear")
				rel = Rel_Servicios_TiposExploracion()
				rel.servicio_id = servicio_id
				rel.tipoExploracion_id = registro.id
				meta.Session.save(rel)
				meta.Session.commit()

		return registro

	@authorize(HasAuthKitRole([roles.admin_tipos_exploracion]))
	def delete(self, id):
		return GenericRESTController.delete(self, id)

	@authorize(HasAuthKitRole([roles.admin_tipos_exploracion]))
	def update(self, id):
		# utilizar el parametro 'formularios', que es una lista de ids separados por comas
		tipoexploracion = self._registro_by_id(id)
		p = request.params;
		if "formularios" in p:
			ids = map( lambda x: int(x) if x else 0, p['formularios'].split(',') )
			p.pop('formularios')

			#   eliminar los anteriores que ya no esten en los nuevos valores
			#   y los que esten, actualizar el 'orden'
			for rel in tipoexploracion.formularios[:]:
				if (not rel.formulario_id in ids):
					meta.Session.delete(rel)
				else:
					rel.orden = ids.index(rel.formulario_id)
					meta.Session.update(rel)

			# anadir los nuevos valores que no esten en los anteriores
			orden = 0
			for formulario_id in ids:
				if (formulario_id == 0) or (formulario_id in [rel.formulario_id for rel in tipoexploracion.formularios]): continue
				rel = Rel_Formularios_TiposExploracion()
				rel.formulario_id = formulario_id
				rel.tipoExploracion_id = tipoexploracion.id
				rel.predefinido = True
				rel.orden = orden
				tipoexploracion.formularios.append(rel)
				orden = orden + 1
		
		#Guarda el campo "active" cuando se pulse el checkbox, sin necesidad de clickar en "guardar"
		if "activo" in request.params:
			active = int(p['activo'])
			print(type(active))
			print(active)
						
			q = meta.Session.query(TipoExploracion).filter(TipoExploracion.id == id )
			
			if q.count():
				tipoExploracion_active = q.one()
				#tipoExploracion_active.id = id
				print(tipoExploracion_active.id)
				tipoExploracion_active.activo = int(request.params['activo'])
				meta.Session.update(tipoExploracion_active)
					

		#actualiza los servicios donde estara disponible el tipo de exploracion
		if "servicios" in p:
			ids = map( lambda x: int(x) if x else 0, p['servicios'].split(',') )
			p.pop('servicios')

			#   eliminar los anteriores que ya no esten en los nuevos valores
			for rel in tipoexploracion.servicios[:]:
				if (not rel.servicio_id in ids):
					meta.Session.delete(rel)

			for servicio_id in ids:
				if (servicio_id == 0) or (servicio_id in [rel.servicio_id for rel in tipoexploracion.servicios]): continue
				rel = Rel_Servicios_TiposExploracion()
				rel.servicio_id = servicio_id
				rel.tipoExploracion_id = tipoexploracion.id
				tipoexploracion.servicios.append(rel)

		self._update_registro_from_params(tipoexploracion, p)
		meta.Session.commit()

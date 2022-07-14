from pylons.i18n import _
from pydicom.dataset import Dataset
from pynetdicom import AE, BasicWorklistManagementPresentationContexts

from base import BasePyDICOM

class WorklistRequest(BasePyDICOM):
	""" La intención de esta clase es que sea 
		aislada de cualquier libreria de 
		pylons y endosys asi luego
		puede ser usada en otros desarrollos
	"""

	# TODO: 
	# 	-Internacionalizar mensajes de error

	def set_requested_context(self, context=None):
		self.ae.requested_contexts = BasicWorklistManagementPresentationContexts
		#self.ae.add_requested_context(BasicWorklistManagementPresentationContexts)
		
	def _create_filters(self, filters=[]):
		ds = Dataset()
		
		for f in filters:
			if type(f['value']) == list:
				# dentro de esta hay una lista, por lo que 
				# se tiene que recorrer la lista, para agregar los filtros internos
				filters_2nd_level = Dataset()
				for f2 in f['value']:
					filters_2nd_level.add_new(f2['key'], f2['type'], f2['value'])
				
				# agrego todos filtros internos al elemento
				ds.add_new(f['key'], f['type'], [filters_2nd_level])
			else:
				ds.add_new(f['key'], f['type'], f['value'])

		return ds

	def get_worklist(self, filters = []):
		# array donde se guardaran los resultados
		results = []

		#filters = [ {"key": 0x00100010, "type": "PN", "value": "*" }]
		#filters = [ {'key': 0x00400100, 'type': 'SQ', 'value': [{'key': 0x00080060, 'type': 'CS', 'value': 'ES' }]} ]
		if filters == []:
			# si no viene con filtros entonces agarra los filtros
			# de la configuracion self.conf.
			# tiene prioridad el filters de la funcion para hacer
			# pruebas individuales, pero generalmente
			# se tiene que usar el filters del conf
			filters = self.conf["filters"]

		try: 
			filters = self._create_filters(filters)
		except Exception, e:
			raise e

		print filters

		if self.assoc.is_established:
			# hay conexion, hago un query con el C-FIND
			# 'W' significa que se hace un query al MWL
			# ds son los filtros que se envian

			responses = self.assoc.send_c_find(filters, query_model='W')

			# TODO: mejorar esta parte, esta en pruebas
			for (status, identifier) in responses:
				if status:
					#print('C-FIND query status: 0x{0:04x}'.format(status.Status))

					# If the status is 'Pending' then identifier is the C-FIND response
					if status.Status in (0xFF00, 0xFF01):
					   results.append(identifier)
					   #print identifier
				else:
					raise Exception(_(u'Error en respuesta MWL: Finalizació del tiempo de espera, la petición fue abortada o se recibió una respuesta inválida'))

			# Cierra la conexion
			self.assoc.release()
			return results
		else:
			raise Exception(_(u'Conexion al worklist ha fallado'))

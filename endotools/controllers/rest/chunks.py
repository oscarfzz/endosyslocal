"""
Este controlador recibe los chunks enviados desde un cliente de EndoTools.
Los chunks son trozos de archivos más grandes. Cuando EndoTools tiene todos los
chunks de un archivo lo reconstruye. Luego, se procesa el archivo según el tipo
indicado.

TODO:
	- Implementar seguridad: control de usuario que envía un chunk
"""
from pylons import config
from pylons.i18n import _
from endotools.model.capturas import Captura
from endotools.model.exploraciones import Exploracion
from xml.etree.ElementTree import Element, SubElement, tostring
from endotools.lib.genericREST import *
from sqlalchemy.sql import join
from authkit.authorize.pylons_adaptors import authorized, authorize, authorize_request, NotAuthorizedError
from authkit.permissions import RemoteUser, ValidAuthKitUser, UserIn, HasAuthKitRole, And
from endotools.lib.usuarios.seguridad import roles
from base64 import b64decode
from endotools.lib.pydcmtk.pydcmtk import *
from endotools.model.capturas import Captura
import logging
import os
try:
    import Image
except ImportError:
    from PIL import Image
import endotools.lib.registro as registro
import shutil
import endotools.lib.chunks.utils as chunk_utils
import endotools.lib.chunks.chunks_process as chunks_process
import uuid
import endotools.lib.capturas


log = logging.getLogger(__name__)

class ChunksController(BaseController):

	def __init__(self, *args, **kwargs):
		BaseController.__init__(self, *args, **kwargs)

	@conditional_authorize(RemoteUser())
	def create(self):
		

		"""
		Se crea un nuevo chunk. Se envía por POST, con content-type: multipart/form-data,
		y con estos parámetros:
		 	* archivo				El param correspondiente al fichero chunk enviado
			* paciente_id      	id del paciente (opcional)
			* exploracion_id      id de la exploración (opcional)
		"""

		# crear el archivo chunk
		ruta = config['pylons.paths']['chunks']
		ruta_capturas = config['pylons.paths']['capturas']
		
		if 'webob._parsed_post_vars' in request.environ:
			# metodo recomendado, usando multipart
			params = request.environ['webob._parsed_post_vars'][0]
			fieldstorage = params['archivo']
			archivo = os.path.basename(fieldstorage.filename)

			ruta = config['pylons.paths']['chunks']
			ruta_capturas = config['pylons.paths']['capturas']

			# El nombre del archivo que se copia en la carpeta de chunks 
			# se graba como se envio con el uuid
			f = open(os.path.join(ruta, archivo), 'wb')
			shutil.copyfileobj(fieldstorage.file, f)
			fieldstorage.file.close()
			f.close()
			
			# Intenta unir y poner como disponible la captura
			try:
				# hace un set para que el procesamiento de no generados termine y deje este habilitado
				config['pylons.g'].event_chunks.set()

				# Espera hasta que se libere el lock y luego realiza
				with config['pylons.g'].lock_chunks:
					chunk_utils.try_join_chunk_and_set_disponible(archivo)
				
				# hace un clear para que el procesamiento de los chunks no 
				# generados pueda ejecutarse nuevamente cuando sea necesario 
				config['pylons.g'].event_chunks.clear()
			except Exception as e:
				log.error(str(e))

		else:
			abort(400, _(u'Los parámetros de la petición no son correctos'))#IDIOMAOK
		
		response.status_code = 201

	@conditional_authorize(RemoteUser())
	def update(self, id):
		"""
		No se permite modificar un chunk
		"""
		abort(403, _(u'No se puede modificar un chunk'))#IDIOMAOK

	@conditional_authorize(RemoteUser())
	def delete(self, id):
		"""
		No se permite eliminar un chunk
		"""
		abort(403, _(u'No se puede eliminar un chunk'))#IDIOMAOK

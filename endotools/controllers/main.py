import logging
import paste.fileapp
import os
from authkit.permissions import RemoteUser
from authkit.authorize.pylons_adaptors import authorize, NotAuthorizedError
from pylons import config
import mimetypes
import codecs
from authkit.authorize.pylons_adaptors import authorize
from authkit.permissions import RemoteUser, ValidAuthKitUser, UserIn, HasAuthKitRole, And
from endotools.lib.base import *

log = logging.getLogger(__name__)

class MainController(BaseController):

	def _servir_fichero(self, path):
		if not os.path.exists(path): abort(404)

		if config.get('CACHE.ACTIVO', '1') == '1':
			etag_cache(key=1)
			max_age = str(config.get('CACHE.MAX_AGE', '31536000')) # 1 anio
			fapp = paste.fileapp.FileApp(path, headers=[('Cache-Control','public'), ('Pragma','cache'), ('Cache-Control','max-age='+str(max_age))])
		else:
			fapp = paste.fileapp.FileApp(path)

		return fapp(request.environ, self.start_response)

	def _web_main_html(self):
		"""
		preprocesar main.html:
			incluir tags adicionales (script, style)
		"""
		response.content_type = "text/html"
		content = open(os.path.join(config['pylons.paths']['static_files'], 'webapp', 'main.html')).read()

		# atributo lang del elemento HTML. Asignar el idioma definido en el INI.
		# Asi se puede inicializar la libreria web de i18n.
		# Si no se ha definido, por defecto "es"
		content = content.replace('ENDOTOOLS:LANG', config.get('lang', 'es'))

		# poner la version.
		try:
			version_file = os.path.join(config['pylons.paths']['root_parent'], 'version.txt')
			v_file = open(version_file, 'r')
			first_line = v_file.readline()
			content = content.replace('ENDOTOOLS:VERSION', first_line)
		except Exception as e:
			log.error(e)
			content = content.replace('ENDOTOOLS:VERSION', '')



		# tags para firma electronica
		if config.get('FIRMA_ELECTRONICA.ACTIVO', '0') in ('1', '2'):
			if config.get('FIRMA_ELECTRONICA.TIPO') == '@firma' :
				content = content.replace('<!--ENDOTOOLS:FIRMA_ELECTRONICA-->',
				"""
<script type="text/javascript" src="/cliente_firma/deployjava/deployJava-non-minified.js?v=1"></script>
<script type="text/javascript" src="/cliente_firma/miniapplet-1.1u4/miniapplet.js"></script>
<script type="text/javascript">
	//	cargar applet de firma electronica.
	//	XXX	seria mejor que el almacen de datos (aqui KEYSTORE_WINDOWS) se pueda configurar desde el INI
	MiniApplet.cargarMiniApplet('/cliente_firma/miniapplet-1.1u4', MiniApplet.KEYSTORE_WINDOWS);
</script>
<!--	El estilo display:none se pone después de cargar el applet, porque si no no se inicializa	-->
<style>#deployJavaPlugin, #miniApplet { position:fixed; z-index:0; left:0; top: 0;}</style>
				"""
				)
			elif config.get('FIRMA_ELECTRONICA.TIPO') == 'viafirma' :
				content = content.replace('<!--ENDOTOOLS:FIRMA_ELECTRONICA-->',
				"""
					<script type="text/javascript" src="/cliente_firma/viafirma.pesado.js"></script>
				"""
				)

		return content

	def web(self, filename):
		"""
		/web accede a los archivos de la aplicación web. Por defecto es la
		carpeta /webapp, pero si se utiliza otra se puede cambiar aqui.
		Se podría hacer configurable en el .INI
		"""
		if filename and filename.lower() == 'main.html':
			# main.html se preprocesa
			return self._web_main_html()
		else:
			return self._servir_fichero(os.path.join(config['pylons.paths']['static_files'], 'webapp', filename))

	@authorize(RemoteUser())
	def admin(self):
		username = request.environ['REMOTE_USER']
		if username.upper() == "SYSADMIN":
			return self._servir_fichero(os.path.join(config['pylons.paths']['static_files'], 'admin', 'main.html'))
		else:
			raise NotAuthorizedError

	def lib(self, filename):
		"""
		/lib accede a las bibliotecas del servidor. Por defecto es la
		carpeta /lib, pero si se utiliza otra se puede cambiar aqui.
		Se podría hacer configurable en el .INI
		"""
		return self._servir_fichero(os.path.join(config['pylons.paths']['static_files'], 'lib', filename))

	def lib_yui2(self, filename):
		"""
		accede a lib/yui2
		"""
		return self._servir_fichero(os.path.join(config['pylons.paths']['static_files'], 'lib', 'yui2', filename))

	def lib_yui3(self, filename):
		"""
		accede a lib/yui3
		"""
		return self._servir_fichero(os.path.join(config['pylons.paths']['static_files'], 'lib', 'yui3', filename))

	def res(self, filename):
		"""
		/res accede a los archivos en endotools/res (blank.png...)
		"""
		return self._servir_fichero(os.path.join(config['pylons.paths']['root'], 'res', filename))

	def custom_informes_res(self, filename):
		"""
		/custom/res accede a los archivos en CLIENTE/informes/res (logos, fuentes,
		etc... para informes)
		"""
		return self._servir_fichero(os.path.join(config['pylons.paths']['custom_informes_res'], filename))

	def version(self):
		"""
		devuelve el número de versión, que está en el archivo /version.txt
		"""
		version_file = os.path.join(config['pylons.paths']['root_parent'], 'version.txt')
		if not os.path.exists(version_file): abort(404)
		fapp = paste.fileapp.FileApp(version_file)
		return fapp(request.environ, self.start_response)

	def combo(self, format):
		"""
		Se pasa un parametro "files", que contiene todos los ficheros que se quieren obtener
		separados por "|", de la carpeta /public. Se devuelven estos ficheros concatenados, con un #13

		Como es directo en python sin pasar por routes, Se han de indicar las rutas
		completas, no sirve p.e. web/, lib/, etc...

			ejemplo de llamada: /combo.css?files=webapp/assets/main.css|webapp/assets/exploraciones.css

		format: opcional, es la extensión pasada a "combo", para devolver un content-type.

		OJO: Los archivos han de ser de texto y con codificación UTF-8. Pueden tener BOM.
		"""
		files = request.params.get('files', '')
		if not files: abort(404)
		files = files.split('|')
		resultado = u''
		for f in files:
			# quitar barras (/, \) iniciales y convertir varias seguidas en una, quedando todas /
			f = '/'.join(filter(lambda item: item != '', f.split('/')))
			f = '/'.join(filter(lambda item: item != '', f.split('\\')))
			f = os.path.join(config['pylons.paths']['static_files'], f)
			if not os.path.exists(f): abort(404)
			# VER:
            #	http://stackoverflow.com/questions/13590749/reading-unicode-file-data-with-bom-chars-in-python
            #	http://stackoverflow.com/questions/147741/character-reading-from-file-in-python
			bytes = min(32, os.path.getsize(f))
			raw = open(f, 'rb').read(bytes)
			if raw.startswith(codecs.BOM_UTF8):
				encoding = 'utf-8-sig'
			else:
				encoding = 'utf-8'
			f = codecs.open(f, encoding=encoding)

			try:
				resultado = resultado + f.read()
			finally:
				f.close()

		format = format or ''
 		response.content_type = mimetypes.types_map.get('.' + format.lower(), 'text/plain')
		return resultado

import logging

from endotools.lib.base import *
from authkit.authorize.pylons_adaptors import authorize
from authkit.permissions import RemoteUser, ValidAuthKitUser, UserIn, HasAuthKitRole, And

log = logging.getLogger(__name__)

class InterpreterController(BaseController):
	""" controlador para ejecutar codigo de forma remota, para pruebas """

	@authorize(UserIn(['sysadmin']))
	def index(self):
		html = """
<html>
  <head>
	<title>PYTHON interpreter</title>

	<script data-main="/web/" type="text/javascript" src="/lib/jquery/require-jquery.js"></script>

	<script type="text/javascript">
  	  $(function() {

		$('#ejecutar').click(function(e) {
			$.ajax({
				type: 'POST',
				url: '/interpreter/ejecutar',
				data: 'command=' + $('#codigo').val(),
				processData: false,
				//contentType: 'text/plain; charset=UTF-8',
				contentType: 'application/x-www-form-urlencoded; charset=UTF-8',
				success: function(data) {
					$('#salida').html(data);
				},
				error: function(data) {
					alert('ERROR. ' + data);
				}
			});

			return false;
		});

	  });
	</script>

  </head>

  <body>
	<h1>PYTHON interpreter</h1>


		<textarea id="codigo" cols=100 rows=15></textarea>

		<br>

		<button id="ejecutar">Ejecutar</button>


	<h2>salida:</h2>
	<div id="salida"></div>

  </body>
</html>
		"""
##		return render('/interpreter.mako')
		return html


	@authorize(UserIn(['sysadmin']))
	def ejecutar(self):
		log.debug('ejecutar %s', request.params['command'])
		exec request.params['command'].replace('\r', '')

		while True:
			a = raw_input(' --> ')
			if a.upper() == 'EXIT': break
			try:
				exec a
			except Exception as e:
				log.error(e)


		return 'ok'
"""The base Controller API

Provides the BaseController class for subclassing, and other objects
utilized by Controllers.
"""
from pylons import c, cache, config, g, request, response, session
from pylons.controllers import WSGIController
from pylons.controllers.util import abort, etag_cache, redirect_to
from pylons.decorators import jsonify, validate
from pylons.i18n import _, ungettext, N_
from pylons.templating import render
from authkit.authorize.pylons_adaptors import authorize, NotAuthorizedError
from authkit.permissions import RemoteUser

import endotools.lib.helpers as h
import endotools.model as model

from endotools.model import meta

class BaseController(WSGIController):

    def __call__(self, environ, start_response):
        """Invoke the Controller"""
        # WSGIController.__call__ dispatches to the Controller method
        # the request is routed to. This routing information is
        # available in environ['pylons.routes_dict']
        try:
            return WSGIController.__call__(self, environ, start_response)
        finally:
            meta.Session.remove()

# Include the '_' function in the public names
__all__ = [__name for __name in locals().keys() if not __name.startswith('_') \
           or __name == '_']


class CommandController(BaseController):
	
	@authorize(RemoteUser())
	def run(self):
		username = request.environ['REMOTE_USER']
		if username.upper() == "SYSADMIN":
			if request.method == 'POST':
				return self.post(request)
			else:
				return self.get(request)
		else:
			raise NotAuthorizedError
			
	def get(self, request):
		return '<html><head></head><body><form method="post"><button type="submit">Run Command</button></form></body></html>'

	def post(self, request):
		self.run_command()
		return self.post_message()

	def post_message(self):
		return "Ran"

	def run_command(self):
		raise NotImplementedError

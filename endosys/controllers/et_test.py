import logging

from endosys.lib.base import *

from authkit.authorize.pylons_adaptors import authorize
from authkit.permissions import RemoteUser, ValidAuthKitUser, UserIn, HasAuthKitRole, And

log = logging.getLogger(__name__)

class EtTestController(BaseController):

	@authorize(UserIn(['sysadmin']))
	def index(self):
		return render('/et_test.mako')

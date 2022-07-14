import logging

import os
from endotools.lib.base import *
from pylons import config
from datetime import date


log = logging.getLogger(__name__)


def check_cache_dir():
	"""
	comprueba que "cache_dir" no sea /data. debería ser /cache, u otra carpeta
	"""
	cache_dir = config.get('pylons.cache_dir', '')
	return not(os.path.split(cache_dir)[1].upper() == 'DATA')

"""The application's Globals object"""
from pylons import config
from threading import Lock, Event
class Globals(object):
	"""Globals acts as a container for objects available throughout the
	life of the application
	"""

	event_chunks = None
	lock_chunks = None

	def __init__(self):
		"""One instance of Globals is created during application
		initialization and is available during requests via the 'g'
		variable
		"""

		self.event_chunks = Event()
		self.lock_chunks = Lock()
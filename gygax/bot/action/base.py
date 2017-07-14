from ...util.log import getLogger
from ...util.conv import make_list
from ...util.sentry import SentryClient
from ..dispatch import Event
_log = getLogger('action')

'''
	This module implements the base Action object.
	All bot actions should subclass Action.
	Subclasses are expected to overload these methods:

		-	Action._install(self, proxy)
			This method is called upon object creation and passed a Proxy object
			Actions are expected to use the proxy to register for events, and push events if needed.

		-	Action._process(self, event)
			This method is called whenever a event matching this action is found.
			It is passed the event and is expected to use push new events onto the queue using self._put().
'''

class Action:
	def __init__(self, proxy, logger = None):
		self._proxy = proxy
		self.__log = logger
		self._install(proxy)

	@property
	def _log(self):
		if not self.__log:
			log = getattr(self, 'log', False)
			if not log:
				log = _log
			self.__log = log.getChild(self.__class__.__name__)
		return self.__log

	def __call__(self, msg):
		try:
			events = self._process(msg)
		except Exception:
			SentryClient.captureException()
			return False
		if isinstance(events, (list, tuple)) or isinstance(events, Event):
			for e in make_list(events):
				self._put(e)
			return True
		else:
			return events

	def _install(self, proxy):
		pass
	
	def _process(self, msg):
		self._log.debug('Got message, Taking no action')
		return True

	def _register(self, event, delay, key = None):
		return self._proxy.register(event, delay , key)

	def _put(self, event):
		return self._proxy.put(event)

	def _delay(self, *args, **kwargs):
		return self._proxy.delay(*args, **kwargs)

	def _cancel(self, key):
		return self._proxy.cancel(key)

	def _schedule(self, event, time, key = None, repeat = False):
		return self._proxy.schedule(event, time, key, repeat)
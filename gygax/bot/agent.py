from threading import Thread, Event, Timer
from queue import Queue, Empty
from .dispatch import Dispatcher, Proxy
from ..util.log import getLogger
from ..util.config import config
from ..util.crypto import rand_key
from ..util.time import convert_delta, time_until, convert_walltime

_log = getLogger('bot.agent')

class Agent(Thread):
	def __init__(self):
		self._events = Queue()
		self._dispatch = Dispatcher()
		self._proxy = Proxy(self._dispatch, self.put, self.delay, self.schedule, self.cancel)
		self._running = Event()
		self._repeat = dict()
		self._scheduled = dict()
		self._pending = dict()
		super().__init__()

	def _get(self):
		try:
			return self._events.get(True, 1)
		except Empty:
			pass
		return None
	
	def put(self, event):
		self._events.put(event)
	
	def delay(self, event, delay, key = None, repeat = False):
		if not key:
			key = rand_key()
		if repeat:
			self._repeat[key] = (event, delay)
		delay = convert_delta(delay).seconds
		timer = Timer(delay, self._on_delay, [event, key])
		self._pending[key] = timer
		if self._running.isSet():
			timer.start()
		return key
	
	def _on_delay(self, event, key):
		self.put(event)
		self._pending.pop(key, None)
		repeat = self._repeat.pop(key, None)
		if repeat:
			self.delay(*repeat, key, repeat = True)

	def cancel(self, key):
		try:
			self._repeat.pop(key, None)
			self._scheduled.pop(key, None)
			timer = self._pending.pop(key, None)
			if timer:
				timer.cancel()
				return True
			return False
		except Exception as e:
			_log.error('Error removing key %s'%key)
			_log.exception(e)

	def schedule(self, event, time, key = None, repeat = False):
		key = key if key else rand_key()
		if repeat:
			self._scheduled[key] = (event, time)
		delay = time_until(convert_walltime(time))
		_log.debug('Scheduling %s at %s, delaying %i seconds'%(event, time, delay))
		timer = Timer(delay, self._on_schedule, [event, key])
		self._pending[key] = timer
		if self._running.isSet():
			timer.start()
		return key


	def _on_schedule(self, event, key):
		self.put(event)
		self._pending.pop(key, None)
		repeat = self._scheduled.pop(key, None)
		if repeat:
			self.schedule(*repeat, key, repeat = True)

	@property
	def proxy(self):
		return self._proxy
		
	def _handle(self, event):
		_log.debug(event)
		_log.debug('Handling event type: %s, topic: %s'%(event.type, event.topic))
		handled = self._dispatch(event)
		if not handled:
			_log.debug('No handlers were found for event')
	
	def start(self):
		self._running.set()
		super().start()

	def run(self):
		_log.debug('Starting agent, waiting for events...')
		for timer in self._pending.values():
			timer.start()
		while self._running.isSet():
			event = self._get()
			if event:
				_log.debug('A wild Event appeared!')
				self._handle(event)
		_log.debug('Exiting.')

	def join(self, timeout = 0):
		self._running.clear
		return super().join(timeout)
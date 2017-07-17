from threading import Thread, Event, Timer, RLock
from queue import Queue, Empty
from .dispatch import Dispatcher, Proxy
from ..util.log import getLogger
from ..util.config import config
from ..util.crypto import rand_key
from ..util.time import convert_delta, time_until, convert_walltime, is_delta, is_walltime, secs_until
from ..api.storage import load_schedule, add_to_schedule, remove_from_schedule
from .const import TIMER_TYPE as TTYPE
from datetime import datetime
# from .action import all_actions
from ..api.slack import Slack

_log = getLogger('bot.agent')

class Agent(Thread):
	def __init__(self):
		self._events = Queue()
		self._dispatch = Dispatcher()
		self._proxy = Proxy(self._dispatch, self.put, self.schedule, self.cancel)
		self._running = Event()
		self._scheduled = dict()
		self._pending = dict()
		self._schedule_lock = RLock()
		super().__init__()

	def _get(self):
		try:
			return self._events.get(True, 1)
		except Empty:
			pass
		return None
	
	def put(self, event):
		self._events.put(event)

	def cancel(self, key):
		try:
			remove_from_schedule(key)
			self._scheduled.pop(key, None)
			timer = self._pending.pop(key, None)
			if timer:
				timer.cancel()
				return True
			return False
		except Exception as e:
			_log.error('Error removing key %s'%key)
			_log.exception(e)

	def schedule(self, event, time, key = None, repeat = False, persist = True):
		if is_walltime(time):
			delay = to_datetime(time)
			_log.debug('Scheduling cron event %s at %s - %s'%(event, time, delay))
		elif is_delta(time):
			delay = datetime.now() + convert_delta(time)
			_log.debug('Scheduling delayed event %s every %s - %s'%(event, time, delay))
		key = key if key else rand_key()
		if persist:
			self._save_event(event, time, key, repeat, delay)
		with self._schedule_lock:
			if not key in self._pending:
				if repeat:
					self._scheduled[key] = (event, time)
				return self._schedule_event(event, delay, key)
			else:
				_log.warning('Event %s with key: %s already scheduled, skipping'%(event, key))

	def _schedule_event(self, event, time, key):
		secs = secs_until(time)
		_log.debug('Scheduling event %s at %s, sleeping %s seconds'%(event, time, secs))
		timer = Timer(secs, self._on_schedule, (event, key))
		with self._schedule_lock:
			self._pending[key] = timer
		if self._running.isSet():
			timer.start()
		return key

	def _on_schedule(self, event, key):
		self.put(event)
		with self._schedule_lock:
			self._pending.pop(key, None)
			remove_from_schedule(key)
			repeat = self._scheduled.pop(key, None)
		if repeat:
			self.schedule(*repeat, key, repeat = True)

	def _save_event(self, event, delay, key, repeat, time):
		add_to_schedule(event, delay, key, repeat, time)
	
	def _load_schedule(self):
		with self._schedule_lock:
			for event, delay, key, repeat, time in load_schedule():
				_log.debug('Loading scheduled event %s, at %s repeat: %s'%(event, time, repeat))
				if time > datetime.now():
					self._schedule_event(event, time, key)
					if repeat:
						self._scheduled[key] = (event, delay)
				else:
					self.schedule(event, delay, key, repeat, persist = False)

	@property
	def proxy(self):
		return self._proxy
		
	def _handle(self, event):
		_log.debug(event)
		_log.debug('Handling event type: %s, topic: %s'%(event.type, event.topic))
		handled = self._dispatch(event)
		if not handled:
			_log.debug('No handlers were found for event')
	
	def register_actions(self, actions):
		self.__actions = actions

	def _setup(self):
		self._load_schedule()
		self.__action_inst = [action(self.proxy) for action in self.__actions]
		self._running.set()

	def start(self):
		self._setup()
		super().start()

	def run(self):
		_log.debug('Starting agent, waiting for events...')
		with self._schedule_lock:		
			for timer in self._pending.values():
				timer.start()
		while self._running.isSet():
			event = self._get()
			if event:
				_log.debug('A wild Event appeared!')
				self._handle(event)
		_log.debug('Exiting.')

	def join(self, timeout = 0):
		self._running.clear()
		self._slack.join()
		return super().join(timeout)
from queue import Queue
from .const import EVENT_TYPES as ETYPES
from collections import defaultdict
from threading import Lock, Timer, Thread
from ..util.log import getLogger

_log = getLogger('dispatch')

class Event:
	type = ETYPES.BASE
	def __init__(self, topic, data = {}):
		self._topic = topic
		self._data = data

	def _get(self, key, default = None):
		return self._data.get(key, default)

	def _set(self, key, value):
		self._data[key] = value
		
	@property
	def topic(self):
		return self._topic
	
	@topic.setter
	def topic(self, topic):
		self._topic = topic

	def data(self, data = None, overwrite = False):
		if not data and  not overwrite:
			return self._data.copy()
		data = data if not data is None else {}
		if overwrite:
			self._data = data
		else:
			self._data.update(data)
			

class Proxy:
	def __init__(self, disp, queue, schedule, cancel):
		self.__disp = disp
		self.__queue = queue
		self.__schedule = schedule
		self.__cancel = cancel

	def register(self, *args, **kwargs):
		return self.__disp.register(*args, **kwargs)

	def put(self, event):
		if isinstance(event, list):
			for e in event:
				self.__queue(e)
		else:
			self.__queue(event)
	
	def schedule(self, *args, **kwargs):
		return self.__schedule(*args, **kwargs)

	def cancel(self, *args):
		return self.__cancel(*args)

class Async(Thread):
	def __init__(self, *args, callback = None, key = None, **kwargs):
		super().__init__(*args, **kwargs)
		self._callback = callback
		self._key = key

	def run(self):
		super().run()
		self._callback(self)


class Dispatcher:
	'''
		this object manages a list of handlers and associated
		topics, which it uses to dispatch incoming events
	'''
	def __init__(self):
		self._handlers = defaultdict(lambda: defaultdict(list))
		self.__lock = Lock()
		self._pending = []
	
	def __call__(self, event):
		return self._handle(event)

	def _handle(self, event):
		found = False
		_log.debug('Handling event type: %s, topic: %s'%(ETYPES._fields[event.type], event.topic))
		with self.__lock:
			for handler in self._handlers[event.type][event.topic]:
				_log.debug('Executing handler %s'%handler)
				# action = Async(target=handler, args=(event,), callback=self._cleanup)
				# self._pending.append(action)
				# action.start()
				try:
					handler(event)
					found = True
				except Exception as e:
					_log.error('Handler for event %s %s threw an exception'%(event.type, event.topic))
					_log.exception(e)
			if not event.topic == None:
				for handler in self._handlers[event.type][None]:
					handler(event)
		return found

	def _cleanup(self, action):
		with self.__lock:
			if action in self._pending:
				self._pending.remove(action)


	def _register(self, type, topic, handler, oneshot = False):
		_log.debug('Registering handler for type: %s, topic: %s'%(ETYPES._fields[type], topic))
		with self.__lock:
			self._handlers[type][topic].append(handler)

	def register(self, type, topic, handler, oneshot = False):
		self._register(type, topic, handler, oneshot)

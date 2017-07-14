from datetime import timedelta, datetime, date, time
from .config import config
from .log import getLogger

_log = getLogger('util.time')

def convert_delta(interval):
	'''
		Converts a timespan represented as a space seperated string 
		Xy Xd Xh Xm Xs to a datetime.timedelta object
		all segments are optional eg '2d 12h', '10m 30s', '1y 30s'
	'''
	seg_map = dict( h='hours',
					m='minutes',
					s='seconds',
					y='years',
					d='days')
	segs = interval.split(' ')
	kwargs = { seg_map[seg[-1]]: int(seg[:-1]) for seg in segs }
	return timedelta(**kwargs)

def timestamp(offset = None):
	t = datetime.utcnow()
	if offset:
		t += offset
	return t.strftime(config.token.timestamp.format)

def is_expired(timestamp):
	t = datetime.strptime(timestamp, config.token.timestamp.format)
	return t < datetime.utcnow()

def convert_walltime(wall_time):
	'''
		This function converts a string in the format
		XX:XX to a time object
		a 24 hour clock format is used
	'''
	hour, minute = map(int, wall_time.split(':'))
	return time(hour=hour, minute=minute)

def to_datetime(time, offset = 0):
	d = date.today()
	d = d.replace(day = d.day + offset)
	return datetime.combine(d, time)

def time_until(wall_time):
	now = datetime.now()
	then = to_datetime(wall_time)
	if then.hour == now.hour and then.minute == now.minute:
		then = to_datetime(wall_time, 1)
	_log.debug('now: %s, then: %s'%(now, then))
	delta = then - now
	return delta.total_seconds()



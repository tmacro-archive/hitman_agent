from datetime import timedelta, datetime, date, time
from pytz import timezone
from pytz import utc as utc_tz
from .config import config
from .log import getLogger

_log = getLogger('util.time')

local_tz = timezone(config.timezone)

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

def to_datetime(wall_time):
	t = convert_walltime(wall_time)
	d = datetime.now()
	if t.hour < d.hour or (t.hour == d.hour and t.minute <= d.minute):
		d = d.replace(day = d.day + 1)
	local = local_tz.localize(d)
	return datetime.combine(d, t).astimezone(utc_tz)
		
def is_walltime(wall_time):
	return len(wall_time.split(':')) == 2

def is_delta(delta):
	try:
		convert_delta(delta)
	except:
		return False
	else:
		return True

def secs_until(time):
	return (time - datetime.utcnow().astimezone(utc_tz)).total_seconds()
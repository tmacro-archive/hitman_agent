'''
	This module defines constant for use 
	when interacting with the bot module
'''

from collections import namedtuple

def const_type(label, const):
	'''
		Generates a namedtuple of `label` type with 
		`const` as the field names, assigning 
		each one a successive unique integer
	'''
	l = len(const)
	return namedtuple(label, const)(**{const[x]:x for x in range(l)})

EVENT_TYPES = [
		'NULL',
		'BASE',
		'MSG',
		'CMD',
		'USER',
		'GAME',
		'CRON',
	]

EVENT_TYPES = const_type('EVENT_TYPES', EVENT_TYPES)

def event_repr(event):
	return EVENT_TYPES._fields[event]

CMD_TYPES = [
		'NULL',
		'REGISTER',
		'REPORT',
		'TARGET',
		'SET',
		'TEST',
		'HELP',
		'CONFIRM',
		'DENY'
	]

CMD_TYPES = const_type('CMD_TYPES', CMD_TYPES)

def cmd_repr(cmd):
	return CMD_TYPES._fields[cmd]

USER_STATUS = [
	'NEW',
	'FREE',
	'WAITING',
	'INGAME',
	'DEAD',
	'STANDBY',
	'RETIRED'
]

USER_STATUS = const_type('USER_STATUS', USER_STATUS)

def user_status_repr(status):
	return USER_STATUS._fields[status]

HIT_STATUS = [
	'ACTIVE',
	'OPEN',
	'PENDING',
	'CONFIRMED'
]

HIT_STATUS = const_type('HIT_STATUS', HIT_STATUS)

def hit_status_repr(status):
	return HIT_STATUS._fields[status]

TIMER_TYPE = [
	'DELAY',
	'SCHED'
]

TIMER_TYPE = const_type('TIMER_TYPE', TIMER_TYPE)

def timer_type_repr(ttype):
	return TIMER_TYPE._fields[ttype]
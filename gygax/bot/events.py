from .dispatch import Event
from .const import EVENT_TYPES as ETYPES
from .const import CMD_TYPES as CTYPES
import re

class MessageEvent(Event):
	type  = ETYPES.MSG
	@property
	def text(self):
		return self._get('text')

	@property
	def user(self):
		return self._get('user')

	@property
	def channel(self):
		return self._get('channel')

	@property
	def public(self):
		return self._get('public')

class CommandEvent(MessageEvent):
	type = ETYPES.CMD
	bang_cmd = r'^!(?P<cmd>[a-z]{3,10})(?:[ \t]+(?P<args>[\w ]+))?'
	at_cmd = r'^<@(?P<user>\w+)>\s(?P<cmd>[a-z]{3,10})(?:[ \t]+(?P<args>[\w ]+))?'
	def __init__(self, *args, no_parse = False, **kwargs):
		super().__init__(*args, **kwargs)
		if not no_parse:
			type, cmd, args = self._parse(self.text)
			self._set('cmd_type', type)
			self._set('cmd', cmd)
			self._set('args', args)
	
	def _parse_args(self, args):
		if not args is None:
			return args.split(' ')

	def _parse(self, text):
		match = re.match(self.bang_cmd, self.text)
		if match:
			return 'bang', match['cmd'], self._parse_args(match['args'])
		match = re.match(self.at_cmd, text)
		if match:
			return 'at', match['cmd'], self._parse_args(match['args'])
		return None, []

	@property
	def cmd(self):
		return self._get('cmd')
	@property
	def args(self):
		return self._get('args')
	
	@property
	def cmd_type(self):
		return self._get('cmd_type')

	@property
	def valid(self):
		return self.cmd.upper() in CTYPES._fields

class SlackValidationEvent(Event):
	type = ETYPES.USER
	@property
	def user(self):
		return self._get('user')

	@property
	def validated(self):
		return self._get('valid', False)

	@property
	def failed(self):
		return self._get('failed', False)

	@property
	def uid(self):
		return self._get('uid')

class SendMessageEvent(MessageEvent):
	type = ETYPES.MSG
	@property
	def text(self):
		if self.template and self.args:
			return self.template.format(**self.args)
		return self._get('text', '')
	
	@property
	def template(self):
		return self._get('template')
	
	@property
	def args(self):
		return self._get('args')

class StructuredMessageEvent(MessageEvent):
	type = ETYPES.MSG
	@property
	def pretext(self):
		return self._get('pretext')

	@property
	def author(self):
		return self._get('auther')
	
	@property
	def author_link(self):
		return self._get('author_link')

	@property
	def title(self):
		return self._get('title')

	@property
	def title_link(self):
		return self._get('title_link')

	@property
	def color(self):
		return self._get('color')

	@property
	def content(self):
		return self._get('content')

	@property
	def fields(self):
		return self._get('fields')

	@property
	def attachments(self):
		msg = {}
		if self.pretext:
			msg['pretext'] = self.pretext
		if self.author:
			msg['author'] = self.author
		if self.author_link:
			msg['author_link'] = self.author
		if self.title:
			msg['title'] = self.title
		if self.title_link:
			msg['title_link'] = self.title_link
		if self.color:
			msg['color'] = self.color
		if self.content:
			msg['text'] = self.content
		if self.fields:
			msg['fields'] = self.fields
		msg['fallback'] = self.title_link
		msg['mrkdwn_in'] = [x for x in msg.keys() if not x == 'color']
		return [msg]

class UpdateUserEvent(MessageEvent):
	type = ETYPES.USER
	@property
	def key(self):
		return self._get('key')
	
	@property
	def value(self):
		return self._get('value')

class UserUpdatedEvent(MessageEvent):
	type = ETYPES.USER

class CollectInfoEvent(MessageEvent):
	type = ETYPES.USER

class UserRegisteredEvent(MessageEvent):
	type = ETYPES.USER

class GameEvent(Event):
	type = ETYPES.GAME
	@property
	def users(self):
		return self._get('users', [])

	@property
	def game(self):
		return self._get('game')

class StartGameEvent(GameEvent):
	pass

class SetupGameEvent(GameEvent):
	pass

class LockUsersEvent(GameEvent):
	pass

class AssignInitialHitsEvent(GameEvent):
	pass

class CheckFreeEvent(Event):
	type = ETYPES.CRON

class AssignmentNotifyEvent(Event):
	type = ETYPES.MSG
	@property
	def game(self):
		return self._get('game')

	@property
	def user(self):
		return self._get('user')

class AssignNextRoundEvent(GameEvent):
	pass

class CheckForWinnerEvent(GameEvent):
	pass

class KillConfirmedEvent(Event):
	type = ETYPES.GAME
	@property
	def game(self):
		return self._get('game')

	@property
	def user(self):
		return self._get('user')

class ConfirmKillEvent(KillConfirmedEvent):
	pass

class ConfirmKillMessageEvent(MessageEvent):
	pass

class EndGameEvent(Event):
	type = ETYPES.GAME
	@property
	def game(self):
		return self._get('game')

	@property
	def winner(self):
		return self._get('winner')



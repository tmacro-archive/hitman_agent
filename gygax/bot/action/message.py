from ..const import EVENT_TYPES as ETYPES
from ...util.log import getLogger
from ...app import slack as SlackApi
from .base import Action
from ...api.storage import get_user
from ..events import SendMessageEvent, StructuredMessageEvent
from ...util.config import config
_log = getLogger('action.message')

class SendMessageAction(Action):
	log = _log
	def _install(self, proxy):
		proxy.register(ETYPES.MSG, 'msg_send', self)

	def _process(self, event):
		self._log.debug('Received outbound message event to %s'%event.user)
		if not event.text:
			self._log.error('Outbound message has no text!')
			return
		if event.channel:
			ok = SlackApi.msg(event.channel, event.text)
		else:
			ok = SlackApi.dm(event.user, event.text)
		if ok:
			self._log.debug('Successfully sent message to %s'%event.user)
		else:
			self._log.debug('Failed to send message to %s'%event.user)

class StructuredMessageAction(Action):
	def _install(self, proxy):
		proxy.register(ETYPES.MSG, 'msg_structured', self)

	def _process(self, event):
		self._log.debug('Received outbound stuctured message event to %s'%event.user)
		if not event.attachments:
			self._log.error('Stuctured message has no body!')
			return
		if event.channel:
			ok = SlackApi.msg(event.channel, attach = event.attachments, message = event.text)
		else:
			ok = SlackApi.dm(event.user, attach = event.attachments, message = event.text)
		if ok:
			self._log.debug('Successfully sent structured message to %s'%event.user)
		else:
			self._log.debug('Failed to send structured message to %s'%event.user)

class AssignmentNotifyAction(Action):
	log = _log
	def _install(self, proxy):
		proxy.register(ETYPES.MSG, 'msg_assignment', self)
	
	def _process(self, event):
		self._log.debug('Notifying %s of target'%event.user)
		with get_user(slack=event.user) as user:
			if user:
				hit = user.assigned
				# return SendMessageEvent('msg_send', dict(user=event.user, template=config.resp.new_assignment,
				# 									 args=dict(target=hit.target.uid, weapon=hit.weapon.desc,
				# 									 			location=hit.location.desc)))
				fields = (('Target',hit.target.uid), ('Weapon',hit.weapon.desc), ('Location', hit.location.desc))
				fields = [dict(title=x[0], value=x[1]) for x in fields]
				return StructuredMessageEvent('msg_structured', dict(user=event.user,
																content=config.resp.new_assignment.content,
																fields=fields))

class KillConfirmMessageAction(Action):
	def _install(self, proxy):
		proxy.register(ETYPES.MSG, 'msg_confirmation', self)

	def _process(self, event):
		self._log.debug('Received KillConfirmationMessageEvent')
		with get_user(slack=event.user) as user:
			if user:
				hit = user.targeted
				fields = [dict(title=x[0], value=x[1]) for x in [('Weapon', hit.weapon.desc),('Location', hit.location.desc)]]
				return StructuredMessageEvent('msg_structured', dict(user=event.user,
												title=config.resp.kill_confirm.title,
												content=config.resp.kill_confirm.content,
												fields = fields
												))
				# return SendMessageEvent('msg_send', dict(user=event.user, template=config.resp.kill_confirm,
				# 										args=dict(hitman=hit.hitman.uid, weapon=hit.weapon.desc,
				# 													location=hit.location.desc)))
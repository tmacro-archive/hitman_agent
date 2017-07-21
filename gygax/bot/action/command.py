from ...util.log import getLogger
from .base import Action
from ..const import CMD_TYPES as CTPYES
from ..const import EVENT_TYPES as ETYPES
from ..const import HIT_STATUS as HSTATUS
from ..events import SlackValidationEvent, CommandEvent, SendMessageEvent, UpdateUserEvent, SetupGameEvent, StructuredMessageEvent, KillConfirmedEvent, ConfirmKillEvent
from ...api.storage import create_user, get_user, get_hit, session_scope
from ...util.config import config
from ...models import Slack
_log = getLogger('action.command')

class CommandAction(Action):
	'''
		This action processes a raw command and 
		pushes the generated event onto the queue
	'''
	log = _log
	def _install(self, proxy):
		proxy.register(ETYPES.CMD, 'cmd_raw', self)

	def _process(self, event):
		self._log.debug('Processing raw command')
		print(event.data())
		if event.cmd_type == 'bang' and event.public:
			self._log.debug('bang command on public channel')
			return
		if event.cmd and event.valid:
			ev = CommandEvent('cmd_%s'%event.cmd, event.data(), no_parse = True)
			self._log.debug('CommandEvent validated setting topic to %s and pushing to queue'%ev.topic)
			self._put(ev)
			return True

class RegisterCommand(Action):
	log = _log
	def _install(self, proxy):
		proxy.register(ETYPES.CMD, 'cmd_register', self)
	
	def _process(self, event):
		self._log.debug('Received registration command for user %s'%event.user)
		with get_user(slack = event.user) as user:
			if user:
				if not user.slack.confirmed:
					self._log.debug('Pushing SlackValidationEvent for %s'%event.user)
					return SlackValidationEvent('user_validate', dict(user=event.user))
				else:
					self._log.debug('user %s already in database'%event.user)
					return SendMessageEvent('msg_send', dict(user=event.user, text=config.resp.already_registered))
		create_user(slack = event.user)
		self._log.info('Created account for %s'%event.user)
		return self._process(event)		

class SetCommand(Action):
	log = _log
	def _install(self, proxy):
		proxy.register(ETYPES.CMD, 'cmd_set', self)

	def _process(self, event):
		self._log.debug('Received set info command from user %s'%event.user)
		if not event.args or len(event.args) < 2:
			# return SendMessageEvent('msg_send', dict(user=event.user, text = config.resp.info_set_usage))
			return StructuredMessageEvent('msg_structured', dict(user = event.user,
																pretext = config.resp.info_set_usage.pretext
																title=config.resp.info_set_usage.title,
																content=config.resp.info_set_usage.content,
																field=config.resp.info_set_usage.fields
																))
		target = event.args[0]
		if not target in ['weapon', 'location']:
			return SendMessageEvent('msg_send', dict(user=event.user, text = config.resp.info_set_usage))
		value = ' '.join(event.args[1:])
		self._log.debug("Pushing update event for %s to %s for user %s"%(target, value, event.user))
		return UpdateUserEvent('user_update', dict(user=event.user, key=target, value=value))

class ReportCommand(Action):
	log = _log
	def _install(self, proxy):
		proxy.register(ETYPES.CMD, 'cmd_report', self)

	def _process(self, event):
		self._log.debug('Received report kill command from user %s'%event.user)
		with session_scope() as session:
			slack = session.query(Slack).filter_by(slack_id = event.user).first()
			user = slack.user if slack else None
			if user and user.assigned:
				if user.assigned.status == HSTATUS.ACTIVE and (user.targeted.status == HSTATUS.ACTIVE or user.targeted.status == HSTATUS.OPEN):
					hit = user.assigned
					hit.status = HSTATUS.PENDING
					session.add(hit)
					return [
							ConfirmKillEvent('game_confirm', dict(user=hit.target.slack.slack_id, game=hit.game.uuid)),
							SendMessageEvent('msg_send', dict(user=event.user, text='Your report has been recieved and is awaiting confirmation from your target'))
							]
				elif not user.assigned.status == HSTATUS.ACTIVE and (user.targeted.status == HSTATUS.ACTIVE or user.targeted.status == HSTATUS.OPEN):
					self._log.warning('Hit not set as OPEN')
					return SendMessageEvent('msg_send', dict(user=event.user, text='This hit is already pending, please wait until your traget responds'))
				elif user.assigned.status == HSTATUS.ACTIVE and not (user.targeted.status == HSTATUS.ACTIVE or user.targeted.status == HSTATUS.OPEN):
					self._log.warning('User reported while their status is PENDING')
					return SendMessageEvent('msg_send', dict(user=event.user, text='Someone has reported that they have killed you\n You can not report a kill until that matter is settled.'))
			else:
				return SendMessageEvent('msg_send', dict(user=event.user, text="I don't know who you killed, but you're not assigned any hits right now..."))
				self._log.error('Unable to find user %s'%event.user)

class ConfirmCommand(Action):
	log = _log
	def _install(self, proxy):
		proxy.register(ETYPES.CMD, 'cmd_confirm', self)

	def _process(self, event):
		self._log.debug('Received confirm kill command from %s'%event.user)
		with get_hit(target = event.user) as hit:
			if hit and hit.status == HSTATUS.PENDING:
				return [
						SendMessageEvent('msg_send', dict(user=event.user, text='Your have confirmed your death.')),
						KillConfirmedEvent('game_confirmed', dict(user=event.user, game=hit.game.uuid))
						]
			elif not hit or not hit.status == HSTATUS.PENDING:
				return SendMessageEvent('msg_send', dict(user=event.user, text="I'm not sure what your trying to confirm here..."))
				# return SendMessageEvent('msg_send', dict(user=event.user, text='You have denied that someone has killed you'))
		

class HelpCommand(Action):
	log = _log
	pass # This is 42, you must find your own

class HitsCommand(Action):
	log = _log
	pass

class ResignCommand(Action):
	log = _log
	pass

class RejoinCommand(Action):
	log = _log
	pass

class HelpCommand(Action):
	log = _log
	def _install(self, proxy):
		proxy.register(ETYPES.CMD, 'cmd_help', self)

	def _process(self, event):
		return [SendMessageEvent('msg_send', dict(channel = event.channel, text = config.resp.help))]

class TestCommand(Action):
	def _install(self, proxy):
		proxy.register(ETYPES.CMD, 'cmd_test', self)

	def _process(self, event):
		return [SetupGameEvent('game_setup')]
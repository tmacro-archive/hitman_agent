from ...util.log import getLogger
from .base import Action
from ..const import CMD_TYPES as CTPYES
from ..const import EVENT_TYPES as ETYPES
from ..const import USER_STATUS as USTAT
from ..events import SendMessageEvent, UserRegisteredEvent, CollectInfoEvent, UserUpdatedEvent, StructuredMessageEvent
from ...api.storage import validate_slack, set_weapon, set_location, info_locked, profile_is_complete, check_profile_completion, set_status, get_user
from ...api import auth as AuthApi
from ...util.config import config

_log = getLogger('action.user')

class UpdateUserAction(Action):
	log = _log
	def _install(self, proxy):
		proxy.register(ETYPES.USER, 'user_update', self)

	def _process(self, event):
		self._log.debug('Received update info event for user %s'%event.user)
		if info_locked(event.user):
			return SendMessageEvent('msg_send', dict(user=event.user, text = "You can't update your %s in the middle of a game!"%event.key))
		self._log.debug("Updating %s's %s to %s"%(event.user, event.key, event.value))
		ok = True
		if event.key == 'weapon':
			if not set_weapon(event.user, event.value):
				ok = False
		elif event.key == 'location':
			if not set_location(event.user, event.value):
				ok = False
		if ok:
			return (SendMessageEvent('msg_send', dict(
						user=event.user, 
						template = config.resp.info_set_confirm, 
						args = dict(key=event.key, value=event.value))),
					UserUpdatedEvent('user_updated', dict(user=event.user)))
		else:
			return SendMessageEvent('msg_send', dict(user=event.user,
												text = 'There was a probem updating your %s, please try again'%event.key))

class ValidateSlackAction(Action):
	'''
		This actions checks if a slack user needs authorizing,
		if so it querys the auth service for a validation url,
		then push a message to the slack user containg the url
	'''
	def _install(self, proxy):
		proxy.register(ETYPES.USER, 'user_validate', self)

	def _process(self, event):
		self._log.debug('Received slack validation event for %s'%event.user)
		if event.validated:
			if validate_slack(event.user, event.uid):
				with get_user(slack=event.user) as user:
					self._log.info('Successfully linked 42 uid %s with slack %s'%(user.uid, user.slack.name))
					self._put(SendMessageEvent('msg_send', dict(user=event.user, 
										template=config.resp.registration_success,
										args=dict(uid=user.uid))))
				self._put(CollectInfoEvent('user_info', dict(user=event.user)))
			else:
				self._log.error('Failed to link 42 uid %s with slack %s'%(event.uid, event.user))
		elif not event.validated and event.failed:
			self._log.error('Failed to validate slack user %s, they probably denied our oauth request'%event.user)
		else:
			self._log.debug('Generating validation url for %s'%event.user)
			uid, url = AuthApi.validate_user(event.user)
			if not url and not uid:
				self._log.error('Failed to retrieve validation url for slack user %s'%event.user)
				ev = SendMessageEvent('msg_send', dict(user=event.user, text=config.resp.register_error))
			elif url:
				self._log.debug('Retrieved vaidation url for %s'%event.user)
				ev = StructuredMessageEvent('msg_structured', dict(user=event.user, content=config.resp.validation, title='Sign in with Intra', title_link=url))			
				# ev = SendMessageEvent('msg_send', dict(user=event.user, template=config.resp.validation, args=dict(url=url)))
			elif uid:
				self._log.debug('slack user %s is already authenticated'%event.user)
				validate_slack(event.user, uid)
				ev = SendMessageEvent('msg_send', dict(user=event.user, text=config.resp.already_registered))				
			self._put(ev)

class CollectInfoAction(Action):
	def _install(self, proxy):
		proxy.register(ETYPES.USER, 'user_info', self)
		proxy.register(ETYPES.USER, 'user_updated', self)
	def _process(self, event):
		if event.topic == 'user_info':
			self._log.debug('Received info collection event for user %s'%event.user)
			# ev = SendMessageEvent('msg_send', dict(user=event.user, text = config.resp.collect_info))
			ev = StructuredMessageEvent('msg_structured', dict(user = event.user, 
																content = config.resp.collect_info.content,
																fields = config.resp.collect_info.fields
																))
			self._put(ev)			
		elif event.topic == 'user_updated':
			if not profile_is_complete(event.user):
				if check_profile_completion(event.user):
					ev = UserRegisteredEvent('user_registered', dict(user=event.user))
					self._put(ev)

class NewUserAction(Action):
	def _install(self, proxy):
		proxy.register(ETYPES.USER, 'user_registered', self)

	def _process(self, event):
		set_status(event.user, USTAT.FREE)
		return [SendMessageEvent('msg_send', dict(user=event.user, text=config.resp.new_user))]
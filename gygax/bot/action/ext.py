from ...util.log import getLogger
from ...util.http import http
from ..events import SlackValidationEvent
from .base import Action
from ...app import agent
_log = getLogger('action.ext')

class SlackAuthorizedAction(Action):
	'''
		This action monitors an http endpoint,
		and pushes a user validation event upon acivity
	'''
	@http.route('/slack_authorized', methods = ['POST'], params = True)
	def _process(data = None, params = None):
		_log.debug('Received notification of slack validation')
		if params:
			data = dict(
				user = params.get('user'),
				valid = params.get('valid'),
				uid = params.get('uid'),
				failed = not params.get('valid')
			)
			if data['user'] and (not data['valid'] or data['uid']):
				ev = SlackValidationEvent('user_validate', data)
				agent.put(ev)
				_log.debug('Received slack validation for user %s 42 uid %s'%(ev.user, ev.uid))
		_log.warning('Malformed request from authentication server')
from ...util.log import getLogger
from ...util.config import config
from ...util.game import Hitman
from .base import Action
from ..const import CMD_TYPES as CTPYES
from ..const import EVENT_TYPES as ETYPES
from ..const import USER_STATUS as USTAT
from ..const import HIT_STATUS as HSTAT
from ..events import SendMessageEvent, UserRegisteredEvent, CollectInfoEvent, UserUpdatedEvent, StartGameEvent, SetupGameEvent, LockUsersEvent, AssignInitialHitsEvent, CheckFreeEvent, AssignmentNotifyEvent, AssignNextRoundEvent, KillConfirmedEvent, ConfirmKillMessageEvent, CheckForWinnerEvent, EndGameEvent, StructuredMessageEvent
from ...api.storage import get_free_users, lock_user, create_hit, create_game, set_status, get_game, session_scope, get_hit
from ...models import Game, Hit
import random

_log = getLogger('action.game')


class MonitorFreeAction(Action):
	def _install(self, proxy):
		proxy.register(ETYPES.USER, 'user_registered', self)
		proxy.register(ETYPES.CRON, 'cron_check_free', self)
		proxy.schedule(CheckFreeEvent('cron_check_free'), config.game.check_interval, 'cron_check_free', repeat = True)

	def _process(self, event):
		users = get_free_users()
		if len(users) >= config.game.size:
			self._log.info('Enough free players available. Starting a new game.')
			self._put(SetupGameEvent('game_setup'))

class SetupGameAction(Action):
	def _install(self, proxy):
		proxy.register(ETYPES.GAME, 'game_setup', self)

	def _process(self, event):
		uuid, slacks = create_game()
		if slacks:
			self._log.debug('Created game with %s'%slacks)
			self._schedule(LockUsersEvent('cron_lock', dict(users = slacks, game=uuid)), config.game.lockout, uuid)
			for u in slacks:
				set_status(u, USTAT.WAITING)
				self._put(SendMessageEvent('msg_send', dict(user=u, template=config.resp.game_starting,
														args = dict(lockout=config.game.lockout))))
				self._put(StructuredMessageEvent('msg_structured', dict(user=u, 
												content=config.resp.game_starting.content,
												title=config.resp.game_starting.title)))

class LockUsersAction(Action):
	def _install(self, proxy):
		proxy.register(ETYPES.GAME, 'cron_lock', self)
	
	def _process(self, event):
		self._log.debug('Locking users in prepartion for game')
		passed = True
		for user in event.users:
			if not lock_user(user):
				passed = False
		if passed:
			self._put(AssignInitialHitsEvent('game_assign_initial', event.data()))
			return [SendMessageEvent('msg_send', dict(user=u, text=config.resp.user_locked)) for u in event.users]
		raise Exception('Failed to lock all users for game %s'%game.uuid)

class AssignInitialHitsAction(Action):
	def _install(self, proxy):
		proxy.register(ETYPES.GAME, 'game_assign_initial', self)

	def _process(self, event):
		self._log.debug('Assigning initial hits for game %s'%event.game)
		with session_scope() as session:
			game  = session.query(Game).filter_by(uuid=event.game).first()
			if game:
				assignments = Hitman.create_game(game.players, game.weapons, game.locations)
				for user, hit in assignments.items():
					h = Hit(user, *hit, game)
					session.add(h)
				return StartGameEvent('game_start', dict(users = event.users, game = event.game))
			else:
				self._log.error('Unable to load game %s'%event.game)

class StartGameAction(Action):
	def _install(self, proxy):
		proxy.register(ETYPES.GAME, 'game_start', self)

	def _process(self, event):
		self._log.debug('Starting game %s'%event.game)
		for user in event.users:
			set_status(user, USTAT.INGAME)
			self._put(AssignmentNotifyEvent('msg_assignment', dict(user=user, game=event.game)))
		self._schedule(AssignNextRoundEvent('game_assign_next', dict(game=event.game)), '23:42', key = event.game + '_assign_next', repeat = True)
		# self._schedule(AssignNextRoundEvent('game_assign_next', dict(game=event.game)), '1m', key = event.game + '_assign_next', repeat = True)

class ConfirmKillAction(Action):
	def _install(self, proxy):
		proxy.register(ETYPES.GAME, 'game_confirm', self)

	def _process(self, event):
		self._log.debug('Received ConfirmKillEvent for %s'%event.user)
		key = '%s_%s_auto_confirm'%(event.user, event.game)
		self._schedule(KillConfirmedEvent('game_confirmed', dict(user=event.user, game=event.game)), '12h', key=key)
		return ConfirmKillMessageEvent('msg_confirmation', dict(user=event.user))

class KillConfirmedAction(Action):
	def _install(self, proxy):
		proxy.register(ETYPES.GAME, 'game_confirmed', self)

	def _process(self, event):
		self._log.debug('Received KillConfirmedAction from %s'%event.user)
		self._cancel('%s_%s_auto_confirm'%(event.user, event.game))
		with get_hit(target = event.user) as hit:
			hit.status = HSTAT.CONFIRMED
			user = hit.hitman.slack.slack_id
		with get_hit(hitman = event.user) as hit:
			hit.status = HSTAT.OPEN
		set_status(event.user, USTAT.DEAD)
		set_status(user, USTAT.STANDBY)
		return [
				SendMessageEvent('msg_send', dict(user=user, text='Your target has confirmed your kill')),
				CheckForWinnerEvent('game_check_winner', dict(game=event.game))
			]

class AssignNextRoundAction(Action):
	def _install(self, proxy):
		proxy.register(ETYPES.GAME, 'game_assign_next', self)

	def _process(self, event):
		with session_scope() as session:
			game = session.query(Game).filter_by(uuid = event.game).first()
			if game and game.open_hits:
				assigned = self._assign_hits(game.free_players, game.open_hits)
				if assigned:
					for player, hit in assigned.items():
						hit.hitman = player
						hit.status = HSTAT.ACTIVE
						session.add(hit)
						set_status(player.slack.slack_id, USTAT.INGAME)
						self._put(AssignmentNotifyEvent('msg_assignment', dict(user=player.slack.slack_id, game=event.game)))
				else:
					self._log.warning('No suitable hits available for assignment')
			elif game and not game.open_hits:
				self._log.debug('No open hits, not assigning')
			else:
				self._log.warning('Unable to locate game %s'%event.game)

	def _assign_hits(self, players, hits):
		assigned = {}
		players = players[:]	# Shorthand to copy a list
		hits = hits[:]			# This is so we can list.remove() without modifying the list and 
		player = players[0]		# effecting the function one step up in the call chain
		while True:
			h = random.choice(hits) # Choose a random hit
			if h.target != player:  # You can't be assigned yourself, so check that
				assigned[player] = h
				hits.remove(h)			# Remove the chosen hit
				players.remove(player)	# and player from their respective lists
				if len(players) > 0:	#space%2Fauth%2Fauthorized If there are any remaining hits/players
					ret = self._assign_hits(players, hits) # Recurse to assign the remaining
					if ret:	# If we were able to assign the remaining hits
						assigned.update(ret)	# Update the assigned dict
						return assigned			# And return it
					else: # If we couldnt assign the rest of the hits, probably because there was only one left and hit.target == player
						hits.append(h)			# Add the player
						players.append(player)	# and the chosen hit back to the list
				else:					# If there are no remaining payers/hits
					return assigned		# return assigned
			elif h.target == player and len(players) == 1:	# If target == player and its the only one left
				return None									# Then return None, and redo the previous step
		# If we make it here then target == player, but there a more to choose from so we loop and try again

class CheckForWinnerAction(Action):
	def _install(self, proxy):
		proxy.register(ETYPES.GAME, 'game_check_winner', self)

	def _process(self, event):
		with get_game(event.game) as game:
			remaining = game.remaining_players
			if len(remaining) == 1:
				self._log.info('One player remaining, %s is the winner!'%remaining[0].uid)
				self._cancel(event.game + '_assign_next')
				return EndGameEvent('game_end', dict(game=event.game, winner=remaining[0].uid))


class EndGameAction(Action):
	def _install(self, proxy):
		proxy.register(ETYPES.GAME, 'game_end', self)

	def _process(self, event):
		self._log.debug('Recieved EndGameEvent, notifying players of winner, and cleaning up game records')
		with session_scope() as session:
			game = session.query(Game).filter_by(uuid=event.game).first()
			for hit in game.hits:
				session.delete(hit)
			for player in game.players:
				player.status = USTAT.FREE
				session.add(player)
				self._put(SendMessageEvent('msg_send', dict(user=player.slack.slack_id, text='This game of ft_hitman is over!\n %s has emerged victorious!'%event.winner)))
			session.delete(game)



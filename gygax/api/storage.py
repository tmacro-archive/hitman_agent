from contextlib import contextmanager
from ..models import User, Weapon, Location, Slack, Game, Hit, Schedule
from ..app import Session
from ..util.log import getLogger
from ..util.conv import make_list
from ..bot.const import USER_STATUS as USTAT
from ..bot.const import HIT_STATUS as HSTAT
from ..util.config import config
from sqlalchemy.exc import IntegrityError

_log = getLogger(__name__)

@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations."""
    session = Session()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()

@contextmanager
def get_user(slack = None, uid = None):
	with session_scope() as session:
		if slack:
			s = session.query(Slack).filter_by(slack_id = slack).first()
			user = s.user if s else None
		elif uid:
			user = session.query(User).filter_by(uid = uid).first()
		else:
			_log.error('Not enough args to fetch user')
			user = None
		yield user
		if user:
			session.add(user)

@contextmanager
def get_game(uuid):
	with session_scope() as session:
		game = session.query(Game).filter_by(uuid = uuid).first()
		if not game:
			game = None
		yield game
		if game:
			session.add(game)

@contextmanager
def get_hit(hitman = None, target = None):
	with session_scope() as session:
		slack_id = hitman if hitman else target
		slack = session.query(Slack).filter_by(slack_id = slack_id).first()
		user = slack.user if slack else None
		hit = None
		if user:
			if hitman:
				hit = user.assigned
			else:
				hit = user.targeted
		yield hit
		if hit:
			session.add(hit)

def confirm_hit(tslack):
	with session_scope() as session:
		user = session.query(User).filter(User.slack.slack_id == tslack)
		for hit in user.hits:
			if hit.status == HSTAT.PENDING:
				hit.status = HSTAT.CONFIRMED
				return True
	return False
	

def create_user(**kwargs):
	with session_scope() as session:
		u = User(**kwargs)
		session.add(u)
		return u.slack_id
		
def set_weapon(slack, weapon):
	with get_user(slack=slack) as user:
		if user:
			if not user.weapon:
				w = Weapon(weapon)
				user.weapon = w
			else:
				w = user.weapon
				w.desc = weapon
			return True
	return False
	

def set_location(slack, location):
	with get_user(slack=slack) as user:
		if user:
			if not user.location:
				l = Location(location)
				user.location = l
			else:
				l = user.location
				l.desc = location
			return True
	return False


def set_status(slack, status):
	with get_user(slack = slack) as user:
		if user:
			user.status = status
			return True
	return False



def validate_slack(slack, uid = None):
	with get_user(slack = slack) as user:
		if user and not user.slack.confirmed:
			user.slack.confirmed = True
			user.uid = uid
			return True
	return False

def lock_user(slack):
	with get_user(slack=slack) as user:
		if user:
			user.locked = True
	return True

def info_locked(slack):
	with get_user(slack=slack) as user:
		return user.locked if user else None

def profile_is_complete(slack):
	with get_user(slack=slack) as user:
		return user.complete if user else None

def check_profile_completion(slack):
	with get_user(slack=slack) as user:
		if user and user.weapon and user.location:
			user.complete = True
			return True
	return False

def create_game(size = config.game.size):
	with session_scope() as session:
		users = session.query(User).filter_by(status = USTAT.FREE).order_by(User.last_game).limit(size).all()
		if len(users) >= config.game.size:
			g = Game()
			for user in users:
				g.players.append(user)
				session.add(user)
			session.add(g)
			return g.uuid, [p.slack.slack_id for p in users]
	return None, None

def get_free_users():
	with session_scope() as session:
		query = session.query(User)
		filtered = query.filter_by(status = USTAT.FREE)
		ordered = filtered.order_by(User.last_game)
		return ordered.all()

def create_hit(hitman, target, weapon, location):
	with session_scope() as session:
		h = Hit(hitman, target, weapon, location)
		session.add(h)

def load_schedule():
	with session_scope() as session:
		for e in session.query(Schedule).all():
			yield e.event, e.delay, e.uuid, e.repeat, e.time	

def add_to_schedule(event, delay, key, repeat, time):
	try:
		with session_scope() as session:
			s = Schedule(event, delay, key, repeat, time)
			session.add(s)
	except IntegrityError:
		with session_scope() as session:
			s = session.query(Schedule).filter_by(uuid = key).first()
			s.event = event
			s.delay = delay
			s.repeat = repeat
			s.time = time
			session.add(s)

def remove_from_schedule(key):
	with session_scope() as session:
		session.query(Schedule).filter_by(uuid = key).delete()
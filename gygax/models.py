from sqlalchemy import Column, Integer, String, ForeignKey, Table, Text, Boolean, DateTime
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from collections import namedtuple
from .app import Session
from .api.slack import Slack as SlackApi
from .util.crypto import rand_key
from .bot.const import HIT_STATUS as HSTAT
from .bot.const import USER_STATUS as USTAT

Base = declarative_base()

game_players = Table('game_players', Base.metadata,
				Column('user_id', Integer, ForeignKey('user.id')),
				Column('game_id', Integer, ForeignKey('game.id')))

class Query:
	@property
	def query(self):
		return Session().query(self.__class__)

class Slack(Base, Query):
	__tablename__ = 'slack'
	id = Column(Integer, primary_key = True)
	name = Column(String(32))
	slack_id = Column(String(64), unique = True)
	confirmed = Column(Boolean, default = False)
	updated  = Column(DateTime(), default=datetime.utcnow)

	def __init__(self, slack):
		self.slack_id = slack
		info = SlackApi._get_user_info(slack)
		self.name = info['name'] if info else None

	snapshot_type = namedtuple('Slack', ['slack_id','name','confirmed','updated'])
	@property
	def snapshot(self):
		return self.snapshot_type(self.slack_id, self.name, self.confirmed, self.updated)

class User(Base, Query):
	__tablename__ = 'user'
	id = Column(Integer, primary_key = True)
	uid = Column(Text, unique = True)
	key = Column(String(128))
	secret = Column(String(128))
	ft_oauth_key = Column(String(64))
	ft_oauth_refresh = Column(String(64))
	slack_id = Column(Integer, ForeignKey('slack.id'))
	slack = relationship("Slack", backref=backref("user", uselist=False))
	complete = Column(Boolean, default = False)
	locked = Column(Boolean, default = False)
	status = Column(Integer, default = 0)
	last_game = Column(DateTime())
	
	def __init__(self, uid = None, slack = None):
		if not uid and not slack:
			raise Exception('You must provide either uid or slack')
		if uid:
			self.uid = uid
		if slack:
			self.slack = Slack(slack)
		self.key = rand_key()
		self.secret = rand_key()

	def check(self, pwd):
		return hashlib.sha256(pwd).hexdigest() == self.pwd

	@staticmethod
	def from_uid(uid):
		return User.query.filter_by(uid = uid).first()

	@staticmethod
	def from_slack(slack):
		return User.query.filter_by(slack = slack).first()

	snapshot_type = namedtuple('User', ['uid', 'key', 'secret', 'ft_oauth_key', 'ft_oauth_refresh',
										'slack_id', 'slack', 'complete', 'status', 'last_game', 'assigned',
										'weapon', 'location'])
	@property
	def snapshot(self):
		pass

class Location(Base, Query):
	__tablename__ = 'location'
	id = Column(Integer, primary_key = True)
	desc = Column(Text)
	user_id = Column(Integer, ForeignKey('user.id'))
	user = relationship("User", backref=backref("location", uselist=False))
	def __init__(self, desc):
		self.desc = desc

class Weapon(Base, Query):
	__tablename__ = 'weapon'
	id = Column(Integer, primary_key = True)
	desc = Column(Text)
	user_id = Column(Integer, ForeignKey('user.id'))
	user = relationship("User", backref=backref("weapon", uselist=False))
	def __init__(self, desc):
		self.desc = desc

class Hit(Base, Query):
	__tablename__ = 'hit'
	id = Column(Integer, primary_key = True)
	target_id = Column(Integer, ForeignKey('user.id'))
	target = relationship('User', backref=backref('targeted', uselist=False), uselist=False, foreign_keys=[target_id])
	hitman_id = Column(Integer, ForeignKey('user.id'))
	hitman = relationship('User', backref=backref('assigned', uselist=False), uselist=False, foreign_keys=[hitman_id])
	weapon_id = Column(Integer, ForeignKey('weapon.id'))
	weapon = relationship('Weapon')
	location_id = Column(Integer, ForeignKey('location.id'))	
	location = relationship('Location')
	game_id = Column(Integer, ForeignKey('game.id'))
	game = relationship('Game', backref='hits')
	conf_code = Column(String(16))
	status = Column(Integer, default = 0)

	def __init__(self, hitman, target, weapon, location, game):
		self.hitman = hitman
		self.target = target
		self.weapon = weapon
		self.location = location
		self.game = game

class Game(Base, Query):
	__tablename__ = 'game'
	id = Column(Integer, primary_key = True)
	players = relationship('User', secondary = game_players, backref = backref('game', uselist=False))
	uuid = Column(String(128))

	def __init__(self):
		self.uuid = rand_key()

	@property
	def weapons(self):
		return [p.weapon for p in self.players]

	@property
	def locations(self):
		return [p.location for p in self.players]

	@property
	def open_hits(self):
		return [h for h in self.hits if h.status == HSTAT.OPEN]

	@property
	def free_players(self):
		return [p for p in self.players if p.status == USTAT.STANDBY]

	@property
	def remaining_players(self):
		return [p for p in self.players if p.status != USTAT.DEAD]
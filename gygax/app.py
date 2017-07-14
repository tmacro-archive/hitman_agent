from .util.config import config
import sqlalchemy
from sqlalchemy.orm import sessionmaker

# Create database
uri = '{driver}{user}:{password}@{path}'.format(**config.storage._asdict())
db = sqlalchemy.create_engine(uri, echo = False)

Session = sessionmaker()
Session.configure(bind = db)

from .models import Base
Base.metadata.bind = db

from .bot.agent import Agent
from .api.slack import Slack

agent = Agent()
# agent.start()

# app.start()
slack = Slack(agent.put)

from .bot.action import all_actions

actions = [a(agent.proxy) for a in all_actions]


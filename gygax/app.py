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

from .api.slack import Slack
slack = Slack()

from .bot.agent import Agent

agent = Agent()

slack.register_output_handler(agent.put)
# agent.start()
from .bot.action import all_actions
agent.register_actions(all_actions)
# actions = [a(agent.proxy) for a in all_actions]

# app.start()




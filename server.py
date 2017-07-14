import signal
import sys
from gygax.app import agent, slack, db
from gygax.util.http import http
import time

def start_agent():
	agent.start()
	slack.start()
	http.start()

def sig_handler(sig, frame):
	slack.stop()
	agent.join(10)
	sys.exit(0)

if __name__ == '__main__':
	signal.signal(signal.SIGINT, sig_handler)
	signal.signal(signal.SIGTERM, sig_handler)
	# create_tables()
	start_agent()
	while True:
		time.sleep(30)

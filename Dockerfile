FROM tmacro/python:3

ENV PORT 80
ENV MODE prod
ADD ./requirements.txt /tmp/
RUN apk_add zeromq py3-zmq py3-psycopg2 && \
	pip install -r /tmp/requirements.txt

ADD s6 /etc

ADD . /app


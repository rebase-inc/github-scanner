import rsyslog
import logging
from os import environ
from multiprocessing import current_process

from redis import StrictRedis
from rq import Worker, Queue, Connection

rsyslog.setup()
LOGGER = logging.getLogger(__name__)
current_process().name = environ['HOSTNAME']

try:
    with Connection(StrictRedis(host = 'redis', port = 6379)):
        worker = Worker(environ['HOSTNAME'])
        worker.work(logging_level = environ['LOG_LEVEL'])
except Exception as exc:
    LOGGER.exception('Unhandled exception!')
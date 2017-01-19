import signal
import rsyslog
import logging
from os import environ
from multiprocessing import current_process

from redis import StrictRedis
from rq import Worker, Queue, Connection

current_process().name = environ['HOSTNAME']
rsyslog.setup(log_level = environ['LOG_LEVEL'])
LOGGER = logging.getLogger()

class QuickKillWorker(Worker):
    def execute_job(self, job, queue):
        super().execute_job(job, queue)
        signal.signal(signal.SIGINT, self.request_force_stop)
        signal.signal(signal.SIGTERM, self.request_force_stop)

try:
    with Connection(StrictRedis(host = 'redis', port = 6379)):
        worker = QuickKillWorker(environ['HOSTNAME'])
        worker.work(logging_level = environ['LOG_LEVEL'])

except Exception as exc:
    LOGGER.exception('Unhandled exception!')

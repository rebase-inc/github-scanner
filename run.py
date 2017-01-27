import os
import signal
import rsyslog
import logging
import multiprocessing

from redis import StrictRedis
from rq import Worker, Queue, Connection

multiprocessing.current_process().name = os.environ['HOSTNAME']
rsyslog.setup(log_level = os.environ['LOG_LEVEL'])

class QuickKillWorker(Worker):
    def execute_job(self, job, queue):
        super().execute_job(job, queue)
        signal.signal(signal.SIGINT, self.request_force_stop)
        signal.signal(signal.SIGTERM, self.request_force_stop)

if __name__ == '__main__':
    try:
        with Connection(StrictRedis(host = 'redis', port = 6379)):
            worker = QuickKillWorker(os.environ['HOSTNAME'])
            worker.work(logging_level = os.environ['LOG_LEVEL'])

    except Exception as exc:
        LOGGER.exception('Unhandled exception!')

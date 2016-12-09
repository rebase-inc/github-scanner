from os import environ
from multiprocessing import current_process

import rsyslog
from redis import Redis, ConnectionPool
from rq import Worker, Queue, Connection

# IMPORT HERE ANY PACKAGES THE QUEUE WILL NEED

current_process().name = environ['HOSTNAME']
pool = ConnectionPool(host='redis', max_connections=1)

with Connection(Redis(connection_pool = pool)):
    queue = Queue(environ['HOSTNAME'])
    worker = Worker(queue)
    current_process().name = environ['HOSTNAME'] + worker.name[0:5]
    worker.work(logging_level = environ['LOG_LEVEL'])

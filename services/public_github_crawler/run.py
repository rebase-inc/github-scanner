from os import environ
from multiprocessing import current_process

import rsyslog
from redis import StrictRedis
from rq import Worker, Queue, Connection

# IMPORT HERE ANY PACKAGES THE QUEUE WILL NEED
#from ..github.crawl.jobs import create_personal_access_token

rsyslog.setup()
current_process().name = environ['HOSTNAME'] 

with Connection(StrictRedis(host = 'redis', port = 6379)):
    worker = Worker(environ['HOSTNAME'])
    #create_personal_access_token()
    worker.work(logging_level = environ['LOG_LEVEL'])

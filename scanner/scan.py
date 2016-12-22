import re
import os
import time
import json
import pickle
import bisect
import rsyslog
import logging
import mimetypes
import functools

import boto3
import psycopg2
import botocore

from githubcrawler import GithubCommitCrawler
from knowledgemodel import DeveloperProfile

LOGGER = logging.getLogger()
logging.getLogger('boto3').setLevel(logging.WARNING)
logging.getLogger('botocore').setLevel(logging.WARNING)
S3_CONFIG = {
        'region_name': os.environ['AWS_REGION'],
        'aws_access_key_id': os.environ['AWS_ACCESS_KEY_ID'],
        'aws_secret_access_key': os.environ['AWS_SECRET_ACCESS_KEY'],
        }

TMPFS_DRIVE = os.environ['TMPFS_DRIVE']
LARGE_DRIVE = os.environ['LARGE_DRIVE']
TMPFS_MAX_WRITE = int(os.environ['TMPFS_DRIVE_MAX_WRITE'])
BUCKET = os.environ['S3_BUCKET']
LEADERBOARD_PREFIX = os.environ['S3_LEADERBOARD_PREFIX']
USER_PREFIX = os.environ['S3_USER_PREFIX']

def scan_all_repos(access_token, skill_set_id):
    user = DeveloperProfile()
    crawler = GithubCommitCrawler(access_token, user.analyze_commit, TMPFS_DRIVE, LARGE_DRIVE, TMPFS_MAX_WRITE)
    github_id = crawler.api.get_user().login
    crawler.crawl_all_repos(skip = lambda repo: repo.name != 'skillgraph')
    bucket = boto3.resource('s3', **S3_CONFIG).Bucket(BUCKET)
    def _compute_knowledge(language, module, dates):
        ''' yeah, this is less than perfect...Should try to find a way to not pass around that knowledge_activation func '''
        return compute_knowledge(bucket, language, module, github_id, dates, user.knowledge_activation)

    knowledge = user.compute_knowledge(_compute_knowledge)
    bucket.Object('{}/{}'.format(USER_PREFIX, github_id)).put(Body = json.dumps(knowledge))

def compute_knowledge(bucket, language, module, github_id, dates, knowledge_activation_function):
    knowledge = functools.reduce(lambda prev, curr: prev + knowledge_activation_function(curr), dates, 0.0)
    key = '{}/{}/{}/{}'.format(LEADERBOARD_PREFIX, language, module, github_id)

    map(lambda obj: obj.delete(), bucket.objects.filter(Prefix = key))
    bucket.Object(key = '{}:{:.2f}'.format(key, knowledge)).put(Body = bytes('', 'utf-8'))

    return knowledge

def write_rankings_to_db(skill_set_id, rankings):
    try:
        connection = psycopg2.connect(dbname = 'postgres', user = 'postgres', password = '', host = 'database')
        cursor = connection.cursor()
        cursor.execute('UPDATE skill_set SET skills=(%s) WHERE id=(%s)', (pickle.dumps(rankings), skill_set_id))
    except Exception as exc:
        LOGGER.exception('Couldnt write skills to database!')
    finally:
        try:
            cursor.close()
            connection.close()
        except:
            pass

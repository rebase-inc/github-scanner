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
        'region_name': 'us-east-1',
        'aws_access_key_id': os.environ['AWS_ACCESS_KEY_ID'],
        'aws_secret_access_key': os.environ['AWS_SECRET_ACCESS_KEY'],
        }
SMALL_REPO_DIR = os.environ['SMALL_REPO_DIR']
LARGE_REPO_DIR = os.environ['LARGE_REPO_DIR']
REPO_CUTOFF_SIZE = int(os.environ['SMALL_REPO_DIR_SIZE']) / int(os.environ['SMALL_REPO_SAFETY_FACTOR'])
KNOWLEDGE_KEYSPACE = os.environ['S3_KNOWLEDGE_KEYSPACE']
KNOWLEDGE_BUCKET = os.environ['S3_KNOWLEDGE_BUCKET']


def scan_all_repos(access_token, skill_set_id):
    user = DeveloperProfile()
    crawler = GithubCommitCrawler(access_token, user.analyze_commit, SMALL_REPO_DIR, LARGE_REPO_DIR, REPO_CUTOFF_SIZE)
    github_id = crawler.api.get_user().login
    crawler.crawl_all_repos(skip = lambda repo: repo.name != 'skillgraph')
    bucket = boto3.resource('s3', **S3_CONFIG).Bucket(KNOWLEDGE_BUCKET)

    def _compute_and_set_ranking(language, module, dates):
        return set_ranking(bucket, language, module, crawler.api.get_user().login, dates, user.knowledge_activation)

    rankings = user.compute_rankings(_compute_and_set_ranking)
    LOGGER.info('Computed rankings for {} modules'.format(count))
    write_rankings_to_db(skill_set_id, rankings)

def set_ranking(bucket, language, module, github_id, dates, knowledge_activation_function):
    knowledge_keyspace = KNOWLEDGE_KEYSPACE.format(language = language, module = module)

    for knowledge_object in bucket.objects.filter(Prefix = knowledge_keyspace + github_id):
        knowledge_object.delete()

    knowledge = functools.reduce(lambda prev, curr: prev + knowledge_activation_function(curr), dates, 0.0)

    knowledge_object = bucket.Object(key = knowledge_keyspace + github_id + ':{:.2f}'.format(knowledge))
    etag = knowledge_object.put(Body = json.dumps(dates))['ETag']
    #knowledge_object.wait_until_exists(IfMatch = etag)

    all_users = []
    for user_knowledge in bucket.objects.filter(Prefix = knowledge_keyspace):
        all_users.append(float(re.match('.*\:([0-9,.]+)', user_knowledge.key).group(1)))
    return bisect.bisect_left(all_users, knowledge) / len(all_users)

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

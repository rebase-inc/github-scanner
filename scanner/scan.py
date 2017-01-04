import os
import json
import rsyslog
import logging
import functools

import boto3
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

def scan_all_repos(access_token, block_until_consistent = True):
    user = DeveloperProfile()
    crawler = GithubCommitCrawler(access_token, user.analyze_commit, TMPFS_DRIVE, LARGE_DRIVE, TMPFS_MAX_WRITE)
    github_id = crawler.api.get_user().login
    LOGGER.info('Scanning all repositories for github user {}'.format(github_id))
    crawler.crawl_all_repos()
    bucket = boto3.resource('s3', **S3_CONFIG).Bucket(BUCKET)

    knowledge = user.compute_knowledge()
    knowledge_object = bucket.Object('{}/{}'.format(USER_PREFIX, github_id))
    etag = knowledge_object.put(Body = json.dumps(knowledge))['ETag']

    user.walk_knowledge(lambda lang, mod, know: write_knowledge_to_s3(bucket, github_id, lang, mod, know))

    # TODO: Add check for all of the s3 written objects
    if block_until_consistent:
        start = time.time()
        LOGGER.debug('Waiting until s3 objects exist...')
        knowledge_object.wait_until_exists(IfMatch = etag)
        LOGGER.debug('S3 object exists...Waited {} seconds'.format(time.time() - start))

def write_knowledge_to_s3(bucket, github_id, language, module, knowledge):
    knowledge = functools.reduce(lambda prev, curr: prev + knowledge_activation_function(curr), dates, 0.0)
    key = '{}/{}/{}/{}'.format(LEADERBOARD_PREFIX, language, module, github_id)

    map(lambda obj: obj.delete(), bucket.objects.filter(Prefix = key))
    bucket.Object(key = '{}:{:.2f}'.format(key, knowledge)).put(Body = bytes('', 'utf-8'))

    return knowledge

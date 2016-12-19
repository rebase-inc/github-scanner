import re
import os
import json
import pickle
import rsyslog
import logging
import mimetypes

import boto3
import botocore

from githubcrawler import GithubCommitCrawler
from knowledgemodel import DeveloperProfile

LOGGER = logging.getLogger()
S3_CONFIG = {
        'region_name': 'us-east-1',
        'aws_access_key_id': os.environ['AWS_ACCESS_KEY_ID'],
        'aws_secret_access_key': os.environ['AWS_SECRET_ACCESS_KEY'],
        }
SKILL_DATA_S3_BUCKET = os.environ['SKILL_DATA_S3_BUCKET']
SMALL_REPO_DIR = os.environ['SMALL_REPO_DIR']
LARGE_REPO_DIR = os.environ['LARGE_REPO_DIR']
REPO_CUTOFF_SIZE = int(os.environ['SMALL_REPO_DIR_SIZE']) / int(os.environ['SMALL_REPO_SAFETY_FACTOR'])

def scan_all(access_token, skill_set_id):
    user = DeveloperProfile()
    crawler = GithubCommitCrawler(access_token, user.analyze_commit, SMALL_REPO_DIR, LARGE_REPO_DIR, REPO_CUTOFF_SIZE)
    crawler.crawl_all_repos(skip = skip_predicate)

    s3 = boto3.resource('s3', **S3_CONFIG)
    keyspace = s3.Object(SKILL_DATA_S3_BUCKET, 'user-profiles/{}/data'.format(crawler.api.get_user().login))
    try:
        keyspace.delete()
    except botocore.exceptions.ClientError as e:
        LOGGER.error('Couldnt delete object, response: {}'.format(str(e.response)))

    knowledge = user.get_computed_knowledge()
    keyspace.put(Body=json.dumps(knowledge))

def skip_predicate(repo):
    if 'ONLY_THIS_REPO' in os.environ:
        return repo.name != os.environ['ONLY_THIS_REPO']
    elif 'SKIP_THIS_REPO' in os.environ:
        return repo.name == os.environ['SKIP_THIS_REPO']
    else:
        return False


import re
import os
import pickle
import rsyslog
import logging
import psycopg2
import mimetypes

import boto3
import botocore

from githubcrawler import GithubCommitCrawler
from knowledgemodel import DeveloperProfile

LOGGER = logging.getLogger()
S3_CONFIG = {
        'region_name': 'us-east-1',
        'aws_access_key_id': os.environ['BACKEND_AWS_ACCESS_KEY_ID'],
        'aws_secret_access_key': os.environ['BACKEND_AWS_SECRET_ACCESS_KEY'],
        }
SKILL_DATA_S3_BUCKET = os.environ['SKILL_DATA_S3_BUCKET']
SMALL_REPO_DIR = os.environ['SMALL_REPO_DIR']
LARGE_REPO_DIR = os.environ['LARGE_REPO_DIR']
REPO_CUTOFF_SIZE = int(os.environ['SMALL_REPO_DIR_SIZE']) / int(os.environ['SMALL_REPO_SAFETY_FACTOR'])

def scan_all(access_token, skill_set_id):
    user = DeveloperProfile()
    crawler = GithubCommitCrawler(access_token, user.analyze_commit, SMALL_REPO_DIR, LARGE_REPO_DIR, REPO_CUTOFF_SIZE)
    crawler.crawl_all_repos(skip = skip_predicate)

    write_skills_to_db(user, skill_set_id)
    write_skills_to_s3(user, crawler.api.get_user().login)

def skip_predicate(repo):
    if 'ONLY_THIS_REPO' in os.environ:
        return repo.name != os.environ['ONLY_THIS_REPO']
    elif 'SKIP_THIS_REPO' in os.environ:
        return repo.name == os.environ['SKIP_THIS_REPO']
    else:
        return False

def write_skills_to_db(user, skill_set_id):
    try:
        connection = psycopg2.connect(dbname = 'postgres', user = 'postgres', password = '', host = 'database')
        cursor = connection.cursor()
        cursor.execute('UPDATE skill_set SET skills=(%s) WHERE id=(%s)', (pickle.dumps(user.as_dict()), skill_set_id))
    except Exception as exc:
        LOGGER.exception('Couldnt write skills to database!')
    finally:
        try:
            cursor.close()
            connection.close()
        except:
            pass

def write_skills_to_s3(user, github_id):
    LOGGER.info('writing skills of {} to s3 under github id {}'.format(str(user.as_dict()), github_id))
    s3 = boto3.resource('s3', **S3_CONFIG)
    keyspace = s3.Object(SKILL_DATA_S3_BUCKET, 'user-profiles/{}/data'.format(github_id))

    try:
        keyspace.delete()
    except botocore.exceptions.ClientError as e:
        LOGGER.error('Couldnt delete object, response: {}'.format(str(e.response)))

    keyspace.put(Body=pickle.dumps(user.as_dict()))
    
    response = keyspace.get()['Body'].read()
    LOGGER.info('just to check, we got back {}'.format(pickle.loads(response))) 


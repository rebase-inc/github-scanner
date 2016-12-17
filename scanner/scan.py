import re
import os
import pickle
import rsyslog
import logging
import psycopg2
import mimetypes

from githubcrawler import GithubCommitCrawler
from knowledgemodel import DeveloperProfile

LOGGER = logging.getLogger()

def scan_all(access_token, skill_set_id = None):
    if 'ONLY_THIS_REPO' in os.environ:
        skip_predicate = lambda repo: repo.name != os.environ['ONLY_THIS_REPO']
    elif 'SKIP_THIS_REPO' in os.environ:
        skip_predicate = lambda repo: repo.name == os.environ['SKIP_THIS_REPO']
    else:
        skip_predicate = lambda repo: False

    user = DeveloperProfile()
    crawler = GithubCommitCrawler(access_token, callback = user.analyze_commit)
    crawler.crawl_all_repos(skip = skip_predicate)

    if skill_set_id:
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

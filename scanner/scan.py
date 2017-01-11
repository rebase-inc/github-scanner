import os
import logging
from collections import Counter

from rq import get_current_job

from githubcrawler import GithubCommitCrawler
from knowledgemodel import KnowledgeModel
from codeparser import CodeParser
from authgen import delete_github_access_token

LOGGER = logging.getLogger()
S3BUCKET = os.environ['S3_BUCKET']
S3_CONFIG = {
        'region_name': os.environ['AWS_REGION'],
        'aws_access_key_id': os.environ['AWS_ACCESS_KEY_ID'],
        'aws_secret_access_key': os.environ['AWS_SECRET_ACCESS_KEY'],
        }
CRAWLER_CONFIG = {
        'tmpfs_drive': os.environ['TMPFS_DRIVE'],
        'fs_drive': os.environ['LARGE_DRIVE'],
        'tmpfs_cutoff': int(os.environ['TMPFS_DRIVE_MAX_WRITE']),
        }

def _report_progress(scanned, total):
    if not isinstance(scanned, Counter) or not isinstance(total, Counter):
        raise Exception('Only collections.Counter objects can be supplied to report progress!')
    job = get_current_job()
    job.meta['commits_scanned'] = scanned
    job.meta['all_commits'] = total
    job.save()

def scan_all_repos(access_token: str, github_id: str = None):
    knowledge = KnowledgeModel()
    parser = CodeParser(callback = knowledge.add_reference)
    crawler = GithubCommitCrawler(
        callback = parser.analyze_code,
        access_token = access_token,
        config = CRAWLER_CONFIG,
        report_progress = _report_progress,
        username = github_id
        )
    crawler.crawl_all_repos()
    knowledge.write_to_s3(crawler.user.login, S3BUCKET, S3_CONFIG)
    LOGGER.info('Scan summary for user {}: {}'.format(crawler.user.login, parser.health))
    return (knowledge.simple_projection, parser.health.as_dict())

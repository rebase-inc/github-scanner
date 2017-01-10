import os
import logging

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

def scan_all_repos(access_token, github_id: str = None):
    knowledge = KnowledgeModel()
    parser = CodeParser(callback = knowledge.add_reference)
    crawler = GithubCommitCrawler(callback = parser.analyze_code, access_token = access_token, config = CRAWLER_CONFIG, username = github_id)

    crawler.crawl_all_repos()
    knowledge.write_to_s3(crawler.user.login, S3BUCKET, S3_CONFIG)
    LOGGER.info('Scan summary for user {}: {}'.format(crawler.user.login, parser.health))
    return knowledge.simple_projection

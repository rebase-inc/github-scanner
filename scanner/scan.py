import os
import logging
from collections import Counter

from rq import get_current_job

from githubcrawler import GithubCommitCrawler
from knowledgemodel import KnowledgeModel
from codeparser import CodeParser
from authgen import GithubToken

LOGGER = logging.getLogger()
S3BUCKET = os.environ['S3_BUCKET']
S3_CONFIG = {
        'region_name': os.environ['AWS_REGION'],
        'aws_access_key_id': os.environ['AWS_ACCESS_KEY_ID'],
        'aws_secret_access_key': os.environ['AWS_SECRET_ACCESS_KEY'],
        }
CLONE_CONFIG = {
        'tmpfs_drive': os.environ['TMPFS_DRIVE'],
        'fs_drive': os.environ['LARGE_DRIVE'],
        'tmpfs_cutoff': int(os.environ['TMPFS_DRIVE_MAX_WRITE']),
        }
USERNAME = os.environ['GITHUB_CRAWLER_USERNAME']
PASSWORD = os.environ['GITHUB_CRAWLER_PASSWORD']

class MeasuredJobProgress(object):

    def __init__(self, steps_key = 'steps', finished_key = 'finished'):
        self.steps = Counter()
        self.finished = Counter()
        self.steps_key = steps_key
        self.finished_key = finished_key
        self.job = get_current_job()

    def add_step(self, name, count = 1):
        self.steps[name] += count
        self.report()

    def mark_finished(self, name, count = 1):
        self.finished[name] += count
        self.report()

    def report(self):
        self.job.meta[self.steps_key] = self.steps
        self.job.meta[self.finished_key] = self.finished
        self.job.save()

def scan_public_repos(github_id: str):
    knowledge = KnowledgeModel()
    parser = CodeParser(callback = knowledge.add_reference)
    progress = MeasuredJobProgress()

    def _skip(repo, log = True):
        skip = not parser.supports_any_of(*repo.get_languages().keys())
        if skip and log:
            LOGGER.debug('Skipping repo {} because of missing language support'.format(repo.full_name))
        return skip

    def _callback(repo_name, commit):
        parser.analyze_commit(repo_name, commit)
        progress.mark_finished(repo_name)

    with GithubToken(USERNAME, PASSWORD, note = github_id) as token:
        crawler = GithubCommitCrawler(token, CLONE_CONFIG)
        crawler.crawl_public_repos(github_id, lambda repo_name, commit: progress.add_step(repo_name), lambda repo: _skip(repo, False), remote_only = True)
        crawler.crawl_public_repos(github_id, _callback, _skip)
        knowledge.write_to_s3(github_id, S3BUCKET, S3_CONFIG)

def scan_authorized_repos(access_token: str):
    knowledge = KnowledgeModel()
    parser = CodeParser(callback = knowledge.add_reference)
    progress = MeasuredJobProgress()

    def _skip(repo):
        return not parser.supports_any_of(*repo.get_languages().keys())
    def _callback(repo_name, commit):
        parser.analyze_commit(repo_name, commit)
        progress.mark_finished(repo_name)

    crawler = GithubCommitCrawler(access_token, CLONE_CONFIG)
    crawler.crawl_public_repos(github_id, lambda repo_name, commit: progress.add_step(repo_name), lambda repo: _skip(repo, False), remote_only = True)
    crawler.crawl_public_repos(github_id, _callback, _skip)
    knowledge.write_to_s3(crawler.user.login, S3BUCKET, S3_CONFIG)

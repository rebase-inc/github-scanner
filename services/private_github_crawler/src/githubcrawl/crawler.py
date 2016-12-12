import os
import git
import shutil
import logging

import magic
import rsyslog
from github import GithubException

from .api import RateLimitAwareGithubAPI

LOGGER = logging.getLogger()
CLONE_RAM_DIR = '/repos'
CLONE_FS_DIR = '/big_repos'

class GithubCommitCrawler(object):
    def __init__(self, access_token):
        self.api = RateLimitAwareGithubAPI(login_or_token = access_token)
        self.oauth_clone_prefix = 'https://{access_token}@github.com'.format(access_token = access_token)

        # TODO: Remove environment variable dependency
        self._in_memory_clone_limit = 1024 * int(os.environ['REPOS_VOLUME_SIZE_IN_MB']) / int(os.environ['CLONE_SIZE_SAFETY_FACTOR'])

    def crawl_all_repos(self, skip = lambda repo: False):
        user = self.api.get_user()
        repos_to_crawl = []
        for repo in user.get_repos():
            try:
                if skip(repo):
                    LOGGER.debug('Skipping repository "{}"'.format(repo))
                else:
                    repos_to_crawl.append(repo)
            except GithubException as e:
                LOGGER.exception('Unknown exception for user "{}" and repository "{}": {}'.format(user, repo, e))
        for repo in repos_to_crawl:
            self.crawl_repo(repo)

    def crawl_repo(self, repo):
        all_commits = repo.get_commits(author = self.api.get_user().login)
        if not (all_commits or all_commits.totalCount()):
            LOGGER.debug('Skipping {} repo (no commits found for user {})'.format(repo.name, self.user.login))
        else:
            cloned_repo = self.clone(repo)
            for commit in repo.get_commits(author = self.api.get_user().login):
                data = self.analyze_commit(cloned_repo.commit(commit.sha))
        if os.path.isdir(cloned_repo.working_dir):
            shutil.rmtree(cloned_repo.working_dir)

    def analyze_commit(self, commit):
        if len(commit.parents) == 0:
            return self.analyze_initial_commit(commit)
        elif len(commit.parents) == 1:
            return self.analyze_regular_commit(commit)
        else:
            return self.analyze_merge_commit(commit)

    def analyze_merge_commit(self, commit):
        return

    def analyze_initial_commit(self, commit):
        for blob in commit.tree.traverse(predicate = lambda item, depth: item.type == 'blob'):
            LOGGER.debug('We are reading some data from an initial commit: {}...'.format(blob.data_stream.read().decode()[:10]))

    def analyze_regular_commit(self, commit):
        for diff in commit.parents[0].diff(commit, create_patch = True):
            if diff.deleted_file or diff.renamed:
                continue
            try:
                old_content = self.decode_blob('' if diff.new_file else commit.parents[0].tree[diff.a_path].data_stream.read())
                new_content = self.decode_blob(commit.tree[diff.b_path].data_stream.read())
                LOGGER.debug('DATA {}:{}'.format(old_content[0:20], new_content[0:20]))
            except ValueError as exc:
                LOGGER.exception('Unreadable diff: {}'.format(str(exc)))


    # TODO: Maybe remove this from the class
    def decode_blob(self, blob):
        encoding = magic.Magic(mime_encoding = True).from_buffer(blob)
        if encoding == 'binary':
            LOGGER.debug('Skipping blob due to binary encoding!')
            return ''
        return blob.decode(encoding)

    def clone(self, repo):
        url = repo.clone_url.replace('https://github.com', self.oauth_clone_prefix, 1)
        clone_base_dir = CLONE_RAM_DIR if repo.size <= self._in_memory_clone_limit else CLONE_FS_DIR
        repo_path = os.path.join(clone_base_dir, repo.name)
        if os.path.isdir(repo_path):
            shutil.rmtree(repo_path)
        try:
            return git.Repo.clone_from(url, repo_path)
        except git.exc.GitCommandError as e:
            if clone_base_dir == CLONE_RAM_DIR:
                LOGGER.exception('Failed to clone {} repository into memory ({}), trying to clone to disk...'.format(repo.name, e))
                repo_path = os.path.join(CLONE_FS_DIR, repo.name)
                return git.Repo.clone_from(url, repo_path)
            else:
                raise e

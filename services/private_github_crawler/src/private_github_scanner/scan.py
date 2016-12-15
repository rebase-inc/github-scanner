import re
import logging
import mimetypes

from githubcrawler import GithubCommitCrawler

from .language import PythonKnowledge

LOGGER = logging.getLogger()

class DeveloperProfile(object):
    def __init__(self):
        self.languages = {}
        self.languages[PythonKnowledge.NAME] = PythonKnowledge()

        self.mimetypes = mimetypes.MimeTypes(strict = False)
        self.mimetypes.types_map[0]['.jsx'] = self.mimetypes.types_map[1]['.js']
        self.mimetype_regex = re.compile('(?:application|text)\/(?:(?:x-)?)(?P<language>[a-z]+)')

    def serialize_results():
        for languages in self.languages:
            language.parser.close()
        return 'some shit'

    def guess_language(self, path):
        # For now, this returns a set with zero or one elements.
        # However, we may in the future support languages that can
        # Be parsed by multiple intepreters, so this returns a set
        mimetype, encoding = self.mimetypes.guess_type(path)
        if not mimetype:
            LOGGER.debug('Unrecognized file type at {}'.format(path))
            return set()
        else:
            match = self.mimetype_regex.match(mimetype)
            if not match:
                LOGGER.debug('Unrecognized mimetype of path {}'.format(path))
                return set()
            return set([ match.group('language') ])

    def analyze_commit(self, commit):
        if len(commit.parents) == 0:
            return self.analyze_initial_commit(commit)
        elif len(commit.parents) == 1:
            return self.analyze_regular_commit(commit)
        else:
            return self.analyze_merge_commit(commit)

    def analyze_regular_commit(self, commit):
        for diff in commit.parents[0].diff(commit, create_patch = True):
            for language in self.guess_language(diff.a_path if diff.deleted_file else diff.b_path):
                if language not in self.languages:
                    LOGGER.debug('Skipping parsing {} in {} due to missing language support'.format(diff.b_path, language))
                    continue
                self.languages[language].analyze_diff(diff, commit)

    def analyze_initial_commit(self, commit):
        for blob in commit.tree.traverse(predicate = lambda item, depth: item.type == 'blob'):
            for language in self.guess_language(blob.path):
                if language not in self.languages:
                    LOGGER.debug('Skipping parsing {} in {} due to missing language support'.format(blob.path, language))
                    continue
                self.languages[language].analyze_blob(blob, commit)

    def analyze_merge_commit(self, commit):
        LOGGER.debug('Skipping merge commit')

def scan_all(access_token):
    user = DeveloperProfile()
    crawler = GithubCommitCrawler(access_token, callback = user.analyze_commit)
    crawler.crawl_all_repos(skip = lambda repo: False)
    return

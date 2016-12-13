import logging

from calendar import timegm
from datetime import datetime
from collections import defaultdict

from githubcrawl import GithubCommitCrawler
from codeparse import parse_python, MissingPathInTree, NotDecodableError

LOGGER = logging.getLogger()

class UserProfile(object):
    def __init__(self):
        self.private_library_uses = defaultdict(list)
        self.standard_library_uses = defaultdict(list)
        self.third_party_library_uses = defaultdict(list)

    def add_data_from_diff(self, commit_datetime, previous_tree, previous_path, current_tree, current_path):
        try:
            commit_datetime = timegm(commit_datetime.utctimetuple())

            use_types_history = [ self.private_library_uses, self.standard_library_uses, self.third_party_library_uses ]
            use_types_before_commit = parse_python(previous_tree, previous_path)
            use_types_after_commit = parse_python(current_tree, current_path)

            for history, before_commit, after_commit in zip(use_types_history, use_types_before_commit, use_types_after_commit):
                for reference in (before_commit | after_commit):
                    history[reference] += [ commit_datetime for _ in range(abs(before_commit[reference] - after_commit[reference])) ]

        except SyntaxError:
            pass
        except NotDecodableError:
            pass
        except MissingPathInTree:
            pass


def scan_all(access_token):
    user = UserProfile()
    crawler = GithubCommitCrawler(access_token, callback = user.add_data_from_diff)
    crawler.crawl_all_repos(skip = lambda repo: repo.name != 'veb')
    for private_library, dates in user.private_library_uses.items():
        for date in dates:
            LOGGER.info('Used {} on {}'.format(private_library, date))
    for standard_library, dates in user.standard_library_uses.items():
        for date in dates:
            LOGGER.info('Used {} on {}'.format(standard_library, date))
    for third_party_library, dates in user.third_party_library_uses.items():
        for date in dates:
            LOGGER.info('Used {} on {}'.format(third_party_library, date))

from .crawler import GithubCommitCrawler

SUPPORTED_LANGUAGES = set(['Python', 'JavaScript', 'Java'])

def crawl(access_token):
    crawler = GithubCommitCrawler(access_token)
    #crawler.crawl_all_repos(skip_repo = lambda repo: not set(repo.get_languages().keys()) & SUPPORTED_LANGUAGES)
    crawler.crawl_all_repos()

import time
import logging
import rsyslog

from github import Github, GithubException
from github.Requester import Requester
from github.MainClass import DEFAULT_BASE_URL, DEFAULT_TIMEOUT, DEFAULT_PER_PAGE

rsyslog.setup()
LOGGER = logging.getLogger()

class RateLimitAwareGithubAPI(Github):

    def __init__(self, login_or_token=None, password=None, base_url=DEFAULT_BASE_URL, 
            timeout=DEFAULT_TIMEOUT, client_id=None, client_secret=None, user_agent='PyGithub/Python', 
            per_page=DEFAULT_PER_PAGE, api_preview=False):
        super().__init__(login_or_token=login_or_token, password=password, base_url=base_url, 
            timeout=timeout, client_id=client_id, client_secret=client_secret, user_agent=user_agent, 
            per_page=per_page, api_preview=api_preview)
        self.__requester = RetryingRequester(login_or_token=login_or_token, password=password, base_url=base_url, 
            timeout=timeout, client_id=client_id, client_secret=client_secret, user_agent=user_agent, 
            per_page=per_page, api_preview=api_preview)

class RetryingRequester(Requester):
    def __init__(self, max_retries = 3, min_delay = 0.75, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.consecutive_failed_attempts = 0
        self.max_retries = max_retries
        self.min_delay = min_delay
        self.last_request_time = None

        # wait_until is not currently used, but it's there so that, if necessary
        # __requestEncode could be easily extended to pay attention to additional
        # rate limiting headers, such as Retry-After. Additionally, a user of the
        # RetryingRequester or RateLimitAwareGithubAPI could force the requester
        # to wait by setting this variable
        self.wait_until = None

    def __requestEncode(self, *args, **kwargs):
        seconds_since_last_request = (datetime.now() - (self.last_request_time or 0)).total_seconds()
        if self.consecutive_failed_attempts >= self.max_retries:
            raise GithubRateLimitMaxRetries(*args[0:3])
        elif self.wait_until:
            time.sleep((self.wait_until - datetime.now()).total_seconds())
        elif seconds_since_last_request < self.min_delay:
            LOGGER.debug('Minimum request delay of {} seconds not reached - sleeping for {} seconds'.format(self.min_delay, self.min_delay - seconds_since_last_request))
            time.sleep(self.min_delay - seconds_since_last_request)
        
        try:
            self.last_request_time = datetime.utcnow()
            LOGGER.debug("ACTUALLY DOING A REQUEST!")
            return super().__requestEncode(*args, **kwargs)
        except GithubException.RateLimitExceededException:
            self.consecutive_failed_attempts += 1
            time_until_reset = (datetime.utcfromtimestamp(self.rate_limiting_resettime) - datetime.utcnow()).total_seconds()
            LOGGER.info('Rate limited from GitHub API! Sleeping for {} seconds'.format(time_until_reset))
            time.sleep(time_until_reset)
            return self.__requestEncode(*args, **kwargs)

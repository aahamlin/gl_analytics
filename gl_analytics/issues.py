""" Issues module interacts with a backend system API, e.g. GitLab.
"""

import requests
from urllib.parse import urlencode

GITLAB_URL_BASE = "https://gitlab.com/api/v4"

class IssuesError(Exception):
    pass

class Session(object):

    def get(self):
        raise IssuesError('Not Implemented')

class GitlabSession(Session):

    def __init__(self, access_token=None):
        self._access_token = access_token

    def _get(self, url, **kwargs):
        return requests.get(url, **kwargs)

    def get(self, url):
        headers = { 'PRIVATE-TOKEN': self._access_token }
        return self._get(url, headers=headers)

    def build_request_url(self, group, milestone):
        url = "{0}/groups/{1}/issues".format(GITLAB_URL_BASE,group)
        params = { 'pagination': 'keyset', 'milestone': milestone }
        print('built url:', url)
        print('built params:', params)
        return "{0}?{1}".format(url, urlencode(params))

class Repository(object):
    """This is specifically a GitLab Issue repository. Current GitLab version is 13.11.0-pre.

    If ever we needed it, an AbstractRepository could be extracted.
    """

    def __init__(self, session=None, group=None, milestone=None):
        """Initialize a repository.
       """
        self._session = session
        self._group = group
        self._milestone = milestone

    def list(self):
        """Return issues from the repository.

       """
        return [x for x in self._page_results()]

    def _page_results(self):
        """Generator of issues from pages of results.
       """

        # starting request
        url = self._session.build_request_url(self._group, self._milestone)

        hasMore = True
        while hasMore:
            # make request
            r1 = self._session.get(url)
            r1.raise_for_status()

            # extract the issues from the response body
            payload = r1.json()
            count = len(payload)
            print(f'processing {count} items');
            for item in payload:
                yield {
                    'iid': item['iid'],
                    'project_id': item['project_id']
                }

            if r1.links and 'next' in r1.links:
                # setup next page request
                next_link = r1.links['next']
                url = next_link['url']
                print('next page:', url)
            else:
                hasMore = False

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

class AbstractRequestFactory(object):

    def get(self, url, **kwargs):
        raise IssuesError()

class RequestFactory(AbstractRequestFactory):

    def get(self, url, **kwargs):
        return requests.get(url, **kwargs)

class GitlabSession(Session):

    def __init__(self, access_token=None, request_factory=RequestFactory()):
        self._access_token = access_token
        self._request_factory = request_factory

    def get(self, url):
        headers = { 'PRIVATE-TOKEN': self._access_token }
        return self._request_factory.get(url, headers=headers)


class AbstractRepository(object):

    def list(self):
        raise IssuesError()

class GroupIssuesRepository(AbstractRepository):
    """This is specifically a GitLab Issue repository. Current GitLab version is 13.11.0-pre.

    If ever we needed it, an AbstractRepository could be extracted.
    """

    def __init__(self, session=None, group=None, milestone=None):
        """Initialize a repository.
       """
        self._session = session
        self._group = group
        self._milestone = milestone
        self._url = self._build_request_url()

    @property
    def url(self):
        return self._url

    def list(self):
        """Return issues from the repository.
        """
        return [x for x in self._page_results()]

    def _build_request_url(self):
        url = "{0}/groups/{1}/issues".format(GITLAB_URL_BASE, self._group)
        params = { 'pagination': 'keyset', 'milestone': self._milestone }
        print('built url:', url)
        print('built params:', params)
        return "{0}?{1}".format(url, urlencode(params))


    def _page_results(self):
        """Generator of issues from pages of results.
       """

        # starting request
        url = self.url

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
                yield Issue(item)

            if r1.links and 'next' in r1.links:
                # setup next page request
                next_link = r1.links['next']
                url = next_link['url']
                print('next page:', url)
            else:
                hasMore = False

class Issue(object):

    def __init__(self, item):

        self._issue_id = item['iid']
        self._project_id = item['project_id']
        self._opened_at = item['opened_at']
        self._closed_at = item.get('closed_at')

    @property
    def issue_id(self):
        return self._issue_id

    @property
    def project_id(self):
        return self._project_id

    @property
    def opened_at(self):
        self._opened_at

    @property
    def closed_at(self):
        self._closed_at

class IssueLabelRepository(AbstractRepository):

    def __init__(self, session=None, issue=None):
        self._session = session
        self._issue = issue
        self._url = self._build_request_url()

    @property
    def url(self):
        return self._url

    def list(self):
        return [x for x in self._label_events()]

    def _build_request_url(self):
        # /api/v4/projects/8279995/issues/191/resource_label_events
        url = "{0}/projects/{1}/issues/{2}/resource_label_events".format(
            GITLAB_URL_BASE, self._issue.project_id, self._issue.issue_id)
        return url

    def _label_events(self):

        url = self.url
        r = self._session.get(url)
        r.raise_for_status()

        payload = r.json()
        print(f'processing label events: {payload}')
        # action: add, remove
        # created_at: datetime
        # label.name
        # label.id
        for event in payload:
            yield {'action': event['action'], 'datetime': event['created_at'], 'step': event['label']['name']}

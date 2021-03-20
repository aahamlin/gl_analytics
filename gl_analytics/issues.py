""" Issues module interacts with a backend system API, e.g. GitLab.
"""

import json
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

class GitlabIssuesRepository(AbstractRepository):
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
            #print(f'processing {count} items');
            for item in payload:
                yield self._load_issue(item)

            if r1.links and 'next' in r1.links:
                # setup next page request
                next_link = r1.links['next']
                url = next_link['url']
                print('next page:', url)
            else:
                hasMore = False

    def _build_issue_label_request_url(self, project_id, issue_id):
        # /api/v4/projects/8279995/issues/191/resource_label_events
        url = "{0}/projects/{1}/issues/{2}/resource_label_events".format(
            GITLAB_URL_BASE, project_id, issue_id)
        return url

    def _load_issue(self, item):
        issue = Issue(item)
        url = self._build_issue_label_request_url(issue.project_id, issue.issue_id)
        r = self._session.get(url)
        r.raise_for_status()

        payload = r.json()
        #print(f'processing label events: {payload}')
        # action: add, remove
        # created_at: datetime
        # label.name
        # label.id
        for event in payload:
            #print('Payload event', json.dumps(event))
            issue.labels.append({'action': event['action'], 'datetime': event['created_at'], 'step': event['label']['name']})

        return issue

class Issue(object):

    def __init__(self, item):
        #print('creating Issue from item', json.dumps(item))
        self._issue_id = item['iid']
        self._project_id = item['project_id']
        self._opened_at = item['created_at']
        self._closed_at = item.get('closed_at')
        self._label_events = []

    @property
    def issue_id(self):
        return self._issue_id

    @property
    def project_id(self):
        return self._project_id

    @property
    def opened_at(self):
        return self._opened_at

    @property
    def closed_at(self):
        return self._closed_at

    @property
    def labels(self):
        return self._label_events

    def __str__(self):
        return f"Issue(id:{self.issue_id}, p:{self.project_id}, o:{self.opened_at}, c:{self.closed_at}, l:{self.labels})"

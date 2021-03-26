""" Issues module interacts with a backend system API, e.g. GitLab.
"""
import sys
import json
import requests

from dateutil import parser as date_parser
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
    # XXX Create a Workflow Resolver to fetch workflow states for each issue. Replaces the Gitlabissueworkflowrepository.
    def __init__(self, session, group=None, milestone=None, resolvers=[]):
        """Initialize a repository.

        Required:
        session: session object
        group: group name or id
        milestone: milestone name or id

        Optional:
        resolvers: resolve additional fields
        """
        if not group or not milestone:
            raise SyntaxError('Requires group and milestone')

        self._session = session
        self._group = group
        self._milestone = milestone
        self._resolvers = resolvers

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
        print('built url:', url, file=sys.stderr)
        print('built params:', params, file=sys.stderr)
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
            #count = len(payload)
            #print(f'processing {count} items');
            for item in payload:
                item = self._resolve_fields(item)
                yield Issue(item)

            if r1.links and 'next' in r1.links:
                # setup next page request
                next_link = r1.links['next']
                url = next_link['url']
                print('next page:', url, file=sys.stderr)
            else:
                hasMore = False

    def _resolve_fields(self, item):
        for resolver_cls in self._resolvers:
            resolver = resolver_cls(self._session)
            item.update(resolver.resolve(item))
        return item

class GitlabWorkflowResolver(object):
    """Add workflow events to an item

    Workflow events are an array of tuples. But should probably be changed to an object.
    """

    def __init__(self, session):
        self._session = session

    def resolve(self, item):
        url = self._build_request_url(item['project_id'], item['iid'])
        res = self._fetch_results(url)
        return {'_workflow': self._calculate_workflow(item, res)}


    def _build_request_url(self, project_id, issue_id):
        # /api/v4/projects/8279995/issues/191/resource_label_events
        url = "{0}/projects/{1}/issues/{2}/resource_label_events".format(
            GITLAB_URL_BASE, project_id, issue_id)
        return url

    def _fetch_results(self, url):
        r = self._session.get(url)
        r.raise_for_status()

        payload = r.json()
        return payload

    def _calculate_workflow(self, item, payload):
        # every workflow starts with 'opened'
        events = []
        events.append(('add', 'opened', date_parser.parse(item['created_at'])))
        hanging_open = True

        for label_event in payload:
            try:
                action_name, step_name, action_date = self._get_workflow_step(label_event)
                #print('processing ', action_name, step_name)
                events.append((action_name, step_name, action_date))
                if hanging_open:
                      events.append(('remove', 'opened', action_date))
                      hanging_open = False
            except TypeError:
                pass

        # closed issues will end with 'closed'
        if 'closed_at' in item:
            #print('events before close', events)
            closed_at = date_parser.parse(item['closed_at'])
            try:
                # XXX ugly syntax
                prev_add = next(filter(lambda a: a[0] == 'add', reversed(events)))
                events.append(('add', 'closed', closed_at))
                _, last_name, _ = prev_add
                events.append(('remove', last_name, closed_at))
            except StopIteration:
                events.append(('add', 'closed', closed_at))

        return events

    def _get_workflow_step(self, event):
        """Returns a tuple containing: action, step_name, date

       This filters for labels scoped as 'workflow::*'
       """
        if 'label' not in event:
            return None

        if not event['label']['name'].startswith('workflow:'):
            return None

        step_name = event['label']['name']
        action_name = event['action']
        action_date = date_parser.parse(event['created_at'])

        return action_name, step_name, action_date


class Issue(object):

    def __init__(self, item):
        #print('creating Issue from item', json.dumps(item))
        self._issue_id = item['iid']
        self._project_id = item['project_id']
        self._opened_at = date_parser.parse(item['created_at'])
        closed_at = item.get('closed_at')
        self._closed_at = date_parser.parse(closed_at) if closed_at else None

        if '_workflow' in item:
            self._workflow = item['_workflow']

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
    def workflow(self):
        return self._workflow

    @workflow.setter
    def workflow(self, wf):
        self._workflow = wf

    @workflow.deleter
    def workflow(self):
        del self._workflow

    def __str__(self):
        return f"Issue(id:{self.issue_id}, p:{self.project_id}, o:{self.opened_at}, c:{self.closed_at}, w:{self.workflow})"


def find_issues(session, group=None, milestone=None):
    """Returns all issues by group and milestone and their entire workflow history.

    session: *required* Session object
    """
    repo = GitlabIssuesRepository(session, group="gozynta", milestone="mb_v1.3", resolvers=[GitlabWorkflowResolver])
    issues = repo.list()
    return issues

""" Issues module interacts with a backend system API, e.g. GitLab.
"""

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

    def __init__(self, session, group=None, milestone=None):
        """Initialize a repository.
       """
        if not group or not milestone:
            raise SyntaxError('Requires group and milestone')

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
            #count = len(payload)
            #print(f'processing {count} items');
            for item in payload:
                yield Issue(item)

            if r1.links and 'next' in r1.links:
                # setup next page request
                next_link = r1.links['next']
                url = next_link['url']
                print('next page:', url)
            else:
                hasMore = False

class GitlabIssueWorkflowRepository(AbstractRepository):
    """List workflow events for an issue.

    Workflow events are an array of tuples. But should probably be changed to an object.
    """
    def __init__(self, session, issue=None):

        if not issue:
            raise SyntaxError('Requires issue')

        self._session = session
        self._issue = issue
        self._url = self._build_request_url(issue.project_id, issue.issue_id)

    @property
    def issue(self):
        return self._issue

    @property
    def url(self):
        return self._url

    def list(self):
        """Return workflow events list for the issue.

       Events array items are tuples: 'action', 'worflowStep', 'date'
       """
        # XXX this is inconsistent with Issue class.
        return [x for x in self._fetch_results()]

    def _build_request_url(self, project_id, issue_id):
        # /api/v4/projects/8279995/issues/191/resource_label_events
        url = "{0}/projects/{1}/issues/{2}/resource_label_events".format(
            GITLAB_URL_BASE, project_id, issue_id)
        return url

    def _fetch_results(self):
        """Collect steps of the workflow for this issue.
        """
        # XXX how to manage the datetime values? truncate to a date or keep time as well?

        # every workflow starts with 'opened'
        events = []
        events.append(('add', 'opened', self.issue.opened_at))
        hanging_open = True

        r = self._session.get(self.url)
        r.raise_for_status()

        payload = r.json()
        for label_event in payload:
            try:
                action_name, step_name, action_date = self._add_workflow_step(label_event)
                #print('processing ', action_name, step_name)
                events.append((action_name, step_name, action_date))
                if hanging_open:
                      events.append(('remove', 'opened', action_date))
                      hanging_open = False
            except TypeError:
                pass

        # closed issues will end with 'closed'
        if self.issue.closed_at:
            #print('events before close', events)
            # XXX find last 'add' event
            try:
                prev_add = next(filter(lambda a: a[0] == 'add', reversed(events)))
                events.append(('add', 'closed', self.issue.closed_at))
                _, last_name, _ = prev_add
                events.append(('remove', last_name, self.issue.closed_at))
            except StopIteration:
                events.append(('add', 'closed', self.issue.closed_at))

        return events

    def _add_workflow_step(self, event):
        """Returns a tuple containing: action, step_name, date

       This filters for labels scoped as 'workflow::*'
       """
        # XXX This startswith workflow:: will come back to bite me someday, I know
        if 'label' not in event and not event['label']['name'].startswith('workflow::'):
            return None

        step_name = event['label']['name']
        action_name = event['action']
        action_date = date_parser.parse(event['created_at'])

        return action_name, step_name, action_date


class Issue(object):

    def __init__(self, item, workflow=[]):
        #print('creating Issue from item', json.dumps(item))
        self._issue_id = item['iid']
        self._project_id = item['project_id']
        self._opened_at = date_parser.parse(item['created_at'])
        closed_at = item.get('closed_at')
        self._closed_at = date_parser.parse(closed_at) if closed_at else None

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
    repo = GitlabIssuesRepository(session, group="gozynta", milestone="mb_v1.3")
    issues = repo.list()
    for issue in issues:
        labels = GitlabIssueWorkflowRepository(session, issue)
        issue.workflow = labels.list()

    return issues

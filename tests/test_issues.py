import pytest
import io
import datetime
from dateutil import parser as date_parser
from urllib.parse import urlparse, parse_qs
from requests import Response

import gl_analytics.issues as issues

class FakeRequestFactory(issues.AbstractRequestFactory):

    def __init__(self):
        """Initialize a fake to test requests.
        """
        self.responses = []
        self._call_index = -1
        self._call_instances = []

    def get(self, url, **kwargs):
        self._call_index += 1
        o = urlparse(url)
        info = FakeRequestInfo(path=o.path, params=parse_qs(o.query), headers=kwargs.get('headers'))
        print(info)
        self._call_instances.append(info)

        try:
            return self.responses[self._call_index]
        except IndexError:
            http500 = Response()
            http500.status_code = 500
            return http500

    @property
    def call_instances(self):
        return self._call_instances

class FakeRequestInfo(object):

    def __init__(self, path="", params={}, headers={}):
        self.path = path
        self.params = params
        self.headers = headers

    def __str__(self):
        return f"path:{self.path}, params:{self.params}, headers:{self.headers}"

def build_http_response(status_code, bytes=None, headers=None):
    # simple setup of fake response data
    response = Response()
    response.status_code = status_code
    response.encoding = 'utf-8'
    if bytes:
        response.raw = bytes
    if headers:
        response.headers.update(headers)
    return response

def test_issues_error():
    assert isinstance(issues.IssuesError(), Exception)

def test_abstract_session():
    with pytest.raises(issues.IssuesError):
        issues.Session().get()

def test_abstract_request_factory():
    with pytest.raises(issues.IssuesError):
        issues.AbstractRequestFactory().get("foo")

def test_abstract_repository():
    with pytest.raises(issues.IssuesError):
        issues.AbstractRepository().list()

def test_gitlab_session():
    session = issues.GitlabSession(access_token="x")
    assert session != None

def test_gitlab_session_adds_access_token():
    fake = FakeRequestFactory()
    fake.responses.append(build_http_response(
        200,
        bytes=io.BytesIO(b'[{"id":8000234,"iid":2,"project_id":"8273019","title":"test title","created_at":"2021-03-09T17:59:43.041Z"}]')))

    session = issues.GitlabSession(access_token="x", request_factory=fake)
    session.get("https://gitlab.com/api/v4/groups/gozynta/issues")
    assert 'PRIVATE-TOKEN' in fake.call_instances[-1].headers

def test_repo_list_pagination():
    """Make sure we page correctly.

    The GitLab API, when using the pagination=keyset parameter, returns the pages referenced
    as first, next, last via the link response header.
    """

    resp = []
    resp.append(build_http_response(
        200,
        headers={'link': '<https://gitlab.com/api/v4/groups/gozynta/issues?id=gozynta&milestone=mb_v1.3&non_archived=true&order_by=created_at&page=2&pagination=keyset&per_page=5&sort=desc&state=all&with_labels_details=false>; rel="next", <https://gitlab.com/api/v4/groups/gozynta/issues?id=gozynta&milestone=mb_v1.3&non_archived=true&order_by=created_at&page=1&pagination=keyset&per_page=5&sort=desc&state=all&with_labels_details=false>; rel="first", <https://gitlab.com/api/v4/groups/gozynta/issues?id=gozynta&milestone=mb_v1.3&non_archived=true&order_by=created_at&page=9&pagination=keyset&per_page=5&sort=desc&state=all&with_labels_details=false>; rel="last"'},
        bytes=io.BytesIO(b'[{"id":8000234,"iid":2,"project_id":"8273019","title":"test title","created_at":"2021-03-09T17:59:43.041Z"}]')))

    resp.append(build_http_response(
        200,
        headers={'link': '<https://gitlab.com/api/v4/groups/gozynta/issues?id=gozynta&milestone=mb_v1.3&non_archived=true&order_by=created_at&page=1&pagination=keyset&per_page=5&sort=desc&state=all&with_labels_details=false>; rel="first", <https://gitlab.com/api/v4/groups/gozynta/issues?id=gozynta&milestone=mb_v1.3&non_archived=true&order_by=created_at&page=9&pagination=keyset&per_page=5&sort=desc&state=all&with_labels_details=false>; rel="last"'},
        bytes=io.BytesIO(b'[{"id":8000235, "iid":3,"project_id":"8273019","title":"test title 2","created_at":"2021-03-09T17:59:43.041Z"}]')))

    fake = FakeRequestFactory()
    fake.responses = resp
    session = issues.GitlabSession(access_token="x", request_factory=fake)

    repo = issues.GitlabIssuesRepository(session, group="gozynta", milestone="mb_v1.3")
    issue_list = repo.list()

    assert len(fake.call_instances) == 2
    assert fake.call_instances[-1].path == "/api/v4/groups/gozynta/issues"
    assert 'pagination' in fake.call_instances[-1].params
    assert 'milestone' in fake.call_instances[-1].params

    assert len(issue_list) == 2
    assert issue_list[0] and issue_list[0].issue_id == 2
    assert issue_list[1] and issue_list[1].issue_id == 3


def test_repo_list_opened():

    fake = FakeRequestFactory()
    fake.responses.append(build_http_response(
        status_code=200,
        # XXX load payload from string to bytes more easily...
        bytes=io.BytesIO(b'[{"created_at": "2021-02-09T16:59:37.783Z","resource_type": "Issue","label":{"id": 18205357,"name": "workflow::Designing"},"action": "add"},{"created_at": "2021-02-09T17:00:49.416Z","resource_type": "Issue","label": {"id": 18205410,"name": "workflow::In Progress"},"action": "add"},{"created_at": "2021-02-09T17:00:49.416Z","resource_type": "Issue","label": {"id": 18205357,"name": "workflow::Designing"},"action": "remove"}]')))

    session = issues.GitlabSession(access_token="x", request_factory=fake)

    issue =issues.Issue({'iid': 3, 'project_id': '8273019', 'created_at': '2021-02-09T16:59:37.783Z' })

    labels = issues.GitlabIssueWorkflowRepository(session, issue)
    labelEvents = labels.list()
    #print(labelEvents)

    assert fake.call_instances[-1].path == "/api/v4/projects/8273019/issues/3/resource_label_events"
    assert labelEvents[0] == ('add', 'opened', issue.opened_at)
    assert labelEvents[2] == ('remove', 'opened', date_parser.parse("2021-02-09T16:59:37.783Z"))

def test_repo_list_closed():

    fake = FakeRequestFactory()
    fake.responses.append(build_http_response(
        status_code=200,
        # XXX load payload from string to bytes more easily...
        bytes=io.BytesIO(b'[{"created_at": "2021-02-09T16:59:37.783Z","resource_type": "Issue","label":{"id": 18205357,"name": "workflow::Designing"},"action": "add"},{"created_at": "2021-02-09T17:00:49.416Z","resource_type": "Issue","label": {"id": 18205410,"name": "workflow::In Progress"},"action": "add"},{"created_at": "2021-02-09T17:00:49.416Z","resource_type": "Issue","label": {"id": 18205357,"name": "workflow::Designing"},"action": "remove"}]')))

    session = issues.GitlabSession(access_token="x", request_factory=fake)

    issue =issues.Issue({'iid': 3, 'project_id': '8273019', 'created_at': '2021-02-09T16:59:37.783Z', 'closed_at': '2021-02-15T00:00:00.000Z' })

    labels = issues.GitlabIssueWorkflowRepository(session, issue)
    labelEvents = labels.list()


    assert fake.call_instances[-1].path == "/api/v4/projects/8273019/issues/3/resource_label_events"
    assert labelEvents[-2] == ('add', 'closed', issue.closed_at)
    assert labelEvents[-1] == ('remove', 'workflow::In Progress', issue.closed_at)

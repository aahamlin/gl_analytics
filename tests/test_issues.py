import pytest
import io
import datetime
from dateutil import parser as date_parser
from urllib.parse import urlparse, parse_qs
from requests import Response

import gl_analytics.issues as issues

from . import FakeRequestFactory, build_http_response

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
    assert 'PRIVATE-TOKEN' in fake.call_instances[-1].headers, 'Token missing from headers'

def test_request_factory_gets(requests_mock):
    requests_mock.get('https://mock-test.com', text='data')
    req = issues.RequestFactory()
    assert 'data' == req.get('https://mock-test.com').text

def test_issue_builder_from_dict():

    wfData =  [
        ('ready', '2021-03-14T15:15:00.000Z'),
        ('in progress', '2021-03-15T10:00:00.000Z'),
        ('done', '2021-03-16T10:00:00.000Z')
    ]
    data = {
        'iid': 1,
        'project_id': 3,
        'created_at': '2021-03-14T12:00:00.000Z',
        '_workflow': wfData
    }

    expectedOpenedAt = datetime.datetime(2021, 3,14, 12, tzinfo=datetime.timezone.utc)
    expectedLabelEvents = [
        ('ready', datetime.datetime(2021, 3, 14, 15, 15, 0, tzinfo=datetime.timezone.utc)),
        ('in progress', datetime.datetime(2021, 3, 15, 10, 0, tzinfo=datetime.timezone.utc)),
        ('done', datetime.datetime(2021, 3, 16, 10, 0, tzinfo=datetime.timezone.utc)),
    ]

    expected = issues.Issue(1, 3, expectedOpenedAt, label_events=expectedLabelEvents)

    actual = issues.issue_from(data)
    print(f"expected {expected} to actual {actual}")
    assert expected == actual

def test_repo_requires_group_and_milestone():
    with pytest.raises(ValueError):
        issues.GitlabIssuesRepository(issues.Session(), milestone="foo")
    with pytest.raises(ValueError):
        issues.GitlabIssuesRepository(issues.Session(), group="foo")

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

def test_workflows_resolver_calculates_label_events():
    resp = []
    resp.append(build_http_response(
        200,
        bytes=io.BytesIO(b'[{"id":8000234,"iid":2,"project_id":"8273019","title":"test title","created_at":"2021-03-09T17:59:43.041Z"}]')))

    resp.append(build_http_response(
        status_code=200,
        # XXX load payload from string to bytes more easily...
        bytes=io.BytesIO(b'[{"created_at": "2021-02-09T16:59:37.783Z","resource_type": "Issue","label":{"id": 18205357,"name": "workflow::Designing"},"action": "add"},{"created_at": "2021-02-09T17:00:49.416Z","resource_type": "Issue","label": {"id": 18205410,"name": "workflow::In Progress"},"action": "add"},{"created_at": "2021-02-09T17:00:49.416Z","resource_type": "Issue","label": {"id": 18205357,"name": "workflow::Designing"},"action": "remove"}]')))

    fake = FakeRequestFactory()
    fake.responses = resp
    session = issues.GitlabSession(access_token="x", request_factory=fake)

    repo = issues.GitlabIssuesRepository(session, group="gozynta", milestone="mb_v1.3", resolvers=[issues.GitlabWorkflowResolver])
    issue_list = repo.list()

    assert len(fake.call_instances) == 2
    assert fake.call_instances[0].path == "/api/v4/groups/gozynta/issues"
    assert fake.call_instances[-1].path == "/api/v4/projects/8273019/issues/2/resource_label_events"

    assert len(issue_list) == 1
    assert len(issue_list[0].label_events) == 2 # designing, in progress

def test_workflows_resolver_skips_non_qualifying_events():
    resp = []
    resp.append(build_http_response(
        200,
        bytes=io.BytesIO(b'[{"id":8000234,"iid":2,"project_id":"8273019","title":"test title","created_at":"2021-03-09T17:59:43.041Z"}]')))

    resp.append(build_http_response(
        status_code=200,
        # XXX load payload from string to bytes more easily...
        bytes=io.BytesIO(b'[{"created_at": "2021-02-09T16:59:37.783Z","resource_type": "Issue","label":{"id": 18205357,"name": "workflow::Designing"},"action": "add"},{"created_at": "2021-02-09T17:00:49.416Z","resource_type": "Issue","label": {"id": 18205410,"name": "NonQualifyingLabel"},"action": "add"},{"created_at": "2021-02-09T17:00:49.416Z","resource_type": "Issue","label": {"id": 18205357,"name": "workflow::Designing"},"action": "remove"}]')))

    fake = FakeRequestFactory()
    fake.responses = resp
    session = issues.GitlabSession(access_token="x", request_factory=fake)

    repo = issues.GitlabIssuesRepository(session, group="gozynta", milestone="mb_v1.3", resolvers=[issues.GitlabWorkflowResolver])
    issue_list = repo.list()

    assert len(fake.call_instances) == 2
    assert fake.call_instances[0].path == "/api/v4/groups/gozynta/issues"
    assert fake.call_instances[-1].path == "/api/v4/projects/8273019/issues/2/resource_label_events"

    assert len(issue_list) == 1
    assert len(issue_list[0].label_events) == 1 # designing

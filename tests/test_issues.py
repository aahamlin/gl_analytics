import pytest
import datetime

import gl_analytics.issues as issues

from .data import TestData, to_bytes, to_link_header

def test_issues_error():
    assert isinstance(issues.IssuesError(), Exception)

def test_abstract_session():
    with pytest.raises(issues.IssuesError):
        issues.Session().get()

def test_abstract_repository():
    with pytest.raises(issues.IssuesError):
        issues.AbstractRepository().list()

def test_abstract_resolver():
    with pytest.raises(issues.IssuesError):
        issues.AbstractResolver().resolve()

def test_gitlab_session():
    session = issues.GitlabSession(access_token="x")
    assert session is not None

def test_gitlab_session_adds_access_token(requests_mock):
    requests_mock.get(
        issues.GITLAB_URL_BASE + '/groups/gozynta/issues',
        body=to_bytes(TestData.issues.iid2.body))

    session = issues.GitlabSession(access_token="x")
    session.get("https://gitlab.com/api/v4/groups/gozynta/issues")
    assert 'PRIVATE-TOKEN' in requests_mock.last_request.headers
    assert requests_mock.last_request.headers['PRIVATE-TOKEN'] == "x"

def test_issue_builder_from_dict():

    wfData = [
        ('ready', '2021-03-14T15:15:00.000Z'),
        ('in progress', '2021-03-15T10:00:00.000Z'),
        ('done', '2021-03-16T10:00:00.000Z')
    ]
    data = {
        'iid': 1,
        'project_id': 3,
        'created_at': '2021-03-14T12:00:00.000Z',
        '_scoped_labels': wfData  # XXX Improve how ScopedLabelResolver does this operation
    }

    expectedOpenedAt = datetime.datetime(2021, 3, 14, 12, tzinfo=datetime.timezone.utc)
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

def test_repo_list_pagination(requests_mock):
    """Make sure we page correctly.

    The GitLab API, when using the pagination=keyset parameter, returns the pages referenced
    as first, next, last via the link response header.
    """

    requests_mock.get(
        issues.GITLAB_URL_BASE + '/groups/gozynta/issues',
        body=to_bytes(TestData.issues.iid2.body),
        headers=to_link_header(TestData.issues.iid2.headers.link))

    requests_mock.get(
        issues.GITLAB_URL_BASE + '/groups/gozynta/issues?id=gozynta&milestone=mb_v1.3&page=2&pagination=keyset',
        body=to_bytes(TestData.issues.iid3.body))

    session = issues.GitlabSession(access_token="x")

    repo = issues.GitlabIssuesRepository(session, group="gozynta", milestone="mb_v1.3")
    issue_list = repo.list()

    assert len(issue_list) == 2
    assert issue_list[0] and issue_list[0].issue_id == 2
    assert issue_list[1] and issue_list[1].issue_id == 3

def test_workflows_resolver_calculates_label_events(requests_mock):

    requests_mock.get(
        issues.GITLAB_URL_BASE + '/groups/gozynta/issues',
        body=to_bytes(TestData.issues.iid2.body))

    requests_mock.get(
        issues.GITLAB_URL_BASE + '/projects/8273019/issues/2/resource_label_events',
        body=to_bytes(TestData.resource_label_events[0]))

    session = issues.GitlabSession(access_token="x")

    repo = issues.GitlabIssuesRepository(session, group="gozynta", milestone="mb_v1.3",
                                         resolvers=[issues.GitlabScopedLabelResolver])
    issue_list = repo.list()

    assert len(issue_list) == 1
    assert len(issue_list[0].label_events) == 2 # designing, in progress

def test_workflows_resolver_skips_non_qualifying_events(requests_mock):

    requests_mock.get(
        issues.GITLAB_URL_BASE + '/groups/gozynta/issues',
        body=to_bytes(TestData.issues.iid2.body))

    requests_mock.get(
        issues.GITLAB_URL_BASE + '/projects/8273019/issues/2/resource_label_events',
        body=to_bytes(TestData.resource_label_events[1]))

    session = issues.GitlabSession(access_token="x")

    repo = issues.GitlabIssuesRepository(session, group="gozynta", milestone="mb_v1.3",
                                         resolvers=[issues.GitlabScopedLabelResolver])
    issue_list = repo.list()

    assert len(issue_list) == 1
    assert len(issue_list[0].label_events) == 1 # designing

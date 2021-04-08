import pytest
import datetime

import gl_analytics.issues as issues


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


def test_gitlab_session(session):
    assert session is not None
    assert session.baseurl is not None
    assert session.baseurl == "https://gitlab.com/api/v4/"
    assert session._access_token is not None


def test_gitlab_session_constructs_abs_baseurl():
    session = issues.GitlabSession("https://gitlab.com/api/v4")
    assert session.baseurl is not None
    assert session.baseurl == "https://gitlab.com/api/v4/"


@pytest.mark.usefixtures("get_issues")
def test_gitlab_session_adds_access_token(session, requests_mock):
    session.get("https://gitlab.com/api/v4/groups/gozynta/issues")
    assert "PRIVATE-TOKEN" in requests_mock.last_request.headers
    assert requests_mock.last_request.headers["PRIVATE-TOKEN"] == "x"


@pytest.mark.usefixtures("get_issues")
def test_gitlab_session_requires_relative_path(session, requests_mock):
    with pytest.raises(ValueError):
        session.get("/groups/gozynta/issues")


def test_issue_builds_from_dict():

    wfData = [
        ("ready", "2021-03-14T15:15:00.000Z"),
        ("in progress", "2021-03-15T10:00:00.000Z"),
        ("done", "2021-03-16T10:00:00.000Z"),
    ]
    data = {
        "iid": 1,
        "project_id": 3,
        "created_at": "2021-03-14T12:00:00.000Z",
        "_scoped_labels": wfData,  # XXX Improve how ScopedLabelResolver does this operation
    }

    expectedOpenedAt = datetime.datetime(2021, 3, 14, 12, tzinfo=datetime.timezone.utc)
    expectedLabelEvents = [
        (
            "ready",
            datetime.datetime(2021, 3, 14, 15, 15, 0, tzinfo=datetime.timezone.utc),
        ),
        (
            "in progress",
            datetime.datetime(2021, 3, 15, 10, 0, tzinfo=datetime.timezone.utc),
        ),
        ("done", datetime.datetime(2021, 3, 16, 10, 0, tzinfo=datetime.timezone.utc)),
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


@pytest.mark.usefixtures("get_paged_issues")
def test_repo_list_pagination(session, requests_mock):
    """Make sure we page correctly.

    The GitLab API, when using the pagination=keyset parameter, returns the pages referenced
    as first, next, last via the link response header.
    """
    repo = issues.GitlabIssuesRepository(session, group="gozynta", milestone="mb_v1.3")
    issue_list = repo.list()

    assert len(issue_list) == 2
    assert issue_list[0] and issue_list[0].issue_id == 2
    assert issue_list[1] and issue_list[1].issue_id == 3


@pytest.mark.usefixtures("get_issues")
@pytest.mark.usefixtures("get_workflow_labels")
def test_scopelabelresolver_includes_qualifying_events(session):

    repo = issues.GitlabIssuesRepository(
        session,
        group="gozynta",
        milestone="mb_v1.3",
        resolvers=[issues.GitlabScopedLabelResolver],
    )
    issue_list = repo.list()

    assert len(issue_list) == 1
    assert len(issue_list[0].label_events) == 2  # designing, in progress


@pytest.mark.usefixtures("get_issues")
@pytest.mark.usefixtures("get_mixed_labels")
def test_scopedlabelresolver_skips_non_qualifying_events(session):

    repo = issues.GitlabIssuesRepository(
        session,
        group="gozynta",
        milestone="mb_v1.3",
        resolvers=[issues.GitlabScopedLabelResolver],
    )
    issue_list = repo.list()

    assert len(issue_list) == 1
    assert len(issue_list[0].label_events) == 1  # designing

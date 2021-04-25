import pytest
import datetime

from dateutil.utils import within_delta

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


def compare_label_events(expected, actual):
    return (
        expected[0] == actual[0]
        and (expected[0] == actual[0] or within_delta(expected[1], actual[1], datetime.timedelta(seconds=1)))
        and (expected[0] == actual[0] or within_delta(expected[2], actual[2], datetime.timedelta(seconds=1)))
    )


@pytest.mark.usefixtures("get_issues")
@pytest.mark.usefixtures("get_workflow_labels")
def test_scopelabelresolver_includes_qualifying_events(session):

    repo = issues.GitlabIssuesRepository(
        session,
        group="gozynta",
        milestone="mb_v1.3",
        resolvers=[issues.GitlabScopedLabelResolver],
    )

    expected_labels = [
        (
            "Designing",
            datetime.datetime(
                2021, 2, 9, 16, 59, 37, 783, tzinfo=datetime.timezone.utc
            ),
            datetime.datetime(2021, 2, 9, 17, 0, 49, 416, tzinfo=datetime.timezone.utc),
        ),
        (
            "In Progress",
            datetime.datetime(2021, 2, 9, 17, 0, 49, 416, tzinfo=datetime.timezone.utc),
            None,
        ),
    ]

    issue_list = repo.list()
    assert len(issue_list) == 1

    the_issue = issue_list[0]
    assert len(the_issue.label_events) == 2  # designing, in progress

    assert all(compare_label_events(a, b) for a, b in zip(expected_labels, the_issue.label_events))


@pytest.mark.usefixtures("get_issues")
@pytest.mark.usefixtures("get_mixed_labels")
def test_scopedlabelresolver_skips_non_qualifying_events(session):

    repo = issues.GitlabIssuesRepository(
        session,
        group="gozynta",
        milestone="mb_v1.3",
        resolvers=[issues.GitlabScopedLabelResolver],
    )

    expected_labels = [
        (
            "Designing",
            datetime.datetime(
                2021, 2, 9, 16, 59, 37, 783, tzinfo=datetime.timezone.utc
            ),
            datetime.datetime(2021, 2, 9, 17, 0, 49, 416, tzinfo=datetime.timezone.utc),
        )
    ]

    issue_list = repo.list()

    assert len(issue_list) == 1

    the_issue = issue_list[0]
    assert len(the_issue.label_events) == 1  # designing

    assert compare_label_events(expected_labels[0], the_issue.label_events[0])

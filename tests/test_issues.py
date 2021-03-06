# from types import SimpleNamespace
import pytest
import datetime

from dateutil.utils import within_delta

import gl_analytics.issues as issues


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


def test_repo_requires_group(session):
    with pytest.raises(ValueError):
        issues.GitlabIssuesRepository(session)


def test_repo_builds_url(session):
    repo = issues.GitlabIssuesRepository(session, group="gozynta")
    assert repo.url == "groups/gozynta/issues"


@pytest.fixture
def opened():
    return datetime.datetime(2021, 3, 15, tzinfo=datetime.timezone.utc)


@pytest.fixture
def closed(opened):
    return opened + datetime.timedelta(days=1)


@pytest.fixture
def issue(opened, closed):
    issue = issues.Issue(1, 2, opened, issue_type="TypeX")
    issue.history.add_events([("closed", closed, None)])
    return issue


@pytest.fixture
def moved_issue(opened, closed):
    """
    When an item is moved, the resource and label events are no longer tracked with the original item.
    """
    issue = issues.Issue(1, 2, opened, closed_at=closed, issue_type="TypeX")
    return issue


def test_issue_contains_issue_id(issue):
    assert issue.issue_id == 1


def test_issue_contains_project_id(issue):
    assert issue.project_id == 2


def test_issue_contains_type(issue):
    assert issue.issue_type == "TypeX"


def test_issue_contains_opened_at(opened, issue):
    assert issue.opened_at == opened


def test_issue_contains_closed_at(closed, issue):
    assert issue.closed_at == closed


def test_issue_closed_should_fallback_closed_at(closed, moved_issue):
    """
    The use case that uncovered this will help explain it better. In gozynta.com project, issue #65 was labeled
    In Progress and then moved to the cwacc project, issue #286. Searching the history of events of gozynta.com#65
    only shows the last in progress date, but the closed_at field still resolves to the close date of cwacc#286.
    """
    assert moved_issue.closed_at == closed


def test_issue_history_contains_opened_and_closed(opened, closed, issue):
    expected = [("opened", opened, closed), ("closed", closed, None)]
    assert len(issue.history) == len(expected)
    assert all([a == b for a, b in zip(issue.history, expected)])


@pytest.mark.usefixtures("get_paged_issues")
def test_repo_list_pagination(session):
    """Make sure we page correctly.

    The GitLab API, when using the pagination=keyset parameter, returns the pages referenced
    as first, next, last via the link response header.
    """
    repo = issues.GitlabIssuesRepository(session, group="gozynta")
    issue_list = repo.list(milestone="mb_v1.3")

    assert len(issue_list) == 2
    assert issue_list[0] and issue_list[0].issue_id == 2
    assert issue_list[1] and issue_list[1].issue_id == 3


def compare_label_events(expected, actual):
    """Helper function for test asserts."""
    return (
        expected[0] == actual[0]
        and (expected[0] == actual[0] or within_delta(expected[1], actual[1], datetime.timedelta(seconds=1)))
        and (expected[0] == actual[0] or within_delta(expected[2], actual[2], datetime.timedelta(seconds=1)))
    )


@pytest.fixture
def scopedlabel_repository(session):
    repo = issues.GitlabIssuesRepository(
        session,
        group="gozynta",
        resolvers=[issues.GitlabScopedLabelResolver],
    )
    return repo


@pytest.mark.usefixtures("get_issues")
@pytest.mark.usefixtures("get_workflow_labels")
def test_scopelabelresolver_includes_qualifying_events(scopedlabel_repository):

    expected_labels = [
        ("opened", datetime.datetime(2021, 2, 9, 12, 59, 43, tzinfo=datetime.timezone.utc), None),
        (
            "Designing",
            datetime.datetime(2021, 2, 9, 16, 59, 37, 783, tzinfo=datetime.timezone.utc),
            datetime.datetime(2021, 2, 9, 17, 0, 49, 416, tzinfo=datetime.timezone.utc),
        ),
        (
            "In Progress",
            datetime.datetime(2021, 2, 9, 17, 0, 49, 416, tzinfo=datetime.timezone.utc),
            None,
        ),
    ]

    issue_list = scopedlabel_repository.list(milestone="mb_v1.3")
    assert len(issue_list) == 1

    the_issue = issue_list[0]
    assert len(the_issue.history) == 3  # designing, in progress
    print(the_issue.history)
    assert all(compare_label_events(a, b) for a, b in zip(expected_labels, the_issue.history))


@pytest.mark.usefixtures("get_closed_issues")
@pytest.mark.usefixtures("get_empty_resource_events")
def test_issue_contains_fallback_closed_date(scopedlabel_repository):

    issue_list = scopedlabel_repository.list(milestone="mb_v1.3")
    assert len(issue_list) == 1

    the_issue = issue_list[0]
    assert len(the_issue.history) == 2

    assert the_issue.closed_at is not None


@pytest.mark.usefixtures("get_issues")
@pytest.mark.usefixtures("get_mixed_labels")
def test_scopedlabelresolver_skips_non_qualifying_events(scopedlabel_repository):

    expected_labels = [
        ("opened", datetime.datetime(2021, 2, 9, 12, 59, 43, tzinfo=datetime.timezone.utc), None),
        (
            "Designing",
            datetime.datetime(2021, 2, 9, 16, 59, 37, 783, tzinfo=datetime.timezone.utc),
            datetime.datetime(2021, 2, 9, 17, 0, 49, 416, tzinfo=datetime.timezone.utc),
        ),
    ]

    issue_list = scopedlabel_repository.list(milestone="mb_v1.3")

    assert len(issue_list) == 1

    the_issue = issue_list[0]
    assert len(the_issue.history) == 2  # opened, designing

    assert compare_label_events(expected_labels[1], the_issue.history[1])


@pytest.mark.usefixtures("get_closed_workflow_labels")
def test_stateeventresolver_records_states(session):
    state_event_resolver = issues.GitLabStateEventResolver(session)
    issue = issues.Issue(2, 8273019, datetime.datetime(2021, 3, 9, 12, tzinfo=datetime.timezone.utc))
    state_event_resolver.resolve(issue)
    assert issue.closed_at == datetime.datetime(2021, 3, 15, 12, tzinfo=datetime.timezone.utc)


@pytest.mark.usefixtures("get_closed_by_merge_request")
def test_closedbyresolver_records_merge_requests(session):
    closed_by_resolver = issues.GitLabClosedByMergeRequestResolver(session)
    issue = issues.Issue(2, 8273019, datetime.datetime(2021, 3, 9, 12, tzinfo=datetime.timezone.utc))
    closed_by_resolver.resolve(issue)
    assert issue.history[1] == (
        "merge_request",
        datetime.datetime(2021, 3, 13, tzinfo=datetime.timezone.utc),
        datetime.datetime(2021, 3, 19, tzinfo=datetime.timezone.utc),
    )


@pytest.mark.usefixtures("get_closed_by_merge_request")
def test_closedbyresolver_skips_merge_requests_before_opened(session):
    closed_by_resolver = issues.GitLabClosedByMergeRequestResolver(session)
    issue = issues.Issue(2, 8273019, datetime.datetime(2021, 3, 14, 12, tzinfo=datetime.timezone.utc))
    closed_by_resolver.resolve(issue)
    assert len(issue.history) == 1
    assert issue.history[0][0] == "opened"


@pytest.mark.usefixtures("get_issues_with_label")
def test_issue_with_typelabel_should_set_type(session):
    repo = issues.GitlabIssuesRepository(session, group="gozynta")

    results = repo.list(milestone="mb_v1.3")
    assert len(results) == 1
    the_issue = results[0]
    assert the_issue.issue_type == "Bug"


@pytest.mark.usefixtures("get_issues")
def test_issue_without_typelabel_should_not_set_type(session):
    repo = issues.GitlabIssuesRepository(session, group="gozynta")

    results = repo.list(milestone="mb_v1.3")
    assert len(results) == 1
    the_issue = results[0]
    assert the_issue.issue_type is None


def test_history_opened(opened):
    history = issues.History(opened, None)
    assert len(history) == 1
    assert history[0] == ("opened", opened, None)


def test_history_closed(opened, closed):
    history = issues.History(opened, closed_at=closed)
    assert len(history) == 2
    assert history[-1] == ("closed", closed, None)
    assert history[0] == ("opened", opened, closed)


def test_history_add_closed_event(opened, closed):
    history = issues.History(opened)
    history.add_events([("closed", closed, None)])
    assert len(history) == 2
    assert history[-1] == ("closed", closed, None)
    assert history[0] == ("opened", opened, closed)


def test_history_add_events(opened, closed):
    history = issues.History(opened)
    in_progress = closed - datetime.timedelta(hours=2)
    history.add_events([("in progress", in_progress, None), ("closed", closed, None)])
    assert len(history) == 3
    assert history[-1] == ("closed", closed, None)
    assert history[0] == ("opened", opened, in_progress)
    assert history[1] == ("in progress", in_progress, closed)


def test_history_closed_event_supersedes_closed(opened, closed):
    history = issues.History(opened, closed)
    in_progress = closed - datetime.timedelta(hours=2)
    closed_event = closed + datetime.timedelta(minutes=1)
    history.add_events([("in progress", in_progress, None), ("closed", closed_event, None)])
    assert len(history) == 3
    assert history[-1] == ("closed", closed_event, None)
    assert history[0] == ("opened", opened, in_progress)
    assert history[1] == ("in progress", in_progress, closed_event)

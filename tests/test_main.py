import datetime
import sys

from gl_analytics.__main__ import main, build_transitions
from gl_analytics.issues import GITLAB_URL_BASE, Issue

from .data import TestData, to_bytes


def test_build_transitions_from_issues():
    created_at = datetime.datetime(2021, 3, 13, 10, tzinfo=datetime.timezone.utc)
    wfData = [
        ("ready", datetime.datetime(2021, 3, 14, 10, tzinfo=datetime.timezone.utc)),
        (
            "in progress",
            datetime.datetime(2021, 3, 15, 10, tzinfo=datetime.timezone.utc),
        ),
        ("done", datetime.datetime(2021, 3, 16, 10, tzinfo=datetime.timezone.utc)),
    ]

    issues = [
        Issue(1, 2, created_at, label_events=wfData),
        Issue(2, 2, created_at, label_events=wfData),
    ]
    transitions = build_transitions(issues)
    assert len(transitions) == 2
    assert all([len(t) == 4 for t in transitions])  # opened, ready, in progress, done


def test_main_prints_csv(capsys, requests_mock):
    """Test that the main function runs without error."""
    requests_mock.get(
        GITLAB_URL_BASE + "/groups/gozynta/issues",
        body=to_bytes(TestData.issues.iid2.body),
    )
    requests_mock.get(
        GITLAB_URL_BASE + "/projects/8273019/issues/2/resource_label_events",
        body=to_bytes(TestData.resource_label_events[0]),
    )

    capsys.readouterr()
    main(access_token="x", group="gozynta", milestone="mb_v1.3", file=sys.stdout)
    captured = capsys.readouterr()
    assert (
        ",opened,workflow::Designing,workflow::Needs Design Approval,workflow::Ready"
        + ",workflow::In Progress,workflow::Code Review,closed"
        in captured.out
    )
    assert "2021-04-07,0,0,0,0,1,0,0" in captured.out

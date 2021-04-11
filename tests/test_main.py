import datetime
import pytest

from gl_analytics.__main__ import Main
from gl_analytics.__main__ import build_transitions
from gl_analytics.issues import Issue


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


def test_main_require_user_token(monkeypatch):
    main = Main(["-m", "mb_v1.3"])
    monkeypatch.delitem(main.config, "TOKEN", raising=False)

    with pytest.raises(KeyError):
        main.run()


def test_main_must_find_base_url(monkeypatch):
    main = Main(["-m", "mb_v1.3"])
    monkeypatch.delitem(main.config, "GITLAB_BASE_URL", raising=True)

    with pytest.raises(KeyError):
        main.run()


@pytest.mark.usefixtures("get_issues")
@pytest.mark.usefixtures("get_workflow_labels")
def test_main_prints_csv(capsys, monkeypatch):
    """Test that the main function runs without error."""
    main = Main(["-m", "mb_v1.3"])
    monkeypatch.setitem(main.config, "TOKEN", "x")

    capsys.readouterr()
    main.run()
    captured = capsys.readouterr()
    assert (
        ",opened,workflow::Designing,workflow::Needs Design Approval,workflow::Ready"
        + ",workflow::In Progress,workflow::Code Review,closed"
        in captured.out
    )
    assert "2021-04-07,0,0,0,0,1,0,0" in captured.out

import datetime
import pytest

import numpy as np
import pandas as pd

from tests import change_directory, read_filepath

from gl_analytics.__main__ import Main
from gl_analytics.__main__ import build_transitions
from gl_analytics.issues import Issue


def test_build_transitions_from_issues():

    created_at = datetime.datetime(2021, 3, 13, 10, tzinfo=datetime.timezone.utc)
    wfData = [
        (
            "ready",
            datetime.datetime(2021, 3, 14, 10, tzinfo=datetime.timezone.utc),
            datetime.datetime(2021, 3, 15, 10, tzinfo=datetime.timezone.utc),
        ),
        (
            "in progress",
            datetime.datetime(2021, 3, 15, 10, tzinfo=datetime.timezone.utc),
            datetime.datetime(2021, 3, 16, 10, tzinfo=datetime.timezone.utc)
        ),
        (
            "done",
            datetime.datetime(2021, 3, 16, 10, tzinfo=datetime.timezone.utc),
            None
        ),
    ]

    issues = [
        Issue(1, 2, created_at, label_events=wfData),
        Issue(2, 2, created_at, label_events=wfData),
    ]
    transitions = build_transitions(issues)
    expected = pd.DataFrame(
        {
            "opened": [1, 0, np.nan, np.nan],
            "ready": [np.nan, 1, 0, np.nan],
            "in progress": [np.nan, np.nan, 1, 0],
            "done": [np.nan, np.nan, np.nan, 1]
        },
        index=[
            created_at,
            datetime.datetime(2021, 3, 14, 10, tzinfo=datetime.timezone.utc),
            datetime.datetime(2021, 3, 15, 10, tzinfo=datetime.timezone.utc),
            datetime.datetime(2021, 3, 16, 10, tzinfo=datetime.timezone.utc),
        ]
    )
    print(expected)
    assert len(transitions) == 2
    print([t.data for t in transitions])
    assert all([expected.equals(t.data) for t in transitions])


def test_main_require_user_token(monkeypatch):
    main = Main(["-m", "mb_v1.3"])
    monkeypatch.delitem(main.config, "TOKEN")

    with pytest.raises(KeyError):
        main.run()


def test_main_must_find_base_url(monkeypatch):
    main = Main(["-m", "mb_v1.3"])
    monkeypatch.delitem(main.config, "GITLAB_BASE_URL", raising=True)

    with pytest.raises(KeyError):
        main.run()


@pytest.mark.usefixtures("get_issues")
@pytest.mark.usefixtures("get_workflow_labels")
def test_main_prints_csv(capsys, monkeypatch, patch_datetime_now):
    """Test that the main function runs without error.
    """
    main = Main(["-m", "mb_v1.3", "-r", "csv"])
    monkeypatch.setitem(main.config, "TOKEN", "x")

    capsys.readouterr()
    main.run()
    captured = capsys.readouterr()
    print("\noutput captured\n", captured.out)
    assert (
        ",opened,Ready,In Progress,Code Review,closed"
        in captured.out
    )
    assert "2021-03-07,0.0,0.0,1.0,0.0,0.0" in captured.out


@pytest.mark.usefixtures("get_issues")
@pytest.mark.usefixtures("get_workflow_labels")
def test_main_writes_csv(filepath_csv, monkeypatch, patch_datetime_now):
    """Test that the main function runs without error.
    """
    str_filepath = str(filepath_csv.resolve())
    main = Main(["-m", "mb_v1.3", "-r", "csv", "-o", str_filepath])
    monkeypatch.setitem(main.config, "TOKEN", "x")

    main.run()
    content = read_filepath(filepath_csv)
    assert (
        ",opened,Ready,In Progress,Code Review,closed"
        in content
    )
    assert "2021-03-07,0.0,0.0,1.0,0.0,0.0" in content


@pytest.mark.usefixtures("get_issues")
@pytest.mark.usefixtures("get_workflow_labels")
def test_main_exports_png(monkeypatch, filepath_png):
    """Test that the main function runs without error.
    """
    str_filepath = str(filepath_png.resolve())
    print(f"export to {str_filepath}")
    main = Main(["-m", "mb_v1.3", "-r", "plot", "-o", str_filepath])
    monkeypatch.setitem(main.config, "TOKEN", "x")

    main.run()
    assert filepath_png.exists()


@pytest.mark.usefixtures("get_issues")
@pytest.mark.usefixtures("get_workflow_labels")
@pytest.mark.usefixtures("patch_datetime_now")
def test_main_exports_default_png(monkeypatch, tmp_path, fake_timestamp):
    """Test that the main function runs without error.
    """
    with change_directory(tmp_path):
        main = Main(["-m", "mb_v1.3", "-r", "plot"])
        monkeypatch.setitem(main.config, "TOKEN", "x")
        main.run()

    timestamp_str = fake_timestamp.strftime("%Y%m%d_%H%M%S")
    assert tmp_path.joinpath(f"cfd_{timestamp_str}.png").exists()

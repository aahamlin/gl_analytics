from datetime import datetime, timezone
import pytest

import pandas as pd

from tests import change_directory, read_filepath, records

from gl_analytics.__main__ import Main
from gl_analytics.__main__ import build_transitions
from gl_analytics.issues import Issue


def test_build_transitions_from_issues():

    created_at = datetime(2021, 3, 13, 10, tzinfo=timezone.utc)

    test_data0 = list(records(2, 1, created_at, steps=["ready", "in progress", "done"]))
    print(test_data0)
    test_data1 = list(records(2, 2, created_at, steps=["ready", "in progress", "done"]))
    print(test_data1)
    expected0 = pd.DataFrame.from_records(test_data0, index=["datetime"])
    expected1 = pd.DataFrame.from_records(test_data1, index=["datetime"])

    wfData = [
        (
            "ready",
            datetime(2021, 3, 14, 10, tzinfo=timezone.utc),
            datetime(2021, 3, 15, 10, tzinfo=timezone.utc),
        ),
        (
            "in progress",
            datetime(2021, 3, 15, 10, tzinfo=timezone.utc),
            datetime(2021, 3, 16, 10, tzinfo=timezone.utc)
        ),
        (
            "done",
            datetime(2021, 3, 16, 10, tzinfo=timezone.utc),
            None
        ),
    ]

    issues = [
        Issue(1, 2, created_at, label_events=wfData),
        Issue(2, 2, created_at, label_events=wfData),
    ]

    transitions = build_transitions(issues)

    print(expected0)
    print(expected1)
    assert len(transitions) == 2
    print(transitions[0])
    print(transitions[1])

    assert all([expected0.equals(transitions[0].data)])
    assert all([expected1.equals(transitions[1].data)])


def test_main_require_user_token(monkeypatch):
    main = Main(["cumulativeflow", "-m", "mb_v1.3"])
    monkeypatch.delitem(main.config, "TOKEN")

    with pytest.raises(KeyError):
        main.run()


def test_main_must_find_base_url(monkeypatch):
    main = Main(["flow", "-m", "mb_v1.3"])
    monkeypatch.delitem(main.config, "GITLAB_BASE_URL", raising=True)

    with pytest.raises(KeyError):
        main.run()


@pytest.mark.usefixtures("get_issues")
@pytest.mark.usefixtures("get_workflow_labels")
def test_main_cumulative_flow_prints_csv(capsys, monkeypatch, patch_datetime_now):
    """Test that the main function runs without error.
    """
    main = Main(["cf", "-m", "mb_v1.3", "-r", "csv"])
    monkeypatch.setitem(main.config, "TOKEN", "x")

    capsys.readouterr()
    main.run()
    captured = capsys.readouterr()
    print("\noutput captured\n", captured.out)
    assert (
        ",opened,In Progress,Code Review,closed"
        in captured.out
    )
    assert "2021-03-07,0.0,1.0,0.0,0.0" in captured.out


@pytest.mark.usefixtures("get_issues")
@pytest.mark.usefixtures("get_workflow_labels")
def test_main_cumulative_flow_writes_csv(filepath_csv, monkeypatch, patch_datetime_now):
    """Test that the main function runs without error.
    """
    str_filepath = str(filepath_csv.resolve())
    main = Main(["cf", "-m", "mb_v1.3", "-r", "csv", "-o", str_filepath])
    monkeypatch.setitem(main.config, "TOKEN", "x")

    main.run()
    content = read_filepath(filepath_csv)
    assert (
        ",opened,In Progress,Code Review,closed"
        in content
    )
    assert "2021-03-07,0.0,1.0,0.0,0.0" in content


@pytest.mark.usefixtures("get_issues")
@pytest.mark.usefixtures("get_workflow_labels")
def test_main_cumulative_flow_exports_png(monkeypatch, filepath_png):
    """Test that the main function runs without error.
    """

    str_filepath = str(filepath_png.resolve())
    print(f"export to {str_filepath}")
    main = Main(["cf", "-m", "mb_v1.3", "-r", "plot", "-o", str_filepath])
    monkeypatch.setitem(main.config, "TOKEN", "x")

    main.run()
    assert filepath_png.exists()


@pytest.mark.usefixtures("get_issues")
@pytest.mark.usefixtures("get_workflow_labels")
@pytest.mark.usefixtures("patch_datetime_now")
def test_main_cumulative_flow_exports_default_png(monkeypatch, tmp_path, fake_timestamp):
    """Test that the main function runs without error.
    """
    with change_directory(tmp_path):
        main = Main(["cf", "-m", "mb_v1.3", "-r", "plot"])
        monkeypatch.setitem(main.config, "TOKEN", "x")
        main.run()

    timestamp_str = fake_timestamp.strftime("%Y%m%d_%H%M%S")
    assert tmp_path.joinpath(f"cfd_{timestamp_str}.png").exists()


def test_cycletime_requires_user_token(monkeypatch):
    main = Main(["cycletime", "-m", "mb_v1.3"])
    monkeypatch.delitem(main.config, "TOKEN")

    with pytest.raises(KeyError):
        main.run()


def test_cycletime_must_find_base_url(monkeypatch):
    main = Main(["cy", "-m", "mb_v1.3"])
    monkeypatch.delitem(main.config, "GITLAB_BASE_URL", raising=True)

    with pytest.raises(KeyError):
        main.run()


@pytest.mark.usefixtures("get_issues")
@pytest.mark.usefixtures("get_workflow_labels")
def test_cycletime_prints_csv(capsys, monkeypatch, patch_datetime_now):
    """Test that the main function runs without error.
    """
    main = Main(["cy", "-m", "mb_v1.3", "-r", "csv"])
    monkeypatch.setitem(main.config, "TOKEN", "x")

    capsys.readouterr()
    main.run()
    captured = capsys.readouterr()
    print("\noutput captured\n", captured.out)
    assert (
        "datetime,type,lead,cycle"
        in captured.out
    )

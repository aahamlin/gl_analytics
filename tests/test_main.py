import pytest

from tests import change_directory, read_filepath

import gl_analytics.__main__ as m


def test_main_require_command(capsys):
    with pytest.raises(SystemExit) as se:
        m.main([])
    assert se.value.code != 0


@pytest.mark.parametrize("cmd", ["cumulativeflow", "cf", "flow", "cycletime", "cy"])
def test_main_supports_commands(capsys, cmd):

    with pytest.raises(SystemExit) as se:
        m.main([cmd, "--help"])

    assert se.value.code == 0


def test_main_require_user_token(monkeypatch):
    monkeypatch.delitem(m.config, "TOKEN")
    with pytest.raises(KeyError):
        m.main(["cumulativeflow", "-m", "mb_v1.3"])


def test_main_must_find_base_url(monkeypatch):
    monkeypatch.delitem(m.config, "GITLAB_BASE_URL", raising=True)
    with pytest.raises(KeyError):
        m.main(["flow", "-m", "mb_v1.3"])


@pytest.mark.usefixtures("get_issues")
@pytest.mark.usefixtures("get_workflow_labels")
def test_main_cumulative_flow_prints_csv(capsys, monkeypatch, patch_datetime_now):
    """Test that the main function runs without error."""
    monkeypatch.setitem(m.config, "TOKEN", "x")

    capsys.readouterr()
    m.main(["cf", "-m", "mb_v1.3", "-r", "csv"])
    captured = capsys.readouterr()
    print("\noutput captured\n", captured.out)
    assert ",opened,In Progress,Code Review,closed" in captured.out
    assert "2021-03-07,0.0,1.0,0.0,0.0" in captured.out


@pytest.mark.usefixtures("get_issues")
@pytest.mark.usefixtures("get_workflow_labels")
def test_main_cumulative_flow_writes_csv(filepath_csv, monkeypatch, patch_datetime_now):
    """Test that the main function runs without error."""
    str_filepath = str(filepath_csv.resolve())
    monkeypatch.setitem(m.config, "TOKEN", "x")
    m.main(["cf", "-m", "mb_v1.3", "-r", "csv", "-o", str_filepath])
    content = read_filepath(filepath_csv)
    assert ",opened,In Progress,Code Review,closed" in content
    assert "2021-03-07,0.0,1.0,0.0,0.0" in content


@pytest.mark.usefixtures("get_issues")
@pytest.mark.usefixtures("get_workflow_labels")
def test_main_cumulative_flow_exports_png(monkeypatch, filepath_png):
    """Test that the main function runs without error."""
    str_filepath = str(filepath_png.resolve())
    print(f"export to {str_filepath}")
    monkeypatch.setitem(m.config, "TOKEN", "x")
    m.main(["cf", "-m", "mb_v1.3", "-r", "plot", "-o", str_filepath])
    assert filepath_png.exists()


@pytest.mark.usefixtures("get_issues")
@pytest.mark.usefixtures("get_workflow_labels")
@pytest.mark.usefixtures("patch_datetime_now")
def test_main_cumulative_flow_exports_default_png(monkeypatch, tmp_path, fake_timestamp):
    """Test that the main function runs without error."""
    with change_directory(tmp_path):
        monkeypatch.setitem(m.config, "TOKEN", "x")
        m.main(["cf", "-m", "mb_v1.3", "-r", "plot"])

    timestamp_str = fake_timestamp.strftime("%Y%m%d_%H%M%S")
    assert tmp_path.joinpath(f"cfd_{timestamp_str}.png").exists()


def test_cycletime_requires_user_token(monkeypatch):
    monkeypatch.delitem(m.config, "TOKEN")

    with pytest.raises(KeyError):
        m.main(["cycletime", "-m", "mb_v1.3"])


def test_cycletime_must_find_base_url(monkeypatch):
    monkeypatch.delitem(m.config, "GITLAB_BASE_URL", raising=True)

    with pytest.raises(KeyError):
        m.main(["cy", "-m", "mb_v1.3"])


@pytest.mark.usefixtures("get_closed_issues")
@pytest.mark.usefixtures("get_closed_workflow_labels")
@pytest.mark.usefixtures("get_closed_by_empty")
def test_cycletime_prints_csv(capsys, monkeypatch, patch_datetime_now):
    """Test that the main function runs without error."""
    monkeypatch.setitem(m.config, "TOKEN", "x")

    capsys.readouterr()
    m.main(["cy", "-m", "mb_v1.3", "-r", "csv"])
    captured = capsys.readouterr()
    print("\noutput captured\n", captured.out)
    assert (
        ",issue,project,type,opened,In Progress,Code Review,closed,last_closed,wip_event,wip,reopened,lead,cycle\n"
        + "0,2,8273019,,2021-03-09,2021-03-12,,2021-03-15,2021-03-15,In Progress,2021-03-12,0,5,2"
    ) in captured.out

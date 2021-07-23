import pytest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import numpy as np
import pandas as pd

from tests import records

from gl_analytics.issues import Issue
from gl_analytics.metrics import CumulativeFlow, IssueStageTransitions, LeadCycleTimes, build_transitions


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
            datetime(2021, 3, 16, 10, tzinfo=timezone.utc),
        ),
        ("done", datetime(2021, 3, 16, 10, tzinfo=timezone.utc), None),
    ]

    issues = [
        Issue(1, 2, created_at),
        Issue(2, 2, created_at),
    ]
    issues[0].history.add_events(wfData)
    issues[1].history.add_events(wfData)

    transitions = build_transitions(issues)

    assert len(transitions) == 2
    print("expected vs actual")
    print(expected0)
    print(transitions[0])
    print("expected vs actual")
    print(expected1)
    print(transitions[1])

    assert all([expected0.equals(transitions[0].data)])
    assert all([expected1.equals(transitions[1].data)])


def test_issue_stage_transitions_should_be_records():
    openedAt = datetime(2021, 3, 14, 12, tzinfo=timezone.utc)
    wfData = [
        (
            "ready",
            datetime(2021, 3, 14, 15, 15, tzinfo=timezone.utc),
            datetime(2021, 3, 15, 10, tzinfo=timezone.utc),
        ),
        (
            "in progress",
            datetime(2021, 3, 15, 10, tzinfo=timezone.utc),
            datetime(2021, 3, 16, 10, tzinfo=timezone.utc),
        ),
        (
            "done",
            datetime(2021, 3, 16, 10, tzinfo=timezone.utc),
            None,
        ),
    ]
    issue = Issue(1, 2, openedAt, issue_type="Bug")
    issue.history.add_events(wfData)

    test_data = [
        {"datetime": openedAt, "project": 2, "id": 1, "type": "Bug", "opened": 1},
        {
            "datetime": datetime(2021, 3, 14, 15, 15, tzinfo=timezone.utc),
            "project": 2,
            "id": 1,
            "type": "Bug",
            "opened": 0,
            "ready": 1,
        },
        {
            "datetime": datetime(2021, 3, 15, 10, tzinfo=timezone.utc),
            "project": 2,
            "id": 1,
            "type": "Bug",
            "ready": 0,
            "in progress": 1,
        },
        {
            "datetime": datetime(2021, 3, 16, 10, tzinfo=timezone.utc),
            "project": 2,
            "id": 1,
            "type": "Bug",
            "in progress": 0,
            "done": 1,
        },
    ]

    expected = pd.DataFrame.from_records(test_data, index=["datetime"])
    print(expected)
    actual = IssueStageTransitions(issue)
    print(actual.data)
    assert expected.equals(actual.data)


def test_issue_transitions_should_end_labels_when_closed():
    openedAt = datetime(2021, 3, 14, 12, tzinfo=timezone.utc)
    closedAt = datetime(2021, 3, 18, tzinfo=timezone.utc)
    wfData = [
        ("todo", openedAt + timedelta(days=1), openedAt + timedelta(days=2)),
        (
            "done",
            openedAt + timedelta(days=2),
            None,
        ),
        ("closed", closedAt, None),
    ]
    issue = Issue(1, 2, openedAt, issue_type="Bug")
    issue.history.add_events(wfData)

    test_data = [
        {"datetime": openedAt, "project": 2, "id": 1, "type": "Bug", "opened": 1},
        {"datetime": openedAt + timedelta(days=1), "project": 2, "id": 1, "type": "Bug", "opened": 0, "todo": 1},
        {"datetime": openedAt + timedelta(days=2), "project": 2, "id": 1, "type": "Bug", "todo": 0, "done": 1},
        {"datetime": closedAt, "project": 2, "id": 1, "type": "Bug", "done": 0, "closed": 1},
    ]

    expected = pd.DataFrame.from_records(test_data, index=["datetime"])
    print(expected)
    actual = IssueStageTransitions(issue)
    print(actual.data)
    assert expected.equals(actual.data)


def test_issue_transitions_should_end_open_when_closed():
    openedAt = datetime(2021, 3, 14, 12, tzinfo=timezone.utc)
    closedAt = datetime(2021, 3, 18, tzinfo=timezone.utc)
    issue = Issue(1, 2, openedAt, issue_type="Bug")
    issue.history.add_events([("closed", closedAt, None)])

    test_data = [
        {"datetime": openedAt, "project": 2, "id": 1, "type": "Bug", "opened": 1},
        {"datetime": closedAt, "project": 2, "id": 1, "type": "Bug", "opened": 0, "closed": 1},
    ]

    expected = pd.DataFrame.from_records(test_data, index=["datetime"])
    actual = IssueStageTransitions(issue)
    assert expected.equals(actual.data)


def test_issue_transitions_should_open_indefinitely():
    openedAt = datetime(2021, 3, 14, 12, tzinfo=timezone.utc)
    issue = Issue(1, 2, openedAt, issue_type="Bug")

    test_data = [
        {"datetime": openedAt, "project": 2, "id": 1, "type": "Bug", "opened": 1},
    ]

    expected = pd.DataFrame.from_records(test_data, index=["datetime"])
    actual = IssueStageTransitions(issue)
    assert expected.equals(actual.data)


def test_issue_transitions_should_provide_str():
    openedAt = datetime(2021, 3, 14, 12, tzinfo=timezone.utc)
    closedAt = datetime(2021, 3, 18, tzinfo=timezone.utc)
    issue = Issue(1, 2, openedAt, issue_type="Bug")
    issue.history.add_events([("closed", closedAt, None)])

    test_data = [
        {"datetime": openedAt, "project": 2, "id": 1, "type": "Bug", "opened": 1},
        {"datetime": closedAt, "project": 2, "id": 1, "type": "Bug", "opened": 0, "closed": 1},
    ]

    expected = pd.DataFrame.from_records(test_data, index=["datetime"])
    actual = IssueStageTransitions(issue)
    assert str(expected) == str(actual)


def test_workflow_requires_date_object_for_start(stages):
    with pytest.raises(ValueError):
        CumulativeFlow([], stages=stages, start_date="2021-03-10T12:00:00.000Z")


def test_workflow_supports_datetime_for_start_date(stages):
    expected = datetime(2021, 3, 10, 12, tzinfo=timezone.utc)
    cf = CumulativeFlow([], stages=stages, start_date=expected, days=1)
    assert cf.included_dates.size == 1
    cf.included_dates.values == [expected]


def test_workflow_supports_datetime_for_end_date(stages):
    expected = datetime(2021, 3, 10, 12, tzinfo=timezone.utc)
    cf = CumulativeFlow([], stages=stages, end_date=expected, days=1)
    assert cf.included_dates.size == 1
    cf.included_dates.values == [expected]


def test_workflow_requires_date_object_for_end(stages):
    with pytest.raises(ValueError):
        CumulativeFlow([], stages=stages, end_date="2021-03-10T12:00:00.000Z")


def test_workflow_enforces_one_day_minimum(stages):
    with pytest.raises(ValueError):
        CumulativeFlow([], stages=stages, days=0)
    with pytest.raises(ValueError):
        CumulativeFlow([], stages=stages, days=-1)


def test_workflow_honors_today_with_days(stages, fake_timestamp, patch_datetime_now):
    # use fake_timestamp and datetime monkeypatch
    cf = CumulativeFlow([], stages=stages, days=5)
    fiveDaysAgo = fake_timestamp - timedelta(days=4)
    assert cf.included_dates.size == 5
    values = cf.included_dates.values
    assert values[0] == pd.to_datetime(fiveDaysAgo).to_datetime64()
    assert values[-1] == pd.to_datetime(fake_timestamp).to_datetime64()


def test_cumulative_flow_should_default_30days(stages):
    cf = CumulativeFlow([], stages=stages, end_date=datetime(2021, 3, 30))
    assert cf.included_dates.size == 30
    values = cf.included_dates.values
    assert values[-1] == np.datetime64(datetime(2021, 3, 30))
    assert values[0] == np.datetime64(datetime(2021, 3, 1))


def test_cumulative_flow_should_generate_date_range(stages):
    cf = CumulativeFlow(
        [],
        stages=stages,
        start_date=datetime(2021, 3, 15),
        end_date=datetime(2021, 3, 19),
    )
    assert cf.included_dates[0] == datetime(2021, 3, 15, tzinfo=timezone.utc)
    assert cf.included_dates[-1] == datetime(2021, 3, 19, tzinfo=timezone.utc)
    assert cf.included_dates.size == 5


def test_cumulative_flow_counts_forward(stages):
    openedAt = datetime(2021, 3, 14, 12, tzinfo=timezone.utc)

    test_data = [
        {"datetime": openedAt, "opened": 1},
        {"datetime": datetime(2021, 3, 15, 0, tzinfo=timezone.utc), "opened": 0, "todo": 1},
        {"datetime": datetime(2021, 3, 16, tzinfo=timezone.utc), "todo": 0, "inprogress": 1},
    ]

    data = pd.DataFrame.from_records(test_data, index=["datetime"])
    tr = SimpleNamespace(data=data)
    cf = CumulativeFlow([tr], stages=stages, start_date=datetime(2021, 3, 15), end_date=datetime(2021, 3, 16))
    df = cf.get_data_frame()
    print(df.to_csv())
    assert all([a == b for a, b in zip(df["todo"].array, [1, 0])])
    assert all([a == b for a, b in zip(df["inprogress"].array, [0, 1])])


def test_cumulative_flow_counts_backwards(stages):
    openedAt = datetime(2021, 3, 14, 12, tzinfo=timezone.utc)

    test_data = [
        {"datetime": openedAt, "opened": 1},
        {"datetime": datetime(2021, 3, 15, 0, tzinfo=timezone.utc), "opened": 0, "review": 1},
        {"datetime": datetime(2021, 3, 16, tzinfo=timezone.utc), "review": 0, "inprogress": 1},
    ]

    data = pd.DataFrame.from_records(test_data, index=["datetime"])
    tr = SimpleNamespace(data=data)

    cf = CumulativeFlow([tr], stages=stages, start_date=datetime(2021, 3, 15), end_date=datetime(2021, 3, 16))

    df = cf.get_data_frame()
    print(df.to_csv())
    assert all([a == b for a, b in zip(df["inprogress"].array, [0, 1])])
    assert all([a == b for a, b in zip(df["review"].array, [1, 0])])


def test_cumulative_flow_additive(stages):
    openedAt = datetime(2021, 3, 14, 12, tzinfo=timezone.utc)

    test_data = [
        {"datetime": openedAt, "opened": 1},
        {"datetime": datetime(2021, 3, 15, 0, tzinfo=timezone.utc), "opened": 0, "todo": 1},
        {"datetime": datetime(2021, 3, 16, tzinfo=timezone.utc), "todo": 0, "inprogress": 1},
    ]

    data = pd.DataFrame.from_records(test_data, index=["datetime"])
    tr = SimpleNamespace(data=data)

    print("\ntransitions", tr)
    cf = CumulativeFlow(
        [tr, tr],
        stages=stages,
        start_date=datetime(2021, 3, 15),
        end_date=datetime(2021, 3, 16),
    )

    df = cf.get_data_frame()
    print(df.to_csv())
    assert all([a == b for a, b in zip(df["todo"].array, [2, 0])])
    assert all([a == b for a, b in zip(df["inprogress"].array, [0, 2])])


def test_cumulative_flow_counts_last_daily(stages):
    """Test that 2 events added on same day == last occuring event of the day."""
    openedAt = datetime(2021, 3, 14, 12, tzinfo=timezone.utc)

    test_data = [
        {"datetime": openedAt, "opened": 1},
        {"datetime": datetime(2021, 3, 15, 3, tzinfo=timezone.utc), "opened": 0, "todo": 1},
        {"datetime": datetime(2021, 3, 15, 4, tzinfo=timezone.utc), "todo": 0, "inprogress": 1},
        {"datetime": datetime(2021, 3, 15, 5, tzinfo=timezone.utc), "inprogress": 0, "review": 1},
    ]

    data = pd.DataFrame.from_records(test_data, index=["datetime"])
    tr = SimpleNamespace(data=data)

    cf = CumulativeFlow(
        [tr],
        stages=stages,
        start_date=datetime(2021, 3, 15),
        end_date=datetime(2021, 3, 16),
    )

    df = cf.get_data_frame()
    print(df.to_csv())
    assert all([a == b for a, b in zip(df["todo"].array, [0, 0])])
    assert all([a == b for a, b in zip(df["inprogress"].array, [0, 0])])
    assert all([a == b for a, b in zip(df["review"].array, [1, 1])])
    assert all([a == b for a, b in zip(df["done"].array, [0, 0])])


def test_cumulative_flow_reports_days_from_today(stages, fake_timestamp, patch_datetime_now):
    """Tests the default behavior calculating backwards by days, including today."""

    # fake_timestamp is the ending date
    test_data = [
        {"datetime": fake_timestamp - timedelta(days=4), "opened": 1},
        {"datetime": fake_timestamp - timedelta(days=3), "opened": 0, "todo": 1},
        {"datetime": fake_timestamp - timedelta(days=2), "todo": 0, "inprogress": 1},
        {"datetime": fake_timestamp - timedelta(days=1), "inprogress": 0, "review": 1},
        {"datetime": fake_timestamp, "review": 0, "done": 1},
    ]

    data = pd.DataFrame.from_records(test_data, index=["datetime"])
    tr = SimpleNamespace(data=data)

    cf = CumulativeFlow(
        [tr],
        stages=stages,
        days=5,
    )

    df = cf.get_data_frame()
    print(df.to_csv())
    assert all([a == b for a, b in zip(df["todo"].array, [0, 1, 0, 0, 0])])
    assert all([a == b for a, b in zip(df["inprogress"].array, [0, 0, 1, 0, 0])])
    assert all([a == b for a, b in zip(df["review"].array, [0, 0, 0, 1, 0])])
    assert all([a == b for a, b in zip(df["done"].array, [0, 0, 0, 0, 1])])


def test_cumulative_flow_first_label_occurs_before_time_window(stages):
    openedAt = datetime(2021, 3, 10, 12, tzinfo=timezone.utc)

    test_data = [
        {"datetime": openedAt, "opened": 1},
        {"datetime": datetime(2021, 3, 10, 3, tzinfo=timezone.utc), "opened": 0, "todo": 1},
        {"datetime": datetime(2021, 3, 17, 4, tzinfo=timezone.utc), "todo": 0, "inprogress": 1},
    ]

    data = pd.DataFrame.from_records(test_data, index=["datetime"])
    tr = SimpleNamespace(data=data)

    cf = CumulativeFlow(
        [tr],
        stages=stages,
        start_date=datetime(2021, 3, 15),
        end_date=datetime(2021, 3, 18),
    )

    df = cf.get_data_frame()
    print(df.to_csv())
    assert all([a == b for a, b in zip(df["todo"].array, [1, 1, 0, 0])])
    assert all([a == b for a, b in zip(df["inprogress"].array, [0, 0, 1, 1])])


def test_cumulative_flow_stage_ends_when_closed(stages):
    openedAt = datetime(2021, 3, 10, 12, tzinfo=timezone.utc)
    closedAt = datetime(2021, 3, 19, 8, tzinfo=timezone.utc)

    test_data = [
        {"datetime": openedAt, "opened": 1},
        {"datetime": datetime(2021, 3, 18, 9, tzinfo=timezone.utc), "opened": 0, "done": 1},
        {"datetime": closedAt, "done": 0, "closed": 1},
    ]

    data = pd.DataFrame.from_records(test_data, index=["datetime"])
    tr = SimpleNamespace(data=data)

    cf = CumulativeFlow(
        [tr],
        stages=stages,
        start_date=datetime(2021, 3, 15),
        end_date=datetime(2021, 3, 20),
    )
    df = cf.get_data_frame()
    print(df.to_csv())
    assert all([a == b for a, b in zip(df["done"].array, [0, 0, 0, 1, 0])])


def test_cumulative_flow_reports_open_closed(stages):
    openedAt = datetime(2021, 3, 10, 12, tzinfo=timezone.utc)
    closedAt = datetime(2021, 3, 18, 8, tzinfo=timezone.utc)

    test_data = [
        {"datetime": openedAt, "opened": 1},
        {"datetime": closedAt, "opened": 0, "closed": 1},
    ]

    data = pd.DataFrame.from_records(test_data, index=["datetime"])
    tr = SimpleNamespace(data=data)

    series1 = ["opened"] + stages + ["closed"]
    cf = CumulativeFlow(
        [tr],
        stages=series1,
        start_date=datetime(2021, 3, 15),
        end_date=datetime(2021, 3, 19),
    )
    df = cf.get_data_frame()
    print(df.to_csv())

    assert all([a == b for a, b in zip(df["opened"].array, [1, 1, 1, 0, 0])])
    assert all([a == b for a, b in zip(df["closed"].array, [0, 0, 0, 1, 1])])


def test_cumulative_flow_created_to_closed_same_day(stages):
    openedAt = datetime(2021, 3, 16, 3, tzinfo=timezone.utc)
    closedAt = datetime(2021, 3, 16, 22, tzinfo=timezone.utc)

    test_data = [
        {"datetime": openedAt, "opened": 1},
        {"datetime": openedAt + timedelta(hours=1), "opened": 0, "todo": 1},
        {"datetime": openedAt + timedelta(hours=3), "todo": 0, "inprogress": 1},
        {"datetime": openedAt + timedelta(hours=5), "inprogress": 0, "review": 1},
        {"datetime": closedAt, "review": 0, "closed": 1},
    ]

    data = pd.DataFrame.from_records(test_data, index=["datetime"])
    tr = SimpleNamespace(data=data)

    series1 = ["opened"] + stages + ["closed"]
    cf = CumulativeFlow(
        [tr],
        stages=series1,
        start_date=datetime(2021, 3, 15),
        end_date=datetime(2021, 3, 19),
    )

    df = cf.get_data_frame()
    print(df.to_csv())

    assert all([a == b for a, b in zip(df["opened"].array, [0, 0, 0, 0, 0])])
    assert all([a == b for a, b in zip(df["todo"].array, [0, 0, 0, 0, 0])])
    assert all([a == b for a, b in zip(df["inprogress"].array, [0, 0, 0, 0, 0])])
    assert all([a == b for a, b in zip(df["review"].array, [0, 0, 0, 0, 0])])
    assert all([a == b for a, b in zip(df["done"].array, [0, 0, 0, 0, 0])])
    assert all([a == b for a, b in zip(df["closed"].array, [0, 1, 1, 1, 1])])


def test_cumulative_flow_filtered_labels_do_not_affect_count_of_columns():
    openedAt = datetime(2021, 3, 15, 3, tzinfo=timezone.utc)
    closedAt = datetime(2021, 3, 19, 22, tzinfo=timezone.utc)

    test_data = [
        {"datetime": openedAt, "opened": 1},
        {"datetime": openedAt + timedelta(days=1), "opened": 0, "todo": 1},
        {"datetime": openedAt + timedelta(days=1, hours=8), "todo": 0, "inprogress": 1},
        {"datetime": openedAt + timedelta(days=2), "inprogress": 0, "review": 1},
        {"datetime": openedAt + timedelta(days=3), "review": 0, "done": 1},
        {"datetime": closedAt, "done": 0, "closed": 1},
    ]

    data = pd.DataFrame.from_records(test_data, index=["datetime"])
    tr = SimpleNamespace(data=data)

    series1 = ["opened", "inprogress", "done", "closed"]

    cf = CumulativeFlow(
        [tr],
        stages=series1,
        start_date=datetime(2021, 3, 15),
        end_date=datetime(2021, 3, 19),
    )
    df = cf.get_data_frame()
    print(df.to_csv())

    # we did not request todo or review items from the list of available transition labels
    with pytest.raises(KeyError):
        df["todo"].array  # todo occurs on 1st date, making opened count zero but todo is not shown
    with pytest.raises(KeyError):
        df["review"].array  # review occurs on 3rd date, making inprogress count zero but review is not shown

    assert all([a == b for a, b in zip(df["opened"].array, [1, 0, 0, 0, 0])])
    assert all([a == b for a, b in zip(df["inprogress"].array, [0, 1, 0, 0, 0])])
    assert all([a == b for a, b in zip(df["done"].array, [0, 0, 0, 1, 0])])
    assert all([a == b for a, b in zip(df["closed"].array, [0, 0, 0, 0, 1])])


def test_cumulative_flow_accounts_for_filtered_stages():
    openedAt = datetime(2021, 3, 15, 3, tzinfo=timezone.utc)
    closedAt = datetime(2021, 3, 19, 22, tzinfo=timezone.utc)

    test_data = [
        {"datetime": openedAt, "opened": 1},
        {"datetime": openedAt + timedelta(days=1), "opened": 0, "todo": 1},
        {"datetime": openedAt + timedelta(days=2), "todo": 0, "inprogress": 1},
        {"datetime": openedAt + timedelta(days=3), "inprogress": 0, "review": 1},
        {"datetime": closedAt, "review": 0, "closed": 1},
    ]

    data = pd.DataFrame.from_records(test_data, index=["datetime"])
    tr = SimpleNamespace(data=data)

    # create new series without todo or review columns
    series1 = ["opened", "inprogress", "done", "closed"]

    cf = CumulativeFlow(
        [tr],
        stages=series1,
        start_date=datetime(2021, 3, 15),
        end_date=datetime(2021, 3, 19),
    )
    df = cf.get_data_frame()
    print(df.to_csv())

    # we did not request todo or review items from the list of available transition labels
    with pytest.raises(KeyError):
        df["todo"].array
    with pytest.raises(KeyError):
        df["review"].array

    assert all([a == b for a, b in zip(df["opened"].array, [1, 0, 0, 0, 0])])
    assert all([a == b for a, b in zip(df["inprogress"].array, [0, 0, 1, 0, 0])])
    assert all([a == b for a, b in zip(df["done"].array, [0, 0, 0, 0, 0])])
    assert all([a == b for a, b in zip(df["closed"].array, [0, 0, 0, 0, 1])])


def test_cumulative_flow_offsets_for_closed_stages():
    """Closed on same day as last stage "done", but Closed is not included."""
    openedAt = datetime(2021, 3, 16, 8, tzinfo=timezone.utc)
    closedAt = datetime(2021, 3, 16, 17, tzinfo=timezone.utc)

    test_data = [
        {"datetime": openedAt, "opened": 1},
        {"datetime": openedAt + timedelta(hours=1), "opened": 0, "todo": 1},
        {"datetime": openedAt + timedelta(hours=2), "todo": 0, "inprogress": 1},
        {"datetime": openedAt + timedelta(hours=3), "inprogress": 0, "review": 1},
        {"datetime": openedAt + timedelta(hours=4), "review": 0, "done": 1},
        {"datetime": closedAt, "done": 0, "closed": 1},
    ]

    data = pd.DataFrame.from_records(test_data, index=["datetime"])
    tr = SimpleNamespace(data=data)

    cf = CumulativeFlow(
        [tr],
        # workflow_stages=["open", "todo", "inprogress", "review", "done", "closed"],
        stages=["done"],
        start_date=datetime(2021, 3, 15),
        end_date=datetime(2021, 3, 19),
    )

    df = cf.get_data_frame()
    print(df.to_csv())

    assert all([a == b for a, b in zip(df["done"].array, [0, 1, 0, 0, 0])])


def test_cumulative_flow_offsets_for_filtered_stages():
    """Same day as last stage "review", but "review" is not included.

    Report will offset the "inprogress" date.
    """
    openedAt = datetime(2021, 3, 16, 8, tzinfo=timezone.utc)

    test_data = [
        {"datetime": openedAt, "opened": 1},
        {"datetime": openedAt + timedelta(hours=1), "opened": 0, "todo": 1},
        {"datetime": openedAt + timedelta(hours=2), "todo": 0, "inprogress": 1},
        {"datetime": openedAt + timedelta(hours=3), "inprogress": 0, "review": 1},
    ]

    data = pd.DataFrame.from_records(test_data, index=["datetime"])
    tr = SimpleNamespace(data=data)

    cf = CumulativeFlow(
        [tr],
        stages=["inprogress"],
        start_date=datetime(2021, 3, 15),
        end_date=datetime(2021, 3, 19),
    )

    df = cf.get_data_frame()
    print(df.to_csv())

    assert all([a == b for a, b in zip(df["inprogress"].array, [0, 1, 0, 0, 0])])


def test_cumulative_flow_opened_ends_at_next_filtered_stage():
    """A report should always show the opened items.

    When an item is open and has a scoped label excluded from the workflow, the report should
    include the item in the opened column.
    """
    openedAt = datetime(2021, 3, 10, 8, tzinfo=timezone.utc)
    closedAt = datetime(2021, 3, 19, 0, tzinfo=timezone.utc)

    test_data = [
        {"datetime": openedAt, "opened": 1},
        {"datetime": datetime(2021, 3, 17, 7, tzinfo=timezone.utc), "opened": 0, "todo": 1},
        {"datetime": datetime(2021, 3, 18, 15, tzinfo=timezone.utc), "todo": 0, "inprogress": 1},
        {"datetime": closedAt, "inprogress": 0, "closed": 1},
    ]

    data = pd.DataFrame.from_records(test_data, index=["datetime"])
    tr = SimpleNamespace(data=data)

    cf = CumulativeFlow(
        [tr],
        stages=["opened", "inprogress"],
        start_date=datetime(2021, 3, 15),
        end_date=datetime(2021, 3, 19),
    )

    df = cf.get_data_frame()
    print(df.to_csv())

    assert all([a == b for a, b in zip(df["opened"].array, [1, 1, 0, 0, 0])])
    assert all([a == b for a, b in zip(df["inprogress"].array, [0, 0, 0, 1, 0])])


def test_cumulative_flow_label_removed_but_not_closed(stages):
    """When an issue has workflow label removed but issue is not closed, the report should show the last day
    the item was in the workflow state.

    """

    openedAt = datetime(2021, 3, 15, 8, tzinfo=timezone.utc)

    test_data = [
        {"datetime": openedAt, "opened": 1},
        {"datetime": openedAt + timedelta(days=1), "opened": 0, "todo": 1},
        {"datetime": openedAt + timedelta(days=2), "todo": 0},
    ]

    data = pd.DataFrame.from_records(test_data, index=["datetime"])
    tr = SimpleNamespace(data=data)

    series = ["opened"] + stages + ["closed"]
    cf = CumulativeFlow(
        [tr],
        stages=series,
        start_date=datetime(2021, 3, 15),
        end_date=datetime(2021, 3, 19),
    )
    df = cf.get_data_frame()
    print(df.to_csv())

    assert all([a == b for a, b in zip(df["opened"].array, [1, 0, 0, 0, 0])])
    assert all([a == b for a, b in zip(df["todo"].array, [0, 1, 0, 0, 0])])


def test_cumulative_flow_shows_hanging_open(stages):
    """Given an issue opened within the reporting window but never included in workflow."""
    openedAt = datetime(2021, 3, 15, 8, tzinfo=timezone.utc)
    test_data = [
        {"datetime": openedAt, "opened": 1},
    ]

    data = pd.DataFrame.from_records(test_data, index=["datetime"])
    tr = SimpleNamespace(data=data)
    series = ["opened"] + stages + ["closed"]

    cf = CumulativeFlow(
        [tr],
        stages=series,
        start_date=datetime(2021, 3, 17),
        end_date=datetime(2021, 3, 19),
    )
    df = cf.get_data_frame()
    print(df.to_csv())

    assert all([a == b for a, b in zip(df["opened"].array, [1, 1, 1])])


def test_leadcycletimes_should_be_additive(stages):
    """Lead and cycle times count days between opened, in progress, and closed."""

    obj = LeadCycleTimes([get_item_over_week(), get_item_over_weekend()], stage="inprogress")
    df = obj.get_data_frame()
    print(df.to_csv())
    assert all([a == b for a, b in zip(df["lead"].array, [5, 4])])
    assert all([a == b for a, b in zip(df["cycle"].array, [3, 2])])


def get_item_over_week():
    openedAt = datetime(2021, 3, 15, 6, tzinfo=timezone.utc)
    inProgressAt = openedAt + timedelta(days=2)
    closedAt = datetime(2021, 3, 19, 21, tzinfo=timezone.utc)

    issue = Issue(1, 2, openedAt, issue_type="Bug")
    history = [
        ("todo", openedAt + timedelta(days=1), inProgressAt),
        ("inprogress", inProgressAt, openedAt + timedelta(days=3)),
        ("review", openedAt + timedelta(days=3), None),
        ("closed", closedAt, None),
    ]
    issue.history.add_events(history)
    return issue


def get_item_over_weekend():
    """Lead and cycle times count days between opened, in progress, and closed."""
    openedAt = datetime(2021, 3, 18, 6, tzinfo=timezone.utc)  # Thursday
    inProgressAt = openedAt + timedelta(days=2)
    closedAt = datetime(2021, 3, 23, 21, tzinfo=timezone.utc)  # Tuesday

    issue = Issue(2, 2, openedAt, issue_type="Bug")
    history = [
        ("todo", openedAt + timedelta(days=1), inProgressAt),
        ("inprogress", inProgressAt, openedAt + timedelta(days=3)),
        ("review", openedAt + timedelta(days=3), None),
        ("closed", closedAt, None),
    ]
    issue.history.add_events(history)
    return issue


def test_leadcycletime_should_use_opened_when_stage_unavailable():
    obj = LeadCycleTimes([get_item_without_stage()], stage="inprogress")
    df = obj.get_data_frame()
    print(df.to_csv())
    assert all([a == b for a, b in zip(df["lead"].array, [5])])
    assert all([a == b for a, b in zip(df["cycle"].array, [5])])


def get_item_without_stage():
    openedAt = datetime(2021, 3, 15, 6, tzinfo=timezone.utc)
    inProgressAt = openedAt + timedelta(days=2)
    closedAt = datetime(2021, 3, 19, 21, tzinfo=timezone.utc)

    issue = Issue(1, 2, openedAt, issue_type="Bug")
    history = [
        ("todo", openedAt + timedelta(days=1), inProgressAt),
        ("review", openedAt + timedelta(days=3), None),
        ("closed", closedAt, None),
    ]
    issue.history.add_events(history)
    return issue


def test_leadcycletime_should_calculate_reopened_leadtimes():
    obj = LeadCycleTimes([get_item_reopened_twice()], stage="inprogress")
    df = obj.get_data_frame()
    print(df.to_csv())
    assert all([a == b for a, b in zip(df["lead"].array, [6])])
    assert all([a == b for a, b in zip(df["cycle"].array, [3])])


def test_leadcycletime_should_calculate_reopened_counts():
    obj = LeadCycleTimes([get_item_reopened_twice()], stage="inprogress")
    df = obj.get_data_frame()
    print(df.to_csv())
    assert all([a == b for a, b in zip(df["lead"].array, [6])])
    assert all([a == b for a, b in zip(df["cycle"].array, [3])])


def get_item_reopened_twice():
    openedAt = datetime(2021, 3, 15, 6, tzinfo=timezone.utc)
    inProgressAt = openedAt + timedelta(days=2)
    closedAt = datetime(2021, 3, 19, 21, tzinfo=timezone.utc)
    # last closed extends over a weekend, adding 1 bus day
    lastClosedAt = datetime(2021, 3, 22, tzinfo=timezone.utc)

    issue = Issue(1, 2, openedAt, issue_type="Bug")
    history = [
        ("todo", openedAt + timedelta(days=1), inProgressAt),
        ("inprogress", inProgressAt, openedAt + timedelta(days=3)),
        ("review", openedAt + timedelta(days=3), None),
        ("closed", closedAt, None),
        ("reopened", closedAt + timedelta(hours=3), None),
        ("closed", closedAt + timedelta(hours=6), None),
        ("reopened", closedAt + timedelta(hours=9), None),
        ("closed", lastClosedAt, None),
    ]
    issue.history.add_events(history)
    return issue


def test_leadcycletime_should_honor_first_closed():
    obj = LeadCycleTimes([get_item_closed_without_work()], stage="inprogress")
    df = obj.get_data_frame()
    print(df.to_csv())
    assert all([a == b for a, b in zip(df["lead"].array, [6])])
    assert all([a == b for a, b in zip(df["cycle"].array, [5])])


def get_item_closed_without_work():
    openedAt = datetime(2021, 3, 15, 6, tzinfo=timezone.utc)
    closedAt = datetime(2021, 3, 19, 21, tzinfo=timezone.utc)
    # last closed extends over a weekend, adding 1 bus day
    lastClosedAt = datetime(2021, 3, 22, tzinfo=timezone.utc)

    issue = Issue(1, 2, openedAt, issue_type="Bug")
    history = [
        ("closed", closedAt, None),
        ("reopened", closedAt + timedelta(hours=3), None),
        ("inprogress", closedAt + timedelta(hours=6), None),
        ("closed", lastClosedAt, None),
    ]
    issue.history.add_events(history)
    return issue

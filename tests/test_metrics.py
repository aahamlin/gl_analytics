import pytest
import datetime

import numpy as np
import pandas as pd

from types import SimpleNamespace

from gl_analytics.metrics import (
    CumulativeFlow,
    IssueStageTransitions,
)


# XXX replace this with another function from pandas
def daterange(start_date, end_date):
    """Generate dates from start to end, exclusive.

    Given start=3-15, end=3-20, generator will generate dates from 3-15..3-19.
    """
    for n in range(int((end_date - start_date).days)):
        yield start_date + datetime.timedelta(n)


def test_daterange_exclusive():
    """Make sure the daterange generator works until we replace it.
    """
    d1 = datetime.date(2021, 3, 15)
    d2 = datetime.date(2021, 3, 20)
    dates = [d for d in daterange(d1, d2)]
    assert dates[-1] == datetime.date(2021, 3, 19)


def test_issue_stage_transitions_should_be_records():

    wfData = [
        (
            "ready",
            datetime.datetime(2021, 3, 14, 15, 15, tzinfo=datetime.timezone.utc),
            datetime.datetime(2021, 3, 15, 10, tzinfo=datetime.timezone.utc),
        ),
        (
            "in progress",
            datetime.datetime(2021, 3, 15, 10, tzinfo=datetime.timezone.utc),
            datetime.datetime(2021, 3, 16, 10, tzinfo=datetime.timezone.utc),
        ),
        (
            "done",
            datetime.datetime(2021, 3, 16, 10, tzinfo=datetime.timezone.utc),
            None,
        ),
    ]

    openedAt = datetime.datetime(2021, 3, 14, 12, tzinfo=datetime.timezone.utc)

    expected_data = [
        {"datetime": openedAt, "opened": 1},
        {"datetime": datetime.datetime(2021, 3, 14, 15, 15, tzinfo=datetime.timezone.utc), "opened": 0, "ready": 1},
        {"datetime": datetime.datetime(2021, 3, 15, 10, tzinfo=datetime.timezone.utc), "ready": 0, "in progress": 1},
        {"datetime": datetime.datetime(2021, 3, 16, 10, tzinfo=datetime.timezone.utc), "in progress": 0, "done": 1},
    ]

    expected = pd.DataFrame.from_records(expected_data, index=["datetime"])
    print(expected)
    actual = IssueStageTransitions(openedAt, None, label_events=wfData)
    print(actual.data)
    assert expected.equals(actual.data)


def test_issue_transitions_ends_last_stage_when_closed():

    wfData = [
        (
            "done",
            datetime.datetime(2021, 3, 16, 10, tzinfo=datetime.timezone.utc),
            None,
        ),
    ]

    openedAt = datetime.datetime(2021, 3, 14, 12, tzinfo=datetime.timezone.utc)
    closedAt = datetime.datetime(2021, 3, 18, tzinfo=datetime.timezone.utc)

    expected_data = [
        {"datetime": openedAt, "opened": 1},
        {"datetime": datetime.datetime(2021, 3, 16, 10, tzinfo=datetime.timezone.utc), "opened": 0, "done": 1},
        {"datetime": datetime.datetime(2021, 3, 18, tzinfo=datetime.timezone.utc), "done": 0, "closed": 1},
    ]

    expected = pd.DataFrame.from_records(expected_data, index=["datetime"])

    actual = IssueStageTransitions(openedAt, closed=closedAt, label_events=wfData)
    assert expected.equals(actual.data)


def test_workflow_requires_date_object_for_start(stages):
    with pytest.raises(ValueError):
        CumulativeFlow([], stages=stages, start_date="2021-03-10T12:00:00.000Z")


def test_workflow_supports_datetime_for_start_date(stages):
    expected = datetime.datetime(2021, 3, 10, 12, tzinfo=datetime.timezone.utc)
    cf = CumulativeFlow([], stages=stages, start_date=expected, days=1)
    assert cf.included_dates.size == 1
    cf.included_dates.values == [expected]


def test_workflow_supports_datetime_for_end_date(stages):
    expected = datetime.datetime(2021, 3, 10, 12, tzinfo=datetime.timezone.utc)
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
    fiveDaysAgo = fake_timestamp - datetime.timedelta(days=4)
    assert cf.included_dates.size == 5
    values = cf.included_dates.values
    assert values[0] == pd.to_datetime(fiveDaysAgo).to_datetime64()
    assert values[-1] == pd.to_datetime(fake_timestamp).to_datetime64()


def test_workflow_honors_end_date_default_days(stages):
    # default 30 days
    cf = CumulativeFlow([], stages=stages, end_date=datetime.date(2021, 3, 30))
    assert cf.included_dates.size == 30
    values = cf.included_dates.values
    assert values[-1] == np.datetime64(datetime.date(2021, 3, 30))
    assert values[0] == np.datetime64(datetime.date(2021, 3, 1))


def test_workflow_honors_start_date(stages):
    report_daterange = [d for d in daterange(datetime.datetime(2021, 3, 15), datetime.datetime(2021, 3, 19))]
    cf = CumulativeFlow(
        [],
        stages=stages,
        start_date=report_daterange[0],
        end_date=report_daterange[-1],
    )
    assert cf.included_dates[0] == report_daterange[0].date()


def test_workflow_honors_end_date(stages):
    report_daterange = [d for d in daterange(datetime.datetime(2021, 3, 15), datetime.datetime(2021, 3, 19))]
    cf = CumulativeFlow(
        [],
        stages=stages,
        start_date=report_daterange[0],
        end_date=report_daterange[-1],
    )
    assert cf.included_dates[-1] == report_daterange[-1].date()


def test_cumulative_flow_counts_forward(stages):
    openedAt = datetime.datetime(2021, 3, 14, 12, tzinfo=datetime.timezone.utc)

    expected_data = [
        {"datetime": openedAt, "opened": 1},
        {"datetime": datetime.datetime(2021, 3, 15, 0, tzinfo=datetime.timezone.utc), "opened": 0, "todo": 1},
        {"datetime": datetime.datetime(2021, 3, 16, tzinfo=datetime.timezone.utc), "todo": 0, "inprogress": 1},
    ]

    data = pd.DataFrame.from_records(expected_data, index=["datetime"])
    tr = SimpleNamespace(data=data)
    cf = CumulativeFlow(
        [tr],
        stages=stages,
        start_date=datetime.datetime(2021, 3, 15),
        end_date=datetime.datetime(2021, 3, 16)
    )
    df = cf.get_data_frame()
    print(df.to_csv())
    assert all([a == b for a, b in zip(df["todo"].array, [1, 0])])
    assert all([a == b for a, b in zip(df["inprogress"].array, [0, 1])])


def test_cumulative_flow_counts_backwards(stages):
    openedAt = datetime.datetime(2021, 3, 14, 12, tzinfo=datetime.timezone.utc)

    expected_data = [
        {"datetime": openedAt, "opened": 1},
        {"datetime": datetime.datetime(2021, 3, 15, 0, tzinfo=datetime.timezone.utc), "opened": 0, "review": 1},
        {"datetime": datetime.datetime(2021, 3, 16, tzinfo=datetime.timezone.utc), "review": 0, "inprogress": 1},
    ]

    data = pd.DataFrame.from_records(expected_data, index=["datetime"])
    tr = SimpleNamespace(data=data)

    cf = CumulativeFlow(
        [tr],
        stages=stages,
        start_date=datetime.datetime(2021, 3, 15),
        end_date=datetime.datetime(2021, 3, 16)
    )

    df = cf.get_data_frame()
    print(df.to_csv())
    assert all([a == b for a, b in zip(df["inprogress"].array, [0, 1])])
    assert all([a == b for a, b in zip(df["review"].array, [1, 0])])


def test_cumulative_flow_additive(stages):
    openedAt = datetime.datetime(2021, 3, 14, 12, tzinfo=datetime.timezone.utc)

    expected_data = [
        {"datetime": openedAt, "opened": 1},
        {"datetime": datetime.datetime(2021, 3, 15, 0, tzinfo=datetime.timezone.utc), "opened": 0, "todo": 1},
        {"datetime": datetime.datetime(2021, 3, 16, tzinfo=datetime.timezone.utc), "todo": 0, "inprogress": 1},
    ]

    data = pd.DataFrame.from_records(expected_data, index=["datetime"])
    tr = SimpleNamespace(data=data)

    print("\ntransitions", tr)
    cf = CumulativeFlow(
        [tr, tr],
        stages=stages,
        start_date=datetime.datetime(2021, 3, 15),
        end_date=datetime.datetime(2021, 3, 16),
    )

    df = cf.get_data_frame()
    print(df.to_csv())
    assert all([a == b for a, b in zip(df["todo"].array, [2, 0])])
    assert all([a == b for a, b in zip(df["inprogress"].array, [0, 2])])


def test_cumulative_flow_counts_last_daily(stages):
    """Test that 2 events added on same day == last occuring event of the day.
    """
    openedAt = datetime.datetime(2021, 3, 14, 12, tzinfo=datetime.timezone.utc)

    expected_data = [
        {"datetime": openedAt, "opened": 1},
        {"datetime": datetime.datetime(2021, 3, 15, 3, tzinfo=datetime.timezone.utc), "opened": 0, "todo": 1},
        {"datetime": datetime.datetime(2021, 3, 15, 4, tzinfo=datetime.timezone.utc), "todo": 0, "inprogress": 1},
        {"datetime": datetime.datetime(2021, 3, 15, 5, tzinfo=datetime.timezone.utc), "inprogress": 0, "review": 1},
    ]

    data = pd.DataFrame.from_records(expected_data, index=["datetime"])
    tr = SimpleNamespace(data=data)

    cf = CumulativeFlow(
        [tr],
        stages=stages,
        start_date=datetime.datetime(2021, 3, 15),
        end_date=datetime.datetime(2021, 3, 16),
    )

    df = cf.get_data_frame()
    print(df.to_csv())
    assert all([a == b for a, b in zip(df["todo"].array, [0, 0])])
    assert all([a == b for a, b in zip(df["inprogress"].array, [0, 0])])
    assert all([a == b for a, b in zip(df["review"].array, [1, 1])])
    assert all([a == b for a, b in zip(df["done"].array, [0, 0])])


def test_cumulative_flow_reports_days_from_today(stages, fake_timestamp, patch_datetime_now):
    """Tests the default behavior calculating backwards by days, including today.
    """

    # fake_timestamp is the ending date
    expected_data = [
        {"datetime": fake_timestamp - datetime.timedelta(days=4), "opened": 1},
        {"datetime": fake_timestamp - datetime.timedelta(days=3), "opened": 0, "todo": 1},
        {"datetime": fake_timestamp - datetime.timedelta(days=2), "todo": 0, "inprogress": 1},
        {"datetime": fake_timestamp - datetime.timedelta(days=1), "inprogress": 0, "review": 1},
        {"datetime": fake_timestamp, "review": 0, "done": 1},
    ]

    data = pd.DataFrame.from_records(expected_data, index=["datetime"])
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
    openedAt = datetime.datetime(2021, 3, 10, 12, tzinfo=datetime.timezone.utc)

    expected_data = [
        {"datetime": openedAt, "opened": 1},
        {"datetime": datetime.datetime(2021, 3, 10, 3, tzinfo=datetime.timezone.utc), "opened": 0, "todo": 1},
        {"datetime": datetime.datetime(2021, 3, 17, 4, tzinfo=datetime.timezone.utc), "todo": 0, "inprogress": 1},
    ]

    data = pd.DataFrame.from_records(expected_data, index=["datetime"])
    tr = SimpleNamespace(data=data)

    cf = CumulativeFlow(
        [tr],
        stages=stages,
        start_date=datetime.datetime(2021, 3, 15),
        end_date=datetime.datetime(2021, 3, 18),
    )

    df = cf.get_data_frame()
    print(df.to_csv())
    assert all([a == b for a, b in zip(df["todo"].array, [1, 1, 0, 0])])
    assert all([a == b for a, b in zip(df["inprogress"].array, [0, 0, 1, 1])])


def test_cumulative_flow_stage_ends_when_closed(stages):
    openedAt = datetime.datetime(2021, 3, 10, 12, tzinfo=datetime.timezone.utc)
    closedAt = datetime.datetime(2021, 3, 19, 8, tzinfo=datetime.timezone.utc)

    expected_data = [
        {"datetime": openedAt, "opened": 1},
        {"datetime": datetime.datetime(2021, 3, 18, 9, tzinfo=datetime.timezone.utc), "opened": 0, "done": 1},
        {"datetime": closedAt, "done": 0, "closed": 1},
    ]

    data = pd.DataFrame.from_records(expected_data, index=["datetime"])
    tr = SimpleNamespace(data=data)

    cf = CumulativeFlow(
        [tr],
        stages=stages,
        start_date=datetime.datetime(2021, 3, 15),
        end_date=datetime.datetime(2021, 3, 20),
    )
    df = cf.get_data_frame()
    print(df.to_csv())
    assert all([a == b for a, b in zip(df["done"].array, [0, 0, 0, 1, 0])])


def test_cumulative_flow_reports_open_closed(stages):
    openedAt = datetime.datetime(2021, 3, 10, 12, tzinfo=datetime.timezone.utc)
    closedAt = datetime.datetime(2021, 3, 18, 8, tzinfo=datetime.timezone.utc)

    expected_data = [
        {"datetime": openedAt, "opened": 1},
        {"datetime": closedAt, "opened": 0, "closed": 1},
    ]

    data = pd.DataFrame.from_records(expected_data, index=["datetime"])
    tr = SimpleNamespace(data=data)

    series1 = ["opened"] + stages + ["closed"]
    cf = CumulativeFlow(
        [tr],
        stages=series1,
        start_date=datetime.datetime(2021, 3, 15),
        end_date=datetime.datetime(2021, 3, 19),
    )
    df = cf.get_data_frame()
    print(df.to_csv())

    assert all([a == b for a, b in zip(df["opened"].array, [1, 1, 1, 0, 0])])
    assert all([a == b for a, b in zip(df["closed"].array, [0, 0, 0, 1, 1])])


def test_cumulative_flow_created_to_closed_same_day(stages):
    openedAt = datetime.datetime(2021, 3, 16, 3, tzinfo=datetime.timezone.utc)
    closedAt = datetime.datetime(2021, 3, 16, 22, tzinfo=datetime.timezone.utc)

    expected_data = [
        {"datetime": openedAt, "opened": 1},
        {"datetime": openedAt + datetime.timedelta(hours=1), "opened": 0, "todo": 1},
        {"datetime": openedAt + datetime.timedelta(hours=3), "todo": 0, "inprogress": 1},
        {"datetime": openedAt + datetime.timedelta(hours=5), "inprogress": 0, "review": 1},
        {"datetime": closedAt, "review": 0, "closed": 1},
    ]

    data = pd.DataFrame.from_records(expected_data, index=["datetime"])
    tr = SimpleNamespace(data=data)

    series1 = ["opened"] + stages + ["closed"]
    cf = CumulativeFlow(
        [tr],
        stages=series1,
        start_date=datetime.datetime(2021, 3, 15),
        end_date=datetime.datetime(2021, 3, 19),
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
    openedAt = datetime.datetime(2021, 3, 15, 3, tzinfo=datetime.timezone.utc)
    closedAt = datetime.datetime(2021, 3, 19, 22, tzinfo=datetime.timezone.utc)

    expected_data = [
        {"datetime": openedAt, "opened": 1},
        {"datetime": openedAt + datetime.timedelta(days=1), "opened": 0, "todo": 1},
        {"datetime": openedAt + datetime.timedelta(days=1, hours=8), "todo": 0, "inprogress": 1},
        {"datetime": openedAt + datetime.timedelta(days=2), "inprogress": 0, "review": 1},
        {"datetime": openedAt + datetime.timedelta(days=3), "review": 0, "done": 1},
        {"datetime": closedAt, "done": 0, "closed": 1},
    ]

    data = pd.DataFrame.from_records(expected_data, index=["datetime"])
    tr = SimpleNamespace(data=data)

    series1 = ["opened", "inprogress", "done", "closed"]

    cf = CumulativeFlow(
        [tr],
        stages=series1,
        start_date=datetime.datetime(2021, 3, 15),
        end_date=datetime.datetime(2021, 3, 19),
    )
    df = cf.get_data_frame()
    print(df.to_csv())

    # we did not request todo or review items from the list of available transition labels
    with pytest.raises(KeyError):
        df[
            "todo"
        ].array  # todo occurs on 1st date, making opened count zero but todo is not shown
    with pytest.raises(KeyError):
        df[
            "review"
        ].array  # review occurs on 3rd date, making inprogress count zero but review is not shown

    assert all([a == b for a, b in zip(df["opened"].array, [1, 0, 0, 0, 0])])
    assert all([a == b for a, b in zip(df["inprogress"].array, [0, 1, 0, 0, 0])])
    assert all([a == b for a, b in zip(df["done"].array, [0, 0, 0, 1, 0])])
    assert all([a == b for a, b in zip(df["closed"].array, [0, 0, 0, 0, 1])])


def test_cumulative_flow_accounts_for_filtered_stages():
    openedAt = datetime.datetime(2021, 3, 15, 3, tzinfo=datetime.timezone.utc)
    closedAt = datetime.datetime(2021, 3, 19, 22, tzinfo=datetime.timezone.utc)

    expected_data = [
        {"datetime": openedAt, "opened": 1},
        {"datetime": openedAt + datetime.timedelta(days=1), "opened": 0, "todo": 1},
        {"datetime": openedAt + datetime.timedelta(days=2), "todo": 0, "inprogress": 1},
        {"datetime": openedAt + datetime.timedelta(days=3), "inprogress": 0, "review": 1},
        {"datetime": closedAt, "review": 0, "closed": 1},
    ]

    data = pd.DataFrame.from_records(expected_data, index=["datetime"])
    tr = SimpleNamespace(data=data)

    # create new series without todo or review columns
    series1 = ["opened", "inprogress", "done", "closed"]

    cf = CumulativeFlow(
        [tr],
        stages=series1,
        start_date=datetime.datetime(2021, 3, 15),
        end_date=datetime.datetime(2021, 3, 19),
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
    openedAt = datetime.datetime(2021, 3, 16, 8, tzinfo=datetime.timezone.utc)
    closedAt = datetime.datetime(2021, 3, 16, 17, tzinfo=datetime.timezone.utc)

    expected_data = [
        {"datetime": openedAt, "opened": 1},
        {"datetime": openedAt + datetime.timedelta(hours=1), "opened": 0, "todo": 1},
        {"datetime": openedAt + datetime.timedelta(hours=2), "todo": 0, "inprogress": 1},
        {"datetime": openedAt + datetime.timedelta(hours=3), "inprogress": 0, "review": 1},
        {"datetime": openedAt + datetime.timedelta(hours=4), "review": 0, "done": 1},
        {"datetime": closedAt, "done": 0, "closed": 1},
    ]

    data = pd.DataFrame.from_records(expected_data, index=["datetime"])
    tr = SimpleNamespace(data=data)

    cf = CumulativeFlow(
        [tr],
        # workflow_stages=["open", "todo", "inprogress", "review", "done", "closed"],
        stages=["done"],
        start_date=datetime.datetime(2021, 3, 15),
        end_date=datetime.datetime(2021, 3, 19),
    )

    df = cf.get_data_frame()
    print(df.to_csv())

    assert all([a == b for a, b in zip(df["done"].array, [0, 1, 0, 0, 0])])


def test_cumulative_flow_offsets_for_filtered_stages():
    """Same day as last stage "review", but "review" is not included.

    Report will offset the "inprogress" date.
    """
    openedAt = datetime.datetime(2021, 3, 16, 8, tzinfo=datetime.timezone.utc)

    expected_data = [
        {"datetime": openedAt, "opened": 1},
        {"datetime": openedAt + datetime.timedelta(hours=1), "opened": 0, "todo": 1},
        {"datetime": openedAt + datetime.timedelta(hours=2), "todo": 0, "inprogress": 1},
        {"datetime": openedAt + datetime.timedelta(hours=3), "inprogress": 0, "review": 1},
    ]

    data = pd.DataFrame.from_records(expected_data, index=["datetime"])
    tr = SimpleNamespace(data=data)

    cf = CumulativeFlow(
        [tr],
        stages=["inprogress"],
        start_date=datetime.datetime(2021, 3, 15),
        end_date=datetime.datetime(2021, 3, 19),
    )

    df = cf.get_data_frame()
    print(df.to_csv())

    assert all([a == b for a, b in zip(df["inprogress"].array, [0, 1, 0, 0, 0])])


def test_cumulative_flow_opened_ends_at_next_filtered_stage():
    """A report should always show the opened items.

    When an item is open and has a scoped label excluded from the workflow, the report should
    include the item in the opened column.
    """
    openedAt = datetime.datetime(2021, 3, 10, 8, tzinfo=datetime.timezone.utc)
    closedAt = datetime.datetime(2021, 3, 19, 0, tzinfo=datetime.timezone.utc)

    expected_data = [
        {"datetime": openedAt, "opened": 1},
        {"datetime": datetime.datetime(2021, 3, 17, 7, tzinfo=datetime.timezone.utc), "opened": 0, "todo": 1},
        {"datetime": datetime.datetime(2021, 3, 18, 15, tzinfo=datetime.timezone.utc), "todo": 0, "inprogress": 1},
        {"datetime": closedAt, "inprogress": 0, "closed": 1}
    ]

    data = pd.DataFrame.from_records(expected_data, index=["datetime"])
    tr = SimpleNamespace(data=data)

    cf = CumulativeFlow(
        [tr],
        stages=["opened", "inprogress"],
        start_date=datetime.datetime(2021, 3, 15),
        end_date=datetime.datetime(2021, 3, 19),
    )

    df = cf.get_data_frame()
    print(df.to_csv())

    assert all([a == b for a, b in zip(df["opened"].array, [1, 1, 0, 0, 0])])
    assert all([a == b for a, b in zip(df["inprogress"].array, [0, 0, 0, 1, 0])])


def test_cumulative_flow_label_removed_but_not_closed(stages):
    """When an issue has workflow label removed but issue is not closed, the report should show the last day
    the item was in the workflow state.

    """

    openedAt = datetime.datetime(2021, 3, 15, 8, tzinfo=datetime.timezone.utc)

    expected_data = [
        {"datetime": openedAt, "opened": 1},
        {"datetime": openedAt + datetime.timedelta(days=1), "opened": 0, "todo": 1},
        {"datetime": openedAt + datetime.timedelta(days=2), "todo": 0},
    ]

    data = pd.DataFrame.from_records(expected_data, index=["datetime"])
    tr = SimpleNamespace(data=data)

    series = ["opened"] + stages + ["closed"]
    cf = CumulativeFlow(
        [tr],
        stages=series,
        start_date=datetime.datetime(2021, 3, 15),
        end_date=datetime.datetime(2021, 3, 19),
    )
    df = cf.get_data_frame()
    print(df.to_csv())

    assert all([a == b for a, b in zip(df["opened"].array, [1, 0, 0, 0, 0])])
    assert all([a == b for a, b in zip(df["todo"].array, [0, 1, 0, 0, 0])])


def test_cumulative_flow_shows_hanging_open(stages):
    """Given an issue opened within the reporting window but never included in workflow."""
    openedAt = datetime.datetime(2021, 3, 15, 8, tzinfo=datetime.timezone.utc)
    expected_data = [
        {"datetime": openedAt, "opened": 1},
    ]

    data = pd.DataFrame.from_records(expected_data, index=["datetime"])
    tr = SimpleNamespace(data=data)
    series = ["opened"] + stages + ["closed"]

    cf = CumulativeFlow(
        [tr],
        stages=series,
        start_date=datetime.datetime(2021, 3, 17),
        end_date=datetime.datetime(2021, 3, 19),
    )
    df = cf.get_data_frame()
    print(df.to_csv())

    assert all([a == b for a, b in zip(df["opened"].array, [1, 1, 1])])

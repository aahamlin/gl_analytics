import pytest
import datetime

from gl_analytics.metrics import (
    daterange,
    start_date_for_time_window,
    CumulativeFlow,
    Transitions,
)


def test_daterange_exclusive():
    d1 = datetime.date(2021, 3, 15)
    d2 = datetime.date(2021, 3, 20)
    dates = [d for d in daterange(d1, d2)]
    assert dates[-1] == datetime.date(2021, 3, 19)


def test_start_date_window():
    d1 = datetime.date(2021, 3, 19)
    d2 = start_date_for_time_window(d1, 5)
    # 19, 18, 17, 16, 15n
    assert d2 == datetime.date(2021, 3, 15)


def test_start_date_window_value_error():
    """Require positive integer greater than 0."""
    with pytest.raises(ValueError):
        start_date_for_time_window(datetime.date(2021, 3, 30), -1)
    with pytest.raises(ValueError):
        start_date_for_time_window(datetime.date(2021, 3, 30), 0)
    assert start_date_for_time_window(datetime.date(2021, 3, 30), 1) == datetime.date(
        2021, 3, 30
    )


def test_transitions_is_sequence():

    wfData = [
        ("ready", datetime.datetime(2021, 3, 14, 15, 15, tzinfo=datetime.timezone.utc)),
        (
            "in progress",
            datetime.datetime(2021, 3, 15, 10, tzinfo=datetime.timezone.utc),
        ),
        ("done", datetime.datetime(2021, 3, 16, 10, tzinfo=datetime.timezone.utc)),
    ]

    openedAt = datetime.datetime(2021, 3, 14, 12, tzinfo=datetime.timezone.utc)

    expected_list = [
        ("opened", openedAt),
        ("ready", datetime.datetime(2021, 3, 14, 15, 15, tzinfo=datetime.timezone.utc)),
        (
            "in progress",
            datetime.datetime(2021, 3, 15, 10, tzinfo=datetime.timezone.utc),
        ),
        ("done", datetime.datetime(2021, 3, 16, 10, tzinfo=datetime.timezone.utc)),
    ]

    actual = Transitions(openedAt, None, workflow_transitions=wfData)

    print(f"expected {expected_list} to actual {list(actual)}")
    assert expected_list == list(actual)


def test_workflow_requires_date_object_for_start(stages):
    with pytest.raises(ValueError):
        CumulativeFlow([], labels=stages, start_date="2021-03-10T12:00:00.000Z")


def test_workflow_supports_datetime_for_start_date(stages):
    expected = datetime.datetime(2021, 3, 10, 12, tzinfo=datetime.timezone.utc)
    cf = CumulativeFlow([], labels=stages, start_date=expected, days=1)
    assert len(cf.included_dates) == 1
    cf.included_dates[0] = expected


def test_workflow_supports_datetime_for_end_date(stages):
    expected = datetime.datetime(2021, 3, 10, 12, tzinfo=datetime.timezone.utc)
    cf = CumulativeFlow([], labels=stages, end_date=expected, days=1)
    assert len(cf.included_dates) == 1
    cf.included_dates[0] = expected


def test_workflow_requires_date_object_for_end(stages):
    with pytest.raises(ValueError):
        CumulativeFlow([], labels=stages, end_date="2021-03-10T12:00:00.000Z")


def test_workflow_enforces_one_day_minimum(stages):
    with pytest.raises(ValueError):
        CumulativeFlow([], labels=stages, days=0)
    with pytest.raises(ValueError):
        CumulativeFlow([], labels=stages, days=-1)


def test_workflow_honors_today_with_days(stages):
    cf = CumulativeFlow([], labels=stages, days=5)
    today = datetime.datetime.utcnow().date()
    fiveDaysAgo = start_date_for_time_window(today, 5)
    assert len(cf.included_dates) == 5
    assert cf.included_dates[0] == fiveDaysAgo
    assert cf.included_dates[-1] == today


def test_workflow_honors_end_date_default_days(stages):
    # default 30 days
    cf = CumulativeFlow([], labels=stages, end_date=datetime.date(2021, 3, 30))
    assert len(cf.included_dates) == 30
    assert cf.included_dates[-1] == datetime.date(2021, 3, 30)
    assert cf.included_dates[0] == datetime.date(2021, 3, 1)


def test_workflow_honors_start_date(datetimes, stages):
    report_daterange = [d for d in daterange(datetimes.start, datetimes.end)]
    cf = CumulativeFlow(
        [],
        labels=stages,
        start_date=report_daterange[0],
        end_date=report_daterange[-1],
    )
    assert cf.included_dates[0] == report_daterange[0].date()


def test_workflow_honors_end_date(datetimes, stages):
    report_daterange = [d for d in daterange(datetimes.start, datetimes.end)]
    cf = CumulativeFlow(
        [],
        labels=stages,
        start_date=report_daterange[0],
        end_date=report_daterange[-1],
    )
    assert cf.included_dates[-1] == report_daterange[-1].date()


def test_cumulative_flow_counts_forward(stages, datetimes):

    tr = Transitions(
        datetimes.created_at,
        None,
        workflow_transitions=[
            ("todo", datetimes.mar_15_2021),
            ("inprogress", datetimes.mar_16_2021),
        ],
    )

    cf = CumulativeFlow(
        [tr],
        labels=stages,
        start_date=datetimes.mar_15_2021,
        end_date=datetimes.mar_16_2021,
    )
    df = cf.get_data_frame()
    print(df.to_csv())
    assert all([a == b for a, b in zip(df["todo"].array, [1, 0])])
    assert all([a == b for a, b in zip(df["inprogress"].array, [0, 1])])


def test_cumulative_flow_counts_backwards(stages, datetimes):

    tr = Transitions(
        datetimes.created_at,
        None,
        workflow_transitions=[
            ("review", datetimes.mar_15_2021),
            ("inprogress", datetimes.mar_16_2021),
        ],
    )

    cf = CumulativeFlow(
        [tr],
        labels=stages,
        start_date=datetimes.mar_15_2021,
        end_date=datetimes.mar_16_2021,
    )

    df = cf.get_data_frame()
    print(df.to_csv())
    assert all([a == b for a, b in zip(df["inprogress"].array, [0, 1])])
    assert all([a == b for a, b in zip(df["review"].array, [1, 0])])


def test_cumulative_flow_additive(stages, datetimes):

    tr = Transitions(
        datetimes.created_at,
        None,
        workflow_transitions=[
            ("todo", datetimes.mar_15_2021),
            ("inprogress", datetimes.mar_16_2021),
        ],
    )

    cf = CumulativeFlow(
        [tr, tr],
        labels=stages,
        start_date=datetimes.mar_15_2021,
        end_date=datetimes.mar_16_2021,
    )

    df = cf.get_data_frame()
    print(df.to_csv())
    assert all([a == b for a, b in zip(df["todo"].array, [2, 0])])
    assert all([a == b for a, b in zip(df["inprogress"].array, [0, 2])])


def test_cumulative_flow_counts_last_daily(stages, datetimes):
    """Test that 2 events added on same day == last occuring event of the day."""
    tr = Transitions(
        datetimes.created_at,
        None,
        workflow_transitions=[
            ("todo", datetimes.mar_15_2021),
            ("inprogress", datetimes.mar_15_2021),
            ("review", datetimes.mar_15_2021),
        ],
    )

    cf = CumulativeFlow(
        [tr],
        labels=stages,
        start_date=datetimes.mar_15_2021,
        end_date=datetimes.mar_16_2021,
    )

    df = cf.get_data_frame()
    print(df.to_csv())
    assert all([a == b for a, b in zip(df["todo"].array, [0, 0])])
    assert all([a == b for a, b in zip(df["inprogress"].array, [0, 0])])
    assert all([a == b for a, b in zip(df["review"].array, [1, 1])])
    assert all([a == b for a, b in zip(df["done"].array, [0, 0])])


def test_cumulative_flow_reports_days_from_today(stages):
    """Tests the default behavior calculating backwards by days, including today."""

    end = datetime.datetime.utcnow()
    start = start_date_for_time_window(end, 5)
    recent = [d for d in daterange(start, (end + datetime.timedelta(1)))]

    tr = Transitions(
        start,
        None,
        workflow_transitions=[
            ("todo", recent[1]),
            ("inprogress", recent[2]),
            ("review", recent[3]),
            ("done", recent[4]),
        ],
    )

    cf = CumulativeFlow(
        [tr],
        labels=stages,
        days=5,
    )

    df = cf.get_data_frame()
    print(df.to_csv())
    assert all([a == b for a, b in zip(df["todo"].array, [0, 1, 0, 0, 0])])
    assert all([a == b for a, b in zip(df["inprogress"].array, [0, 0, 1, 0, 0])])
    assert all([a == b for a, b in zip(df["review"].array, [0, 0, 0, 1, 0])])
    assert all([a == b for a, b in zip(df["done"].array, [0, 0, 0, 0, 1])])


def test_cumulative_flow_first_label_occurs_before_time_window(stages, datetimes):

    tr = Transitions(
        datetimes.created_at,
        None,
        workflow_transitions=[
            ("todo", datetimes.mar_10_2021),
            ("inprogress", datetimes.mar_17_2021),
        ],
    )

    cf = CumulativeFlow(
        [tr],
        labels=stages,
        start_date=datetimes.mar_15_2021,
        end_date=datetimes.mar_18_2021,
    )

    df = cf.get_data_frame()
    print(df.to_csv())
    assert all([a == b for a, b in zip(df["todo"].array, [1, 1, 0, 0])])
    assert all([a == b for a, b in zip(df["inprogress"].array, [0, 0, 1, 1])])


def test_cumulative_flow_stage_ends_when_closed(stages, datetimes):

    tr = Transitions(
        datetimes.created_at,
        datetimes.mar_19_2021,
        workflow_transitions=[
            ("todo", datetimes.mar_15_2021),
            ("inprogress", datetimes.mar_16_2021),
            ("review", datetimes.mar_17_2021),
            ("done", datetimes.mar_18_2021),
        ],
    )

    cf = CumulativeFlow(
        [tr],
        labels=stages,
        start_date=datetimes.mar_15_2021,
        end_date=datetimes.mar_20_2021,
    )
    df = cf.get_data_frame()
    print(df.to_csv())
    assert all([a == b for a, b in zip(df["done"].array, [0, 0, 0, 1, 0])])


def test_cumulative_flow_displays_hanging_open_closed(stages, datetimes):

    tr = Transitions(
        datetimes.created_at,
        datetimes.mar_18_2021,
        workflow_transitions=[],
    )
    series1 = ["opened"] + stages + ["closed"]
    cf = CumulativeFlow(
        [tr],
        labels=series1,
        start_date=datetimes.start,
        end_date=datetimes.end,
    )
    df = cf.get_data_frame()
    print(df.to_csv())

    assert all([a == b for a, b in zip(df["opened"].array, [1, 1, 1, 0, 0])])
    assert all([a == b for a, b in zip(df["closed"].array, [0, 0, 0, 1, 1])])


def test_cumulative_flow_created_to_closed_same_day(stages, datetimes):

    tr = Transitions(
        datetimes.mar_16_2021,
        datetimes.mar_16_2021,
        workflow_transitions=[
            ("todo", datetimes.mar_16_2021),
            ("inprogress", datetimes.mar_16_2021),
            ("review", datetimes.mar_16_2021),
        ],
    )

    series1 = ["opened"] + stages + ["closed"]
    cf = CumulativeFlow(
        [tr],
        labels=series1,
        start_date=datetimes.start,
        end_date=datetimes.end,
    )

    df = cf.get_data_frame()
    print(df.to_csv())

    assert all([a == b for a, b in zip(df["opened"].array, [0, 0, 0, 0, 0])])
    assert all([a == b for a, b in zip(df["todo"].array, [0, 0, 0, 0, 0])])
    assert all([a == b for a, b in zip(df["inprogress"].array, [0, 0, 0, 0, 0])])
    assert all([a == b for a, b in zip(df["review"].array, [0, 0, 0, 0, 0])])
    assert all([a == b for a, b in zip(df["done"].array, [0, 0, 0, 0, 0])])
    assert all([a == b for a, b in zip(df["closed"].array, [0, 1, 1, 1, 1])])


def test_cumulative_flow_filtered_labels_do_not_affect_count_of_columns(datetimes):

    tr = Transitions(
        datetimes.start,
        datetimes.end,
        workflow_transitions=[
            ("todo", datetimes.mar_16_2021),
            ("inprogress", datetimes.mar_16_2021),
            ("review", datetimes.mar_17_2021),
            ("done", datetimes.mar_18_2021),
        ],
    )

    series1 = ["opened", "inprogress", "done", "closed"]

    cf = CumulativeFlow(
        [tr],
        labels=series1,
        start_date=datetimes.start,
        end_date=datetimes.end,
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


def test_cumulative_flow_accounts_for_filtered_stages(datetimes):

    tr = Transitions(
        datetimes.created_at,
        datetimes.mar_19_2021,
        workflow_transitions=[
            ("todo", datetimes.mar_16_2021),
            ("inprogress", datetimes.mar_17_2021),
            ("review", datetimes.mar_18_2021),
        ],
    )

    # create new series without todo or review columns
    series1 = ["opened", "inprogress", "done", "closed"]

    cf = CumulativeFlow(
        [tr],
        labels=series1,
        start_date=datetimes.mar_15_2021,
        end_date=datetimes.mar_19_2021,
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


def test_cumulative_flow_offsets_for_closed_stages(datetimes):
    """Closed on same day as last stage "done", but Closed is not included."""
    tr = Transitions(
        datetimes.mar_16_2021,
        datetimes.mar_16_2021,
        workflow_transitions=[
            ("todo", datetimes.mar_16_2021),
            ("inprogress", datetimes.mar_16_2021),
            ("review", datetimes.mar_16_2021),
            ("done", datetimes.mar_16_2021),
        ],
    )

    cf = CumulativeFlow(
        [tr],
        labels=["done"],
        start_date=datetimes.start,
        end_date=datetimes.end,
    )

    df = cf.get_data_frame()
    print(df.to_csv())

    assert all([a == b for a, b in zip(df["done"].array, [0, 1, 0, 0, 0])])


def test_cumulative_flow_offsets_for_filtered_stages(datetimes):
    """Same day as last stage "review", but "review" is not included.

    Report will offset the "inprogress" date.
    """
    tr = Transitions(
        datetimes.mar_16_2021,
        None,
        workflow_transitions=[
            ("todo", datetimes.mar_16_2021),
            ("inprogress", datetimes.mar_16_2021),
            ("review", datetimes.mar_16_2021),
        ],
    )

    cf = CumulativeFlow(
        [tr],
        labels=["inprogress"],
        start_date=datetimes.start,
        end_date=datetimes.end,
    )

    df = cf.get_data_frame()
    print(df.to_csv())

    assert all([a == b for a, b in zip(df["inprogress"].array, [0, 1, 0, 0, 0])])


def test_cumulative_flow_opened_ends_at_next_filtered_stage(datetimes):
    """A report should always show the opened items.

    When an item is open and has a scoped label excluded from the workflow, the report should
    include the item in the opened column.
    """
    tr = Transitions(
        datetimes.created_at,
        datetimes.end,
        workflow_transitions=[
            ("todo", datetimes.mar_17_2021),
            ("inprogress", datetimes.mar_18_2021),
        ],
    )

    cf = CumulativeFlow(
        [tr],
        labels=["opened", "inprogress"],
        start_date=datetimes.start,
        end_date=datetimes.end,
    )

    df = cf.get_data_frame()
    print(df.to_csv())

    assert all([a == b for a, b in zip(df["opened"].array, [1, 1, 0, 0, 0])])
    assert all([a == b for a, b in zip(df["inprogress"].array, [0, 0, 0, 1, 0])])


def test_cumulative_flow_accounts_for_last_day_of_report_window(stages, datetimes):
    """When an issue is not closed but the last stage ends on the last day of the report window."""

    series = ["opened"] + stages + ["closed"]
    tr = Transitions(
        datetimes.mar_15_2021,
        None,
        workflow_transitions=[
            ("todo", datetimes.mar_16_2021),
            ("inprogress", datetimes.mar_17_2021),
            ("review", datetimes.mar_18_2021),
            ("done", datetimes.mar_19_2021),
        ],
    )
    cf = CumulativeFlow(
        [tr],
        labels=series,
        start_date=datetimes.mar_15_2021,
        end_date=datetimes.mar_19_2021,
    )
    df = cf.get_data_frame()
    print(df.to_csv())

    assert all([a == b for a, b in zip(df["opened"].array, [1, 0, 0, 0, 0])])
    assert all([a == b for a, b in zip(df["todo"].array, [0, 1, 0, 0, 0])])
    assert all([a == b for a, b in zip(df["inprogress"].array, [0, 0, 1, 0, 0])])
    assert all([a == b for a, b in zip(df["review"].array, [0, 0, 0, 1, 0])])
    assert all([a == b for a, b in zip(df["done"].array, [0, 0, 0, 0, 1])])


@pytest.mark.skip(reason="Not implemented")
def test_cumulative_flow_label_removed_but_not_closed():
    """When an issue has workflow label removed but issue is not closed, the report should show the last day
    the item was in the workflow state.

    """
    assert False, "Not implemented"

import pytest
import datetime

# XXX date handling needs to be cleaned up
from gl_analytics.metrics import (
    daterange,
    start_date_for_time_window,
    CumulativeFlow,
    Transitions,
)

# dates of transitions in test, unless otherwise provided
TEST_CREATED_AT = datetime.datetime(2021, 3, 10)
TEST_DATETIME_LIST = [
    d for d in daterange(datetime.datetime(2021, 3, 15), datetime.datetime(2021, 3, 21))
]
# series of workflow steps
TEST_SERIES = ["todo", "inprogress", "review", "done"]


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


def test_workflow_requires_date_object_for_start():
    with pytest.raises(ValueError):
        CumulativeFlow([], labels=TEST_SERIES, start_date="2021-03-10T12:00:00.000Z")


def test_workflow_supports_datetime_for_start_date():
    expected = datetime.datetime(2021, 3, 10, 12, tzinfo=datetime.timezone.utc)
    cf = CumulativeFlow([], labels=TEST_SERIES, start_date=expected, days=1)
    assert len(cf.included_dates) == 1
    cf.included_dates[0] = expected


def test_workflow_supports_datetime_for_end_date():
    expected = datetime.datetime(2021, 3, 10, 12, tzinfo=datetime.timezone.utc)
    cf = CumulativeFlow([], labels=TEST_SERIES, end_date=expected, days=1)
    assert len(cf.included_dates) == 1
    cf.included_dates[0] = expected


def test_workflow_requires_date_object_for_end():
    with pytest.raises(ValueError):
        CumulativeFlow([], labels=TEST_SERIES, end_date="2021-03-10T12:00:00.000Z")


def test_workflow_enforces_one_day_minimum():
    with pytest.raises(ValueError):
        CumulativeFlow([], labels=TEST_SERIES, days=0)
    with pytest.raises(ValueError):
        CumulativeFlow([], labels=TEST_SERIES, days=-1)


def test_workflow_honors_today_with_days():
    cf = CumulativeFlow([], labels=TEST_SERIES, days=5)
    today = datetime.datetime.utcnow().date()
    fiveDaysAgo = start_date_for_time_window(today, 5)
    assert len(cf.included_dates) == 5
    assert cf.included_dates[0] == fiveDaysAgo
    assert cf.included_dates[-1] == today


def test_workflow_honors_end_date_default_days():
    # default 30 days
    cf = CumulativeFlow([], labels=TEST_SERIES, end_date=datetime.date(2021, 3, 30))
    assert len(cf.included_dates) == 30
    assert cf.included_dates[-1] == datetime.date(2021, 3, 30)
    assert cf.included_dates[0] == datetime.date(2021, 3, 1)


def test_workflow_honors_start_date():
    cf = CumulativeFlow(
        [],
        labels=TEST_SERIES,
        start_date=TEST_DATETIME_LIST[0],
        end_date=TEST_DATETIME_LIST[-1],
    )
    assert cf.included_dates[0] == TEST_DATETIME_LIST[0].date()


def test_workflow_honors_end_date():
    cf = CumulativeFlow(
        [],
        labels=TEST_SERIES,
        start_date=TEST_DATETIME_LIST[0],
        end_date=TEST_DATETIME_LIST[-1],
    )
    assert cf.included_dates[-1] == TEST_DATETIME_LIST[-1].date()


def test_collect_values():
    list_of_Ts = [
        Transitions(
            TEST_CREATED_AT,
            None,
            workflow_transitions=[
                ("todo", TEST_DATETIME_LIST[0]),
                ("inprogress", TEST_DATETIME_LIST[1]),
                ("done", TEST_DATETIME_LIST[-1]),
            ],
        ),
        Transitions(
            TEST_CREATED_AT,
            None,
            workflow_transitions=[
                ("todo", TEST_DATETIME_LIST[1]),
                ("inprogress", TEST_DATETIME_LIST[3]),
                ("review", TEST_DATETIME_LIST[4]),
            ],
        ),
    ]

    cf = CumulativeFlow(
        list_of_Ts,
        labels=TEST_SERIES,
        start_date=TEST_DATETIME_LIST[0].date(),
        end_date=TEST_DATETIME_LIST[-1].date(),
    )
    df = cf.get_data_frame()
    print(df.to_csv())
    #            todo  inprogress  review  done
    # 2021-03-15     1           0       0     0
    # 2021-03-16     1           1       0     0
    # 2021-03-17     1           1       0     0
    # 2021-03-18     0           2       0     0
    # 2021-03-19     0           1       1     0
    # 2021-03-20     0           0       1     1

    # access various data
    # print(df['inprogress'])
    assert len(df["inprogress"].array) == 6
    assert all([a == b for a, b in zip(df["inprogress"].array, [0, 1, 1, 2, 1, 0])])
    assert df.at["2021-03-18", "inprogress"] == 2
    assert df.iloc[0, 0] == 1
    assert df.loc["2021-03-15", "todo"] == 1
    assert df.iloc[5, 3] == 1
    assert df.loc["2021-03-20", "done"] == 1
    # print(df.loc[str(date[-1])])
    # assert df.loc[str(date[-1])] == [0, 0, 1, 1]


def test_events_on_same_day_record_last_event():
    """Test that 2 events added on same day == last occuring event of the day."""
    list_of_Ts = [
        Transitions(
            TEST_CREATED_AT,
            None,
            workflow_transitions=[
                ("todo", TEST_DATETIME_LIST[1]),
                ("inprogress", TEST_DATETIME_LIST[1]),
                ("review", TEST_DATETIME_LIST[1]),
            ],
        )
    ]

    cf = CumulativeFlow(
        list_of_Ts,
        labels=TEST_SERIES,
        start_date=TEST_DATETIME_LIST[0].date(),
        end_date=TEST_DATETIME_LIST[-1].date(),
    )
    df = cf.get_data_frame()
    print(df.to_csv())

    assert len(df["todo"].array) == 6
    assert all([a == b for a, b in zip(df["todo"].array, [0, 0, 0, 0, 0, 0])])
    assert all([a == b for a, b in zip(df["inprogress"].array, [0, 0, 0, 0, 0, 0])])
    assert all([a == b for a, b in zip(df["review"].array, [0, 1, 1, 1, 1, 1])])
    assert all([a == b for a, b in zip(df["done"].array, [0, 0, 0, 0, 0, 0])])


def test_events_in_days_from_today():
    """Tests the default behavior calculating backwards by days, including today."""
    # IMPORTANT: in order to end the range including today, increment by one day
    end = datetime.datetime.utcnow()
    start = start_date_for_time_window(end, 5)
    print(f"from {start} to {end}")

    recent = [d for d in daterange(start, (end + datetime.timedelta(1)))]

    list_of_Ts = [
        Transitions(
            TEST_CREATED_AT,
            None,
            workflow_transitions=[
                ("todo", recent[1]),
                ("inprogress", recent[1]),
                ("review", recent[1]),
            ],
        )
    ]

    cf = CumulativeFlow(list_of_Ts, labels=TEST_SERIES, days=5)
    df = cf.get_data_frame()
    print(df.to_csv())

    assert len(df["todo"].array) == 5
    assert all([a == b for a, b in zip(df["todo"].array, [0, 0, 0, 0, 0])])
    assert all([a == b for a, b in zip(df["inprogress"].array, [0, 0, 0, 0, 0])])
    assert all([a == b for a, b in zip(df["review"].array, [0, 1, 1, 1, 1])])
    assert all([a == b for a, b in zip(df["done"].array, [0, 0, 0, 0, 0])])


def test_opened_before_time_window():
    # dates array starts at 2021-03-15
    list_of_Ts = [
        Transitions(
            TEST_CREATED_AT,
            None,
            workflow_transitions=[
                ("todo", datetime.datetime(2021, 3, 1)),
                ("inprogress", TEST_DATETIME_LIST[1]),
                ("review", TEST_DATETIME_LIST[3]),
                ("done", TEST_DATETIME_LIST[-1]),
            ],
        )
    ]

    cf = CumulativeFlow(
        list_of_Ts,
        labels=TEST_SERIES,
        start_date=TEST_DATETIME_LIST[0],
        end_date=TEST_DATETIME_LIST[-1],
    )
    df = cf.get_data_frame()
    print(df.to_csv())

    assert len(df["todo"].array) == 6
    assert all([a == b for a, b in zip(df["todo"].array, [1, 0, 0, 0, 0, 0])])
    assert all([a == b for a, b in zip(df["inprogress"].array, [0, 1, 1, 0, 0, 0])])
    assert all([a == b for a, b in zip(df["review"].array, [0, 0, 0, 1, 1, 0])])
    assert all([a == b for a, b in zip(df["done"].array, [0, 0, 0, 0, 0, 1])])


def test_close_during_time_window():
    # dates array starts at 2021-03-15
    list_of_Ts = [
        Transitions(
            TEST_CREATED_AT,
            TEST_DATETIME_LIST[-2],
            workflow_transitions=[
                ("todo", datetime.datetime(2021, 3, 1)),
                ("inprogress", TEST_DATETIME_LIST[1]),
                ("review", TEST_DATETIME_LIST[2]),
                ("done", TEST_DATETIME_LIST[3]),
            ],
        )
    ]

    cf = CumulativeFlow(
        list_of_Ts,
        labels=TEST_SERIES,
        start_date=TEST_DATETIME_LIST[0],
        end_date=TEST_DATETIME_LIST[-1],
    )
    df = cf.get_data_frame()
    print(df.to_csv())

    assert len(df["todo"].array) == 6
    assert all([a == b for a, b in zip(df["todo"].array, [1, 0, 0, 0, 0, 0])])
    assert all([a == b for a, b in zip(df["inprogress"].array, [0, 1, 0, 0, 0, 0])])
    assert all([a == b for a, b in zip(df["review"].array, [0, 0, 1, 0, 0, 0])])
    assert all([a == b for a, b in zip(df["done"].array, [0, 0, 0, 1, 0, 0])])


def test_step_backwards():
    # dates array starts at 2021-03-15
    list_of_Ts = [
        Transitions(
            TEST_CREATED_AT,
            None,
            workflow_transitions=[
                ("todo", datetime.datetime(2021, 3, 1)),
                ("inprogress", TEST_DATETIME_LIST[1]),
                ("review", TEST_DATETIME_LIST[2]),
                ("inprogress", TEST_DATETIME_LIST[3]),
                ("review", TEST_DATETIME_LIST[4]),
                ("done", TEST_DATETIME_LIST[-1]),
            ],
        )
    ]

    cf = CumulativeFlow(
        list_of_Ts,
        labels=TEST_SERIES,
        start_date=TEST_DATETIME_LIST[0],
        end_date=TEST_DATETIME_LIST[-1],
    )
    df = cf.get_data_frame()
    print(df.to_csv())

    assert len(df["todo"].array) == 6
    assert all([a == b for a, b in zip(df["todo"].array, [1, 0, 0, 0, 0, 0])])
    # XXX This inprogress assertion fails because I have not implemented the handling of tracking
    #     backward and forward movement through the workflow yet.
    assert all([a == b for a, b in zip(df["inprogress"].array, [0, 1, 0, 1, 0, 0])])
    assert all([a == b for a, b in zip(df["review"].array, [0, 0, 1, 0, 1, 0])])
    assert all([a == b for a, b in zip(df["done"].array, [0, 0, 0, 0, 0, 1])])


def test_transitions_same_day_with_closed():
    list_of_Ts = [
        Transitions(
            TEST_CREATED_AT,
            TEST_DATETIME_LIST[2],
            workflow_transitions=[
                ("todo", TEST_DATETIME_LIST[1]),
                ("inprogress", TEST_DATETIME_LIST[1]),
                ("review", TEST_DATETIME_LIST[1]),
            ],
        )
    ]

    series1 = ["opened"] + TEST_SERIES + ["closed"]
    cf = CumulativeFlow(
        list_of_Ts,
        labels=series1,
        start_date=TEST_DATETIME_LIST[0],
        end_date=TEST_DATETIME_LIST[-1],
    )
    df = cf.get_data_frame()
    print(df.to_csv())

    assert len(df["todo"].array) == 6
    assert all([a == b for a, b in zip(df["opened"].array, [1, 0, 0, 0, 0, 0])])
    assert all([a == b for a, b in zip(df["todo"].array, [0, 0, 0, 0, 0, 0])])
    assert all([a == b for a, b in zip(df["inprogress"].array, [0, 0, 0, 0, 0, 0])])
    assert all([a == b for a, b in zip(df["review"].array, [0, 1, 0, 0, 0, 0])])
    assert all([a == b for a, b in zip(df["done"].array, [0, 0, 0, 0, 0, 0])])
    assert all([a == b for a, b in zip(df["closed"].array, [0, 0, 1, 1, 1, 1])])


def test_created_to_closed_same_day():
    list_of_Ts = [
        Transitions(
            TEST_DATETIME_LIST[1],
            TEST_DATETIME_LIST[1],
            workflow_transitions=[
                ("todo", TEST_DATETIME_LIST[1]),
                ("inprogress", TEST_DATETIME_LIST[1]),
                ("review", TEST_DATETIME_LIST[1]),
            ],
        )
    ]

    series1 = ["opened"] + TEST_SERIES + ["closed"]

    cf = CumulativeFlow(
        list_of_Ts,
        labels=series1,
        start_date=TEST_DATETIME_LIST[0],
        end_date=TEST_DATETIME_LIST[-1],
    )
    df = cf.get_data_frame()
    print(df.to_csv())

    assert len(df["todo"].array) == 6
    assert all([a == b for a, b in zip(df["opened"].array, [0, 0, 0, 0, 0, 0])])
    assert all([a == b for a, b in zip(df["todo"].array, [0, 0, 0, 0, 0, 0])])
    assert all([a == b for a, b in zip(df["inprogress"].array, [0, 0, 0, 0, 0, 0])])
    assert all([a == b for a, b in zip(df["review"].array, [0, 0, 0, 0, 0, 0])])
    assert all([a == b for a, b in zip(df["done"].array, [0, 0, 0, 0, 0, 0])])
    assert all([a == b for a, b in zip(df["closed"].array, [0, 1, 1, 1, 1, 1])])


def test_save_image():

    list_of_Ts = [
        Transitions(
            TEST_CREATED_AT,
            None,
            workflow_transitions=[
                ("todo", TEST_DATETIME_LIST[0]),
                ("inprogress", TEST_DATETIME_LIST[1]),
                ("done", TEST_DATETIME_LIST[-1]),
            ],
        ),
        Transitions(
            TEST_CREATED_AT,
            None,
            workflow_transitions=[
                ("todo", TEST_DATETIME_LIST[1]),
                ("inprogress", TEST_DATETIME_LIST[3]),
                ("review", TEST_DATETIME_LIST[4]),
            ],
        ),
    ]

    cf = CumulativeFlow(
        list_of_Ts,
        labels=TEST_SERIES,
        start_date=TEST_DATETIME_LIST[0],
        end_date=TEST_DATETIME_LIST[-1],
    )
    df = cf.get_data_frame()
    print(df.to_csv())
    #            todo  inprogress  review  done
    # 2021-03-15     1           0       0     0
    # 2021-03-16     1           1       0     0
    # 2021-03-17     1           1       0     0
    # 2021-03-18     0           2       0     0
    # 2021-03-19     0           1       1     0
    # 2021-03-20     0           0       1     1
    import os

    if os.path.exists("output.png"):
        os.remove("output.png")

    assert not os.path.exists("output.png")

    import matplotlib.pyplot as plt

    plt.close("all")
    ax = df.plot.area()
    fig = ax.get_figure()
    fig.savefig("output.png")
    assert os.path.exists("output.png")

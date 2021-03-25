import pytest
import datetime
import pandas as pd

from random import randrange
from gl_analytics.metrics import daterange, start_date_for_time_window, _resolve_date, WorkflowHistory

dates = [d for d in daterange(datetime.date(2021, 3, 15), datetime.date(2021, 3, 21))]

# series of workflow steps
series = ['todo','inprogress','review','done']

def test_daterange_exclusive():
    d1 = datetime.date(2021, 3, 15)
    d2 = datetime.date(2021, 3, 20)
    dates = [d for d in daterange(d1, d2)]
    assert dates[-1] == datetime.date(2021, 3, 19)

def test_start_date_window():
    d1 = datetime.date(2021, 3, 19)
    d2 = start_date_for_time_window(d1, 5)
     # 19, 18, 17, 16, 15
    assert d2 == datetime.date(2021, 3, 15)

def test_start_date_window_value_error():
    """Require positive integer greater than 0.
    """
    with pytest.raises(ValueError):
        start_date_for_time_window(datetime.date(2021, 3, 30), -1)
    with pytest.raises(ValueError):
        start_date_for_time_window(datetime.date(2021, 3, 30), 0)
    assert start_date_for_time_window(datetime.date(2021, 3, 30), 1) == datetime.date(2021, 3, 30)

def test_resolve_date_from_date():
    expected = datetime.date(2021, 3, 20)
    assert _resolve_date(expected) == expected

def test_resolve_date_from_datetime():
    expected = datetime.datetime(2021, 3, 20, 0, 0, 0, tzinfo=datetime.timezone.utc)
    assert _resolve_date(expected) == expected.date()


def test_resolve_date_from_other():
    with pytest.raises(ValueError):
        _resolve_date('foo')

def test_workflow_honors_today_with_days():
    wfh = WorkflowHistory([], series=series, days=5)
    today = datetime.datetime.utcnow().date()
    fiveDaysAgo = start_date_for_time_window(today, 5)
    assert len(wfh.included_dates) == 5
    assert wfh.included_dates[0] == fiveDaysAgo
    assert wfh.included_dates[-1] == today

def test_workflow_honors_end_date_default_days():
    # default 30 days
    wfh = WorkflowHistory([], series=series, end_date=datetime.date(2021, 3, 30))
    assert len(wfh.included_dates) == 30
    assert wfh.included_dates[0] == datetime.date(2021, 3, 1)
    assert wfh.included_dates[-1] == datetime.date(2021, 3, 30)

def test_workflow_honors_start_date():
    wfh = WorkflowHistory([], series=series, start_date=dates[0], end_date=dates[-1])
    assert wfh.included_dates[0] == dates[0]
    assert wfh.included_dates[-1] == dates[-1]

def test_collect_values():
    events = []
    events.append([
        ('add', 'todo', dates[0]),
        ('add', 'inprogress',dates[1]),
        ('remove', 'todo', dates[1]),
        ('add', 'done', dates[-1]),
        ('remove', 'inprogress',dates[-1])
    ])
    events.append([
        ('add', 'todo', dates[1]),
        ('add', 'inprogress',dates[3]),
        ('remove', 'todo', dates[3]),
        ('add', 'review', dates[4]),
        ('remove', 'inprogress',dates[4])
    ])

    wfh = WorkflowHistory(events, series=series, start_date=dates[0], end_date=dates[-1])
    df = wfh._get_data_frame()
    print(df.to_csv())
    #            todo  inprogress  review  done
    #2021-03-15     1           0       0     0
    #2021-03-16     1           1       0     0
    #2021-03-17     1           1       0     0
    #2021-03-18     0           2       0     0
    #2021-03-19     0           1       1     0
    #2021-03-20     0           0       1     1

    # access various data
    # print(df['inprogress'])
    assert len(df["inprogress"].array) == 6
    assert all([a == b for a, b in zip(df["inprogress"].array, [0, 1, 1, 2, 1, 0])])
    assert df.at["2021-03-18", "inprogress"] == 2
    assert df.iloc[0, 0] == 1
    assert df.loc["2021-03-15", "todo"] == 1
    assert df.iloc[5, 3] == 1
    assert df.loc["2021-03-20", "done"] == 1
    #print(df.loc[str(date[-1])])
    #assert df.loc[str(date[-1])] == [0, 0, 1, 1]

def test_events_on_same_day_record_last_event():
    """Test that 2 events added on same day == last occuring event of the day.
    """
    events = []
    events.append([
        ('add', 'todo', dates[1]),
        ('add', 'inprogress',dates[1]),
        ('remove', 'todo', dates[1]),
        ('add', 'review', dates[1]),
        ('remove', 'inprogress',dates[1])
    ])

    wfh = WorkflowHistory(events, series=series, start_date=dates[0], end_date=dates[-1])
    df = wfh._get_data_frame()
    print(df.to_csv())

    assert len(df["todo"].array) == 6
    assert all([a == b for a, b in zip(df["todo"].array, [0, 0, 0, 0, 0, 0])])
    assert all([a == b for a, b in zip(df["inprogress"].array, [0, 0, 0, 0, 0, 0])])
    assert all([a == b for a, b in zip(df["review"].array, [0, 1, 1, 1, 1, 1])])
    assert all([a == b for a, b in zip(df["done"].array, [0, 0, 0, 0, 0, 0])])

def test_events_in_days_from_today():
    """Tests the default behavior calculating backwards by days, including today.
    """
    # IMPORTANT: in order to end the range including today, increment by one day
    end = datetime.datetime.utcnow().date()
    start = start_date_for_time_window(end, 5)
    print(f'from {start} to {end}')

    recent = [d for d in daterange(start, (end + datetime.timedelta(1)))]

    events = []
    events.append([
        ('add', 'todo', recent[1]),
        ('add', 'inprogress', recent[1]),
        ('remove', 'todo', recent[1]),
        ('add', 'review', recent[1]),
        ('remove', 'inprogress', recent[1])
    ])

    wfh = WorkflowHistory(events, series=series, days=5)
    df = wfh._get_data_frame()
    print(df.to_csv())

    assert len(df["todo"].array) == 5
    assert all([a == b for a, b in zip(df["todo"].array, [0, 0, 0, 0, 0])])
    assert all([a == b for a, b in zip(df["inprogress"].array, [0, 0, 0, 0, 0])])
    assert all([a == b for a, b in zip(df["review"].array, [0, 1, 1, 1, 1])])
    assert all([a == b for a, b in zip(df["done"].array, [0, 0, 0, 0, 0])])

def test_step_before_time_window():
    # dates array starts at 2021-03-15
    events = []
    events.append([
        ('add', 'todo', datetime.date(2021, 3, 1)),
        ('add', 'inprogress',dates[1]),
        ('remove', 'todo', dates[1]),
        ('add', 'review', dates[3]),
        ('remove', 'inprogress',dates[3]),
        ('add', 'done', dates[-1]),
        ('remove', 'review', dates[-1])
    ])

    wfh = WorkflowHistory(events, series=series, start_date=dates[0], end_date=dates[-1])
    df = wfh._get_data_frame()
    print(df.to_csv())

    assert len(df["todo"].array) == 6
    assert all([a == b for a, b in zip(df["todo"].array, [1, 0, 0, 0, 0, 0])])
    assert all([a == b for a, b in zip(df["inprogress"].array, [0, 1, 1, 0, 0, 0])])
    assert all([a == b for a, b in zip(df["review"].array, [0, 0, 0, 1, 1, 0])])
    assert all([a == b for a, b in zip(df["done"].array, [0, 0, 0, 0, 0, 1])])


def skip_test_step_backwards():
    # dates array starts at 2021-03-15
    events = []
    events.append([
        ('add', 'todo', datetime.date(2021, 3, 1)),
        ('add', 'inprogress',dates[1]),
        ('remove', 'todo', dates[1]),
        ('add', 'review', dates[2]),
        ('remove', 'inprogress',dates[2]),
        ('add', 'inprogress',dates[3]),
        ('remove', 'review', dates[3]),
        ('add', 'review', dates[4]),
        ('remove', 'inprogress',dates[4]),
        ('add', 'done', dates[-1]),
        ('remove', 'review', dates[-1])
    ])

    wfh = WorkflowHistory(events, series=series,  start_date=dates[0], end_date=dates[-1])
    df = wfh._get_data_frame()
    print(df.to_csv())

    assert len(df["todo"].array) == 6
    assert all([a == b for a, b in zip(df["todo"].array,       [1, 0, 0, 0, 0, 0])])
    # XXX This inprogress assertion fails because I have not implemented the handling of tracking
    #     backward and forward movement through the workflow yet.
    assert all([a == b for a, b in zip(df["inprogress"].array, [0, 1, 0, 1, 0, 0])])
    assert all([a == b for a, b in zip(df["review"].array,     [0, 0, 1, 0, 1, 0])])
    assert all([a == b for a, b in zip(df["done"].array,       [0, 0, 0, 0, 0, 1])])
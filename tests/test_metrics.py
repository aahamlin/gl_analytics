import pytest
import datetime
import pandas as pd

from random import randrange

# XXX date handling needs to be cleaned up
from gl_analytics.metrics import daterange, start_date_for_time_window, _resolve_date, \
    build_transitions, WorkflowHistory, Transitions

# dates of transitions in test, unless otherwise provided
created_at = datetime.datetime(2021, 3, 10)
datetimes = [d for d in daterange(datetime.datetime(2021, 3, 15), datetime.datetime(2021, 3, 21))]
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
     # 19, 18, 17, 16, 15n
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

def test_transitions_is_sequence():

    wfData =  [
        ('ready', datetime.datetime(2021,3,14,15,15, tzinfo=datetime.timezone.utc)),
        ('in progress', datetime.datetime(2021, 3,15,10,tzinfo=datetime.timezone.utc)),
        ('done', datetime.datetime(2021, 3,16,10,tzinfo=datetime.timezone.utc))
    ]

    openedAt = datetime.datetime(2021, 3,14, 12, tzinfo=datetime.timezone.utc)

    expected_list = [
        ('opened', openedAt),
        ('ready', datetime.datetime(2021,3,14,15,15, tzinfo=datetime.timezone.utc)),
        ('in progress', datetime.datetime(2021, 3,15,10,tzinfo=datetime.timezone.utc)),
        ('done', datetime.datetime(2021, 3,16,10,tzinfo=datetime.timezone.utc))
    ]

    actual = Transitions(openedAt, None, workflow_transitions=wfData)

    print(f"expected {expected_list} to actual {list(actual)}")
    assert expected_list == list(actual)

def test_build_transitions_from_issues():
    from gl_analytics.issues import Issue
    wfData =  [
        ('ready', datetime.datetime(2021,3,14,15,15, tzinfo=datetime.timezone.utc)),
        ('in progress', datetime.datetime(2021, 3,15,10,tzinfo=datetime.timezone.utc)),
        ('done', datetime.datetime(2021, 3,16,10,tzinfo=datetime.timezone.utc))
    ]

    issues = [Issue(1, 2, created_at, label_events=wfData), Issue(2, 2, created_at, label_events=wfData)]
    transitions = build_transitions(issues)
    assert len(transitions) == 2
    assert all([len(t)==4 for t in transitions]) # opened, ready, in progress, done

def test_workflow_requires_date_object_for_start():
    with pytest.raises(ValueError):
        WorkflowHistory([], series=series, start_date='2021-03-10T12:00:00.000Z')

def test_workflow_supports_datetime_for_start_date():
    expected = datetime.datetime(2021, 3, 10, 12, tzinfo=datetime.timezone.utc)
    wfh = WorkflowHistory([], series=series, start_date=expected, days=1)
    assert len(wfh.included_dates) == 1
    wfh.included_dates[0] = expected

def test_workflow_supports_datetime_for_end_date():
    expected = datetime.datetime(2021, 3, 10, 12, tzinfo=datetime.timezone.utc)
    wfh = WorkflowHistory([], series=series, end_date=expected, days=1)
    assert len(wfh.included_dates) == 1
    wfh.included_dates[0] = expected

def test_workflow_requires_date_object_for_end():
    with pytest.raises(ValueError):
        WorkflowHistory([], series=series, end_date='2021-03-10T12:00:00.000Z')

def test_workflow_enforces_one_day_minimum():
    with pytest.raises(ValueError):
        WorkflowHistory([], series=series, days=0)
    with pytest.raises(ValueError):
        WorkflowHistory([], series=series, days=-1)

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
    assert wfh.included_dates[-1] == datetime.date(2021, 3, 30)
    assert wfh.included_dates[0] == datetime.date(2021, 3, 1)

def test_workflow_honors_start_date():
    wfh = WorkflowHistory([], series=series, start_date=datetimes[0], end_date=datetimes[-1])
    assert wfh.included_dates[0] == datetimes[0].date()

def test_workflow_honors_end_date():
    wfh = WorkflowHistory([], series=series, start_date=datetimes[0], end_date=datetimes[-1])
    assert wfh.included_dates[-1] == datetimes[-1].date()

def test_collect_values():
    list_of_Ts = [
        Transitions(created_at, None, workflow_transitions=[
            ('todo', datetimes[0]), ('inprogress',datetimes[1]), ('done', datetimes[-1])
        ]),
        Transitions(created_at, None, workflow_transitions=[
            ('todo', datetimes[1]), ('inprogress',datetimes[3]), ('review', datetimes[4])
        ])
    ]

    wfh = WorkflowHistory(list_of_Ts, series=series, start_date=datetimes[0].date(), end_date=datetimes[-1].date())
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
    list_of_Ts = [
        Transitions(created_at, None, workflow_transitions=[
            ('todo', datetimes[1]), ('inprogress',datetimes[1]), ('review', datetimes[1])
        ])
    ]

    wfh = WorkflowHistory(list_of_Ts, series=series, start_date=datetimes[0].date(), end_date=datetimes[-1].date())
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
    end = datetime.datetime.utcnow()
    start = start_date_for_time_window(end, 5)
    print(f'from {start} to {end}')

    recent = [d for d in daterange(start, (end + datetime.timedelta(1)))]

    list_of_Ts = [
        Transitions(created_at, None, workflow_transitions=[
            ('todo', recent[1]), ('inprogress', recent[1]), ('review', recent[1])
        ])
    ]

    wfh = WorkflowHistory(list_of_Ts, series=series, days=5)
    df = wfh._get_data_frame()
    print(df.to_csv())

    assert len(df["todo"].array) == 5
    assert all([a == b for a, b in zip(df["todo"].array, [0, 0, 0, 0, 0])])
    assert all([a == b for a, b in zip(df["inprogress"].array, [0, 0, 0, 0, 0])])
    assert all([a == b for a, b in zip(df["review"].array, [0, 1, 1, 1, 1])])
    assert all([a == b for a, b in zip(df["done"].array, [0, 0, 0, 0, 0])])

def test_step_before_time_window():
    # dates array starts at 2021-03-15
    list_of_Ts = [
        Transitions(created_at, None, workflow_transitions=[
            ('todo', datetime.datetime(2021, 3, 1)), ('inprogress',datetimes[1]), ('review', datetimes[3]), ('done', datetimes[-1])
        ])
    ]

    wfh = WorkflowHistory(list_of_Ts, series=series, start_date=datetimes[0], end_date=datetimes[-1])
    df = wfh._get_data_frame()
    print(df.to_csv())

    assert len(df["todo"].array) == 6
    assert all([a == b for a, b in zip(df["todo"].array, [1, 0, 0, 0, 0, 0])])
    assert all([a == b for a, b in zip(df["inprogress"].array, [0, 1, 1, 0, 0, 0])])
    assert all([a == b for a, b in zip(df["review"].array, [0, 0, 0, 1, 1, 0])])
    assert all([a == b for a, b in zip(df["done"].array, [0, 0, 0, 0, 0, 1])])


def test_step_backwards():
    # dates array starts at 2021-03-15
    list_of_Ts = [
        Transitions(created_at, None, workflow_transitions=[
            ('todo', datetime.datetime(2021, 3, 1)), ('inprogress',datetimes[1]), ('review', datetimes[2]),
             ('inprogress',datetimes[3]), ('review', datetimes[4]), ('done', datetimes[-1])
        ])
    ]

    wfh = WorkflowHistory(list_of_Ts, series=series,  start_date=datetimes[0], end_date=datetimes[-1])
    df = wfh._get_data_frame()
    print(df.to_csv())

    assert len(df["todo"].array) == 6
    assert all([a == b for a, b in zip(df["todo"].array,       [1, 0, 0, 0, 0, 0])])
    # XXX This inprogress assertion fails because I have not implemented the handling of tracking
    #     backward and forward movement through the workflow yet.
    assert all([a == b for a, b in zip(df["inprogress"].array, [0, 1, 0, 1, 0, 0])])
    assert all([a == b for a, b in zip(df["review"].array,     [0, 0, 1, 0, 1, 0])])
    assert all([a == b for a, b in zip(df["done"].array,       [0, 0, 0, 0, 0, 1])])

def test_transitions_same_day_with_closed():
    list_of_Ts = [
        Transitions(created_at, datetimes[2], workflow_transitions=[
            ('todo', datetimes[1]), ('inprogress',datetimes[1]), ('review', datetimes[1])
        ])
    ]

    series1 = ['opened'] + series + ['closed']
    wfh = WorkflowHistory(list_of_Ts, series=series1, start_date=datetimes[0], end_date=datetimes[-1])
    df = wfh._get_data_frame()
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
        Transitions(datetimes[1], datetimes[1], workflow_transitions=[
            ('todo', datetimes[1]), ('inprogress',datetimes[1]), ('review', datetimes[1])
        ])
    ]

    series1 = ['opened'] + series + ['closed']

    wfh = WorkflowHistory(list_of_Ts, series=series1, start_date=datetimes[0], end_date=datetimes[-1])
    df = wfh._get_data_frame()
    print(df.to_csv())

    assert len(df["todo"].array) == 6
    assert all([a == b for a, b in zip(df["opened"].array, [0, 0, 0, 0, 0, 0])])
    assert all([a == b for a, b in zip(df["todo"].array, [0, 0, 0, 0, 0, 0])])
    assert all([a == b for a, b in zip(df["inprogress"].array, [0, 0, 0, 0, 0, 0])])
    assert all([a == b for a, b in zip(df["review"].array, [0, 0, 0, 0, 0, 0])])
    assert all([a == b for a, b in zip(df["done"].array, [0, 0, 0, 0, 0, 0])])
    assert all([a == b for a, b in zip(df["closed"].array, [0, 1, 1, 1, 1, 1])])

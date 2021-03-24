import pytest
import datetime
import pandas as pd

from random import randrange
from gl_analytics.metrics import daterange, WorkflowHistory

dates = [d for d in daterange(datetime.date(2021, 3, 15), datetime.date(2021, 3, 21))]

# series of workflow steps
series = ['todo','inprogress','review','done']

def test_daterange_exclusive():
    d1 = datetime.date(2021, 3, 1)
    d2 = datetime.date(2021, 3, 5)
    dates = [d for d in daterange(d1, d2)]
    assert dates[-1] == datetime.date(2021, 3, 4)


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

    wfh = WorkflowHistory(events, series=series, daterange=dates)
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

    wfh = WorkflowHistory(events, series=series, daterange=dates)
    df = wfh._get_data_frame()
    print(df.to_csv())

    assert len(df["todo"].array) == 6
    assert all([a == b for a, b in zip(df["todo"].array, [0, 0, 0, 0, 0, 0])])
    assert all([a == b for a, b in zip(df["inprogress"].array, [0, 0, 0, 0, 0, 0])])
    assert all([a == b for a, b in zip(df["review"].array, [0, 1, 1, 1, 1, 1])])
    assert all([a == b for a, b in zip(df["done"].array, [0, 0, 0, 0, 0, 0])])

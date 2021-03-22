import pytest
import datetime
import pandas as pd

from random import randrange
from gl_analytics.issues import daterange

def test_pandas_table():
    dates = [d for d in daterange(datetime.date(2021,3,15), datetime.date(2021,3,21))]
    data = {

        'Todo': [randrange(10) for _ in range(len(dates))],
        'InProgress': [randrange(10) for _ in range(len(dates))],
        'CodReview': [3, 5, None, 7, None, 2],
        'Done': [randrange(10) for _ in range(len(dates))]
    }

    df = pd.DataFrame(data, index=[str(d) for d in dates])
    filled = df.fillna(value=1, axis=1)

    print(df.to_csv())
    # ,Todo,InProgress,CodReview,Done
    # 2021-03-15,0,5,3.0,8
    # 2021-03-16,5,9,5.0,4
    # 2021-03-17,2,2,,0
    # 2021-03-18,7,6,7.0,1
    # 2021-03-19,9,8,,6
    # 2021-03-20,8,8,2.0,1
    assert True

def test_collect_values():
    dates = [d for d in daterange(datetime.date(2021,3,15), datetime.date(2021,3,21))]
    e1 = [
        ('add', 'todo', dates[0]),
        ('add', 'inprogress',dates[1]),
        ('remove', 'todo', dates[1]),
        ('add', 'done', dates[-1]),
        ('remove', 'inprogress',dates[-1])
    ]
    e2 = [
        ('add', 'todo', dates[1]),
        ('add', 'inprogress',dates[3]),
        ('remove', 'todo', dates[3]),
        ('add', 'review', dates[4]),
        ('remove', 'inprogress',dates[4])
    ]
    # series of workflow steps
    series = ['todo','inprogress','review','done']

    # empty 2D list
    series_buckets = [[0 for _ in dates] for _ in series]


    # assumptions: 2 events added on same day == last occuring event of the day

    # goal: calculate the range of each step, then fill in the series accordingly.
    for eventhistory in [e1, e2]:
        # store each label in series key, build start and end range by 'add' and 'remove'
        range_of_labels = {}
        for action, label, date in eventhistory:
            if action == 'add':
                range_of_labels[label] = (date,datetime.date.max)
            if action == 'remove':
                added, _ = range_of_labels[label]
                range_of_labels[label] = (added, date)
        # fill in the corresponding buckets
        for label, labelrange in range_of_labels.items():
            # find index of label in series
            series_index = series.index(label)
            # build daterange from label range
            start, end = labelrange
            # loop through dates until end of time window.
            # avoid looping to datetime.date.max =)
            for d1 in [d0 for d0 in daterange(start, end) if d0 <= dates[-1]]:
                # find date index and increment
                date_index = dates.index(d1)
                series_buckets[series_index][date_index] += 1

    # index = the daterange of the time window
    data = {k:v for k, v in zip(series, series_buckets)}
    df = pd.DataFrame(data, index=[str(d) for d in dates], columns=series)
    print(df.to_csv())

    assert False

import pytest
import datetime
import pandas as pd

from random import randrange
from gl_analytics.issues import daterange, workflow_series

dates = [d for d in daterange(datetime.date(2021, 3, 15), datetime.date(2021, 3, 21))]

# series of workflow steps
series = ['todo','inprogress','review','done']


def build_data_frame(events_list):
    # Build a dataframe from each event history and concat them together
    # store each label in series key, build start and end range by 'add' and 'remove'
        # empty 2D list
    # XXX Pandas must provide a way to build a series skipping indexes?
    # XXX try concatenating 2 data frames?
    series_buckets = [[0 for _ in dates] for _ in series]

    # goal: calculate the range of each step, then fill in the series accordingly.
    for eventhistory in events_list:
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
    indexes = [str(d) for d in dates]
    df = pd.DataFrame(data, index=indexes, columns=series)

    return df


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

    df = build_data_frame(events)
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

    df = build_data_frame(events)
    print(df.to_csv())

    assert len(df["todo"].array) == 6
    assert all([a == b for a, b in zip(df["todo"].array, [0, 0, 0, 0, 0, 0])])
    assert all([a == b for a, b in zip(df["inprogress"].array, [0, 0, 0, 0, 0, 0])])
    assert all([a == b for a, b in zip(df["review"].array, [0, 1, 1, 1, 1, 1])])
    assert all([a == b for a, b in zip(df["done"].array, [0, 0, 0, 0, 0, 0])])

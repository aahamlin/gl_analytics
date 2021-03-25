
import datetime
import pandas as pd

def daterange(start_date, end_date):
    for n in range(int((end_date - start_date).days)):
        yield start_date + datetime.timedelta(n)

def date_days_prior(date, days):
    return (date-datetime.timedelta(days))


DEFAULT_SERIES = ['open', 'workflow::Ready', 'workflow::In Progress', 'workflow::Code Review', 'closed']

class WorkflowHistory(object):

    def __init__(self, events, series=DEFAULT_SERIES, days=30, dates=None):

        if not dates:
            today = datetime.datetime.utcnow().date()
            self._daterange = list(daterange(date_days_prior(today, days), today))
        else:
            self._daterange = dates
        self._series = series
        self._events = events

    def print_csv(self):
        df = self._get_data_frame()
        print(df.to_csv())

    def _get_data_frame(self):
        # Build a dataframe from each event history and concat them together
        # store each label in series key, build start and end range by 'add' and 'remove'
        # empty 2D list
        series_buckets = [[0 for _ in self._daterange] for _ in self._series]

        # goal: calculate the range of each step, then fill in the series accordingly.
        for ev in self._events:
            # store each label in series key, build start and end range by 'add' and 'remove'
            range_of_labels = {}
            for action, label, date in ev:
                if action == 'add':
                    range_of_labels[label] = (date, datetime.date.max)
                if action == 'remove':
                    added, _ = range_of_labels[label]
                    range_of_labels[label] = (added, date)
            # fill in the corresponding buckets
            for label, labelrange in range_of_labels.items():
                # find index of label in series
                series_index = self._series.index(label)
                # build daterange from label range
                start, end = labelrange
                # loop through dates until end of time window.
                # avoid looping to datetime.date.max =)
                for d1 in [d for d in daterange(start, end) if d <= self._daterange[-1]]:
                    # find date index and increment
                    date_index = self._daterange.index(d1)
                    series_buckets[series_index][date_index] += 1

        # index = the daterange of the time window
        data = {k:v for k, v in zip(self._series, series_buckets)}
        indexes = [str(d) for d in self._daterange]
        df = pd.DataFrame(data, index=indexes, columns=self._series)

        return df

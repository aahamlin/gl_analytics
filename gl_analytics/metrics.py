
import datetime
import pandas as pd

def daterange(start_date, end_date):
    """Generate dates from start to end, exclusive.

    Given start=3-15, end=3-20, generator will generate dates from 3-15..3-19.
    """
    for n in range(int((end_date - start_date).days)):
        yield start_date + datetime.timedelta(n)

def start_date_for_time_window(end_date, days):
    """Return starting date of a time window including given end_date.
    For example, 5 day window from 2021-3-15 to 2021-3-19 (M-F)
    """
    if days<1:
        raise ValueError()
    return (end_date-datetime.timedelta(days-1))

def _resolve_date(date_or_datetime):
    if isinstance(date_or_datetime, datetime.datetime):
        return date_or_datetime.date()
    elif isinstance(date_or_datetime, datetime.date):
        return date_or_datetime

    raise ValueError(datetime.datetime)


DEFAULT_SERIES = ['opened', 'workflow::Ready', 'workflow::In Progress', 'workflow::Code Review', 'closed']

class MetricsError(Exception):
    pass

class WorkflowHistory(object):

    def __init__(self, events, series=DEFAULT_SERIES, days=30, end_date=datetime.datetime.utcnow().date(), start_date=None):

        # build include_dates
        if end_date and start_date:
            self._included_dates = self._calculate_include_dates(start_date, end_date)
        elif days:
            self._included_dates = self._calculate_include_dates(*self._data_range_from_days(end_date, days))
        else:
            raise MetricsError('Must specify days or data_range tuple')

        self._series = series
        self._events = events

    @property
    def included_dates(self):
        """The dates included in this report.
       """
        return self._included_dates

    @property
    def series(self):
        return self._series

    def _calculate_include_dates(self, start, end):
        # add 1 day
        end = (end + datetime.timedelta(1))
        return list(daterange(start, end))

    def _data_range_from_days(self, end, days):
        start = start_date_for_time_window(end, days)
        return (start, end)

    def to_csv(self, *args, **kwargs):
        df = self._get_data_frame()
        return df.to_csv(*args, **kwargs)

    def _get_data_frame(self):
        # Build a dataframe from each event history and concat them together
        # store each label in series key, build start and end range by 'add' and 'remove'
        # empty 2D list

        series_buckets = [[0 for _ in self.included_dates] for _ in self._series]

        # goal: calculate the range of each step, then fill in the series accordingly.
        for ev in self._events:
            # store each label in series key, build start and end range by 'add' and 'remove'
            range_of_labels = {}
            for action, label, dt in ev:
                if label not in self._series:
                    #print('skipping label', label)
                    continue

                date = _resolve_date(dt)
                if action == 'add':
                    range_of_labels[label] = (date, datetime.date.max)
                if action == 'remove':
                    try:
                        added, _ = range_of_labels[label]
                        range_of_labels[label] = (added, date)
                    except KeyError:
                        ## This is a data error caused by a typo in a scoped workflow label. When first
                        ## created the In Progress label was incorrectly written as 'workflow:In Progress'
                        ## with only a single colon (:). The label was corrected but at least one item in
                        ## GitLab `cwacc`` project now has a label "remove"" without corresponding "add".
                        #print(f'Error processing removal of {label} while processing {ev}')
                        pass
            # fill in the corresponding buckets
            for label, label_range in range_of_labels.items():
                try:
                    # find index of label in series
                    series_index = self._series.index(label)
                    # loop through dates included in the time window.
                    for d in self._labels_time_window(*label_range):
                        date_index = self.included_dates.index(d)
                        series_buckets[series_index][date_index] += 1
                except ValueError:
                    pass

        # index by dates within this report's time window
        data = {k:v for k, v in zip(self._series, series_buckets)}
        indexes = [str(d) for d in self.included_dates]
        df = pd.DataFrame(data, index=indexes, columns=self.series)

        return df

    def _labels_time_window(self, start, end):
         return [d for d in daterange(start, end) if d in self.included_dates]

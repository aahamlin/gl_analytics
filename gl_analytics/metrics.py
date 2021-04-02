import datetime
import pandas as pd

from itertools import starmap
from collections.abc import Sequence


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
    if days < 1:
        raise ValueError()

    return end_date - datetime.timedelta(days - 1)


def transition_to_date(label, datetime):
    return label, datetime.date()


class Transitions(Sequence):
    def __init__(self, opened, closed=None, workflow_transitions=[]):
        transitions = [("opened", opened)] + workflow_transitions
        if closed:
            transitions += [("closed", closed)]
        self._transitions = transitions

    def __getitem__(self, key):
        return self._transitions.__getitem__(key)

    def __len__(self):
        return self._transitions.__len__()


class MetricsError(Exception):
    pass


class CumulativeFlow(object):
    def __init__(
        self,
        transitions,
        labels=["opened", "closed"],
        days=30,
        end_date=None,
        start_date=None,
    ):

        if start_date and not isinstance(start_date, datetime.date):
            raise ValueError("start_date must be datetime.date")

        if end_date and not isinstance(end_date, datetime.date):
            raise ValueError("end_date must be datetime.date")

        if days < 1:
            raise ValueError("days must include at least 1 day")

        if hasattr(start_date, "date"):
            start_date = start_date.date()

        if hasattr(end_date, "date"):
            end_date = end_date.date()

        if isinstance(end_date, datetime.date) and isinstance(
            start_date, datetime.date
        ):
            self._included_dates = self._calculate_include_dates(start_date, end_date)
        else:
            end_date = (
                end_date
                if end_date
                else datetime.datetime.now(tz=datetime.timezone.utc).date()
            )
            self._included_dates = self._calculate_include_dates(
                *self._data_range_from_days(end_date, days)
            )

        self._labels = labels
        # Cumulativeflow only records changes per day, so normalize all transition to dates
        self._transitions = list([starmap(transition_to_date, t) for t in transitions])
        self._matrix = self._build_matrix()

    @property
    def included_dates(self):
        """The dates included in this report."""
        return self._included_dates

    @property
    def labels(self):
        return self._labels

    def _calculate_include_dates(self, start, end):
        # add 1 day because generator excludes end, as matches Python generators expectations
        end = end + datetime.timedelta(1)
        return list(daterange(start, end))

    def _data_range_from_days(self, end, days):
        start = start_date_for_time_window(end, days)
        return (start, end)

    def to_csv(self, *args, **kwargs):
        df = self._get_data_frame()
        return df.to_csv(*args, **kwargs)

    def _get_data_frame(self):
        """Build a DataFrame for processing (metrics, plotting, etc)."""
        # index by dates within this report's time window
        data = {k: v for k, v in zip(self._labels, self._matrix)}
        indexes = [str(d) for d in self.included_dates]
        df = pd.DataFrame(data, index=indexes, columns=self.labels)

        return df

    def _build_matrix(self):
        # process self._transitions, e.g. a list of lists containing transitions of each issue
        # each transition is a tuple, label and datetime
        # datetimes will be normalized to dates for simple per day CFD
        # 'opened' is always the first transition, even if its not in the time window
        # when all transitions for an issue occur on the same day, record the last transition

        matrix = [[0 for _ in self.included_dates] for _ in self._labels]

        for wf_transitions in self._transitions:
            # takes all transitions into account, in particular opened and closed datetimes
            transitions = [(s, t) for s, t in wf_transitions]

            tx_labels, dates = list(zip(*transitions))

            opened_date = dates[0]

            # Same day event: add last series label and time only
            if all([d == opened_date for d in dates]):
                self._add(matrix, tx_labels[-1], opened_date, datetime.date.max)
                continue

            # Multiple day events: add each series label with start and end times
            for idx, label in enumerate(tx_labels):
                start_date = dates[idx]
                try:
                    end_date = dates[idx + 1]
                except IndexError:
                    end_date = datetime.date.max

                if label in self.labels:
                    self._add(matrix, label, start_date, end_date)

        return matrix

    def _add(self, matrix, tx_label, start_date, end_date):
        # add transitions that are in our label collection
        series_index = self.labels.index(tx_label)
        # loop through dates included in the time window.
        for d in self._labels_time_window(start_date, end_date):
            date_index = self.included_dates.index(d)
            matrix[series_index][date_index] += 1

    def _labels_time_window(self, start, end):
        inside_start = (
            start if start > self.included_dates[0] else self.included_dates[0]
        )
        inside_end = (
            end
            if end <= self.included_dates[-1]
            else (self.included_dates[-1] + datetime.timedelta(1))
        )
        return list(daterange(inside_start, inside_end))

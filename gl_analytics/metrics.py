import datetime
import pandas as pd

from itertools import starmap
from collections.abc import Sequence
from operator import itemgetter


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


class Stages(Sequence):
    """List holding all stages of a single Issue through a workflow.

    Each list item is a tuple (label, start_datetime, end_datetime).
    """
    def __init__(self, opened, closed=None, label_events=[]):
        # open ends at next transition start or datetime.max
        if len(label_events)>0:
            opened_end = label_events[0][1]
        elif closed:
            opened_end = closed
        else:
            opened_end = datetime.datetime.max


        transitions = [("opened", opened, opened_end)]

        if len(label_events) > 0 and closed:
            last_label_event = label_events.pop()
            label_events.append((last_label_event[0], last_label_event[1], closed))

        transitions += label_events

        if closed:
            transitions += [("closed", closed, datetime.datetime.max)]

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
        stage_transitions,
        stages=["opened", "closed"],
        days=30,
        end_date=None,
        start_date=None,
    ):
        """Groups stages of workflow by date.

        args:
        stage_transitions list of Stages objects

        kwargs:
        stages list of stages to include in the report
        days number of days to include in the report, default 30
        end_date provide a specific end date, default today()
        start_date provide a specific start date, default 30 days before end_date (inclusive)
        """

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

        self._labels = stages

        # Cumulativeflow only records changes per day, so normalize all transition to dates
        def transition_to_date(label, dt_start, dt_end):
            return label, dt_start.date(), dt_end.date()

        self._transitions = list(
            map(list, [starmap(transition_to_date, t) for t in stage_transitions])
        )
        self._matrix = self._build_matrix()

    @property
    def included_dates(self):
        """The dates included in this report."""
        return self._included_dates

    @property
    def stages(self):
        return self._labels

    def get_data_frame(self):
        """Build a DataFrame for processing (metrics, plotting, etc)."""
        # index by dates within this report's time window
        data = {k: v for k, v in zip(self._labels, self._matrix)}
        indexes = [str(d) for d in self.included_dates]
        df = pd.DataFrame(data, index=indexes, columns=self.stages)

        return df

    def _calculate_include_dates(self, start, end):
        # add 1 day because generator excludes end, as matches Python generators expectations
        end = end + datetime.timedelta(1)
        return list(daterange(start, end))

    def _data_range_from_days(self, end, days):
        start = start_date_for_time_window(end, days)
        return (start, end)

    def _build_matrix(self):
        """Process workflow stages for all issues e.g. a list of lists containing
        list of transitions within a list of issues.

        Each transition is a tuple, label and datetime
        Datetimes are normalized to dates for simple per day counts

        'opened' is always the first transition, even if its not in the time window.

        When all transitions for an issue occur on the same day, record the last transition
        that is included in the desired set of labels.
        """


        # XXX this section is still a mess :(
        #  this should be rewritten to build up a pandas dataframe from series of our stages,
        #  grouped by labels and ggregated by days.
        matrix = [[0 for _ in self.included_dates] for _ in self.stages]

        labelgetter = itemgetter(0)
        openedgetter = itemgetter(1)
        endedgetter = itemgetter(2)

        for issue_stages in self._transitions:
            filtered_stages = [
                tx for tx in issue_stages if labelgetter(tx) in self.stages
            ]

            last_stage = filtered_stages.pop()
            if openedgetter(last_stage) == endedgetter(last_stage):
                # the last included state must span 1 day or it will not be displayed
                last_stage = (
                    labelgetter(last_stage),
                    openedgetter(last_stage),
                    (endedgetter(last_stage) + datetime.timedelta(1)),
                )

            if not all(
                    [
                        openedgetter(elm) == openedgetter(issue_stages[0])
                        for elm in issue_stages
                    ]
            ):
                for stage in filtered_stages:
                    self._add(matrix, *stage)

            self._add(matrix, *last_stage)

        return matrix

    def _add(self, matrix, tx_label, start_date, end_date):
        """Add counts of stages that are within our set of stages to display and within our report time window.
        """
        series_index = self.stages.index(tx_label)
        for d in self._labels_time_window(start_date, end_date):
            date_index = self.included_dates.index(d)
            matrix[series_index][date_index] += 1

    def _labels_time_window(self, start, end):
        inside_start = max(start, self.included_dates[0])
        inside_end = min(end, (self.included_dates[-1] + datetime.timedelta(1)))
        return list(daterange(inside_start, inside_end))

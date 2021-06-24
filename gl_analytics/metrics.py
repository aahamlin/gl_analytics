import datetime
import pandas as pd
import numpy as np

from itertools import starmap
from collections.abc import Sequence
from functools import partial
from operator import itemgetter

from .func import foldl


class IssueStageTransitions:
    """Creates a DataFrame holding all stages of a single Issue through a workflow.

    Each row is indexed by "datetime".
    """

    def __init__(self, issue):

        # XXX This could definitely be cleaned up by constructing the list of dicts more directly

        # print("Issue:", issue)
        issue_id = issue.issue_id
        opened = issue.opened_at
        closed = issue.closed_at
        index_name = "datetime"
        id_name = "id"
        type_name = "type"
        project_name = "project"

        opened = issue.opened_at
        closed = issue.closed_at
        label_events = issue.label_events

        issue_id = issue.issue_id
        project_id = issue.project_id
        issue_type = issue.issue_type

        # open ends at next transition start or datetime.max
        if len(label_events) > 0:
            opened_end = label_events[0][1]
        elif closed:
            opened_end = closed
        else:
            opened_end = None

        def to_record(label, start, end):
            yield dict(zip([index_name, project_name, id_name, type_name, label], [start, project_id, issue_id, issue_type, 1]))

            if end:
                yield dict(zip([index_name, project_name, id_name, type_name, label], [end, project_id, issue_id, issue_type, 0]))

        transitions = []

        transitions.extend(to_record("opened", opened, opened_end))

        if len(label_events) > 0 and closed:
            last_label_event = label_events.pop()
            label_events.append((last_label_event[0], last_label_event[1], closed))

        for event in label_events:
            transitions.extend(to_record(*event))

        if closed:
            transitions.extend(to_record("closed", closed, None))

        records = {}
        for t in transitions:
            dt = t[index_name]
            if dt not in records:
                records[dt] = {}
            records[dt].update(t)

        # from_records requires a list
        values = list(records.values())
        self._transitions = pd.DataFrame.from_records(values, index=[index_name])

    @property
    def data(self):
        return self._transitions

    def __str__(self):
        return str(self._transitions)


class CumulativeFlow(object):
    def __init__(
        self,
        transitions,
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
        self._index_daterange = _calculate_date_range(days, start_date, end_date)
        self._labels = stages

        cats = pd.Series(
            pd.Categorical(self._labels, categories=self._labels, ordered=True)
        )

        df = pd.DataFrame([], index=self._index_daterange, columns=cats)
        self._data = foldl(combine_by_totals, df, [a.data for a in transitions])

    @property
    def included_dates(self):
        """The dates included in this report."""
        # return self._included_dates
        return self._index_daterange

    def get_data_frame(self):
        """Build a DataFrame for processing (metrics, plotting, etc).
        """
        return self._data


def _calculate_date_range(days, start_date, end_date):
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

    pd_date_range = partial(pd.date_range, freq="D", name="datetime", tz="UTC")

    if end_date and start_date:
        return pd_date_range(
            start=start_date,
            end=end_date
        )
    elif start_date:
        return pd_date_range(
            start=start_date,
            periods=days
        )

    end_date = (
        end_date
        if end_date
        else datetime.datetime.now(datetime.timezone.utc).date()
    )
    return pd_date_range(
        end=end_date,
        periods=days
    )


def dt_index_shift(r):
    """If last row sum == 0 return index of row else None
    """
    return (
        r.iloc[-1].name
        if not r.dropna().empty and 0 == r.iloc[-1].sum()
        else None
    )

def combine_by_totals(d1, d2):
    d2 = d2.reindex(columns=d1.columns)
    shift_dt_index = d2.groupby(pd.Grouper(freq="1D")).apply(dt_index_shift)
    dt_to_shift = [dt for dt in shift_dt_index if dt is not pd.NaT]
    for dt in dt_to_shift:
        # use numpy datetime64 object to sort these "raw" indices
        dt64 = dt.to_numpy()
        new_index_dt64 = (dt.normalize() + pd.Timedelta("1D")).to_numpy()
        old_indices_dt64 = np.where(d2.index.values == dt64)[0]
        for old_index in old_indices_dt64:
            d2.index.values[old_index] = new_index_dt64

    d2 = d2.resample("1D").last()
    d2 = d2.fillna(method="ffill")
    d2 = d2.reindex(d1.index, method="ffill")
    return d1.combine(d2, np.add, fill_value=0)


class LeadCycleTimes():
    """Calculations for a scatter plot diagram.
    """
    def __init__(
        self,
            transitions,
            stage=None,
            days=30,
            end_date=None,
            start_date=None
    ):
        """Generate lead & cycle time values from issue transitions.
        """

        # XXX not sure how to use the data range
        self._index_daterange = _calculate_date_range(days, start_date, end_date)
        self._labels = ["datetime", "type", "lead", "cycle"]

        df = pd.DataFrame([], columns=self._labels)
        self._data = foldl(partial(combine_by_cycles, stage), df, [a.data for a in transitions])

    def get_data_frame(self):
        # print("Data", self._data)
        return self._data


def combine_by_cycles(cycle_label, d1, d2):
    # only uses opened, closed, and In Progress.
    d2 = d2.filter(["opened", cycle_label, "closed", "type"])
    d2 = d2.replace(to_replace=0, value=np.nan)
    d2 = d2.dropna(how="all")
    d2 = d2.reset_index()
    # d2.columns = ["datetime", "lead", "cycle", "closed"]
    wip_date = d2["datetime"].shift()
    open_date = wip_date if cycle_label not in d2 else d2["datetime"].shift(periods=2)

    d2["cycle"] = d2["datetime"]-wip_date
    d2["lead"] = d2["datetime"]-open_date

    d2["open"] = open_date
    d2["wip"] = wip_date

    d2 = d2.filter(d1.columns.values).dropna(how="any")
    # d2 = d2.drop("closed", axis=1, errors="ignore")
    # print("\nnew data\n", d2)
    return d1.append(d2)

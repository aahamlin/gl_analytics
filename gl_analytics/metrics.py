import datetime
import pandas as pd
import numpy as np

# from itertools import starmap
# from collections.abc import Sequence
from functools import partial, reduce

# from operator import itemgetter


def build_transitions(issues):
    """Create a list of transitions from a list of issues."""
    return [IssueStageTransitions(i) for i in issues]


class IssueStageTransitions:
    """Creates a DataFrame holding all stages of a single Issue through a workflow.

    Each row is indexed by "datetime".

    Example:
                               project  id type  opened  ready  in progress  done
    datetime
    2021-03-14 12:00:00+00:00        2   1  Bug     1.0    NaN          NaN   NaN
    2021-03-14 15:15:00+00:00        2   1  Bug     0.0    1.0          NaN   NaN
    2021-03-15 10:00:00+00:00        2   1  Bug     NaN    0.0          1.0   NaN
    2021-03-16 10:00:00+00:00        2   1  Bug     NaN    NaN          0.0   1.0
    """

    def __init__(self, issue):

        # XXX This could definitely be cleaned up by constructing the list of dicts more directly
        #      see the new LeadCycleTimes class, building records in a simple loop. Load them all
        #      into a DataFrame at once.
        # XXX This can be pushed down into the class itself as well

        # print("Issue:", issue)
        issue_id = issue.issue_id
        opened = issue.opened_at
        closed = issue.closed_at
        index_name = "datetime"
        id_name = "id"
        type_name = "type"
        project_name = "project"

        history = issue.history

        issue_id = issue.issue_id
        project_id = issue.project_id
        issue_type = issue.issue_type

        def to_record(label, start, end):
            yield dict(
                zip(
                    [index_name, project_name, id_name, type_name, label], [start, project_id, issue_id, issue_type, 1]
                )
            )

            if end:
                yield dict(
                    zip(
                        [index_name, project_name, id_name, type_name, label],
                        [end, project_id, issue_id, issue_type, 0],
                    )
                )

        transitions = []

        for event in history:
            transitions.extend(to_record(*event))

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
        *args,
        **kwargs,
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

        cats = pd.Series(pd.Categorical(self._labels, categories=self._labels, ordered=True))

        df = pd.DataFrame([], index=self._index_daterange, columns=cats)
        self._data = reduce(combine_by_totals, [a.data for a in transitions], df)

    @property
    def included_dates(self):
        """The dates included in this report."""
        # return self._included_dates
        return self._index_daterange

    def get_data_frame(self):
        """Build a DataFrame for processing (metrics, plotting, etc)."""
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
        return pd_date_range(start=start_date, end=end_date)
    elif start_date:
        return pd_date_range(start=start_date, periods=days)

    end_date = end_date if end_date else datetime.datetime.now(datetime.timezone.utc).date()
    return pd_date_range(end=end_date, periods=days)


def dt_index_shift(r):
    """If last row sum == 0 return index of row else None"""
    return r.iloc[-1].name if not r.dropna().empty and 0 == r.iloc[-1].sum() else None


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


class LeadCycleTimes:
    """Calculations for a scatter plot diagram."""

    def __init__(self, issues, stage=None, *args, **kwargs):
        """Generate lead & cycle time values from issue histories."""

        # we could generate a business day range by passing freq='B' into date_range calculation.

        # flatten the array of issues and histories to an array of records(dictionaries)
        # build dataframe from records
        # calculate the lead and cycle times
        records = self._build_records_from_issues(issues, stage)
        df = pd.DataFrame.from_records(records)

        df["lead"] = [
            x + 1
            for x in np.busday_count(
                df["opened"].values.astype("datetime64[D]"), df["last_closed"].values.astype("datetime64[D]")
            )
        ]
        df["cycle"] = [
            x + 1
            for x in np.busday_count(
                df[stage].values.astype("datetime64[D]"), df["closed"].values.astype("datetime64[D]")
            )
        ]
        self._data = df

    def get_data_frame(self):
        # print("Data", self._data)
        return self._data

    def _build_records_from_issues(self, issues, stage):
        records = []
        for issue in issues:
            rec = {"id": issue.issue_id, "project": issue.project_id, "type": issue.issue_type}
            update_args = {}
            reopened_count = 0
            # XXX see latest edits, when items are not labeled w/ inProgress, we can still see that
            #     there was activity when later labels (CodeReview) were applied, and merge requests
            #     were referenced. (Possibly assignees, but that seems super unreliable!)
            for k, v1, _ in issue.history:
                # for cycletime: process from 1st stage to 1st closed event
                # filter events to opened, 1st "stage" and closed values
                if k == "opened" or ((k == stage or k == "closed") and k not in update_args):
                    update_args[k] = v1
                # for leadtime: from opened to last closed event
                if k == "closed":
                    update_args["last_closed"] = v1
                # count occurrences of reopened
                if k == "reopened":
                    reopened_count += 1

            # if 1st stage is not present or newer than 1st closed, use opened instead
            if stage not in update_args or update_args[stage] > update_args["closed"]:
                update_args[stage] = update_args["opened"]

            # include reopened count
            update_args["reopened"] = reopened_count

            rec.update(update_args)
            # print(f"built record {rec}")
            records.append(rec)

        return records

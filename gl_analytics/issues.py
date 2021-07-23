""" Issues module interacts with a backend system API, e.g. GitLab.
"""
# import json
import logging
from typing import Sequence
import requests

from abc import ABC, abstractmethod
from cachecontrol import CacheControlAdapter
from cachecontrol.caches.file_cache import FileCache
from cachecontrol.heuristics import ExpiresAfter
from collections.abc import Sequence

# from datetime import datetime
from dateutil import parser as date_parser
from operator import itemgetter
from urllib.parse import urlencode, urljoin

from functools import reduce

_log = logging.getLogger(__name__)


class Session(ABC):  # pragma: no cover
    @abstractmethod
    def get(self):
        raise NotImplementedError()


class GitlabSession(Session):
    def __init__(self, base_url, access_token=None):
        if not base_url.endswith("/"):
            base_url += "/"
        self._base_url = base_url
        self._access_token = access_token

        sess = requests.Session()
        sess.headers.update({"PRIVATE-TOKEN": self._access_token})

        # XXX filecache does NOT clean up old files, it will grow infiinitely
        # add some logic to remove old files
        cache = FileCache(".webcache")
        adapter = CacheControlAdapter(cache=cache, heuristic=ExpiresAfter(hours=1))
        sess.mount("https://", adapter)

        self.session = sess

    def get(self, path):
        """Calls request.get(url) appending relative path to session baseurl.

        args:
        path - path relative to base_url or absolute url starting with scheme

        raises:
        ValueError - when path starts with "/"
        """
        if path.startswith("/"):
            raise ValueError
        url = urljoin(self.baseurl, path)

        return self.session.get(url)

    @property
    def baseurl(self):
        return self._base_url


class AbstractRepository(ABC):  # pragma: no cover
    @abstractmethod
    def list(self):
        raise NotImplementedError()


class AbstractResolver(ABC):  # pragma: no cover
    @property
    @abstractmethod
    def session(self):
        raise NotImplementedError()

    @abstractmethod
    def build_request_url(self, project_id, issue_id):
        raise NotImplementedError()

    @abstractmethod
    def process(self, issue, res):
        raise NotImplementedError()

    def resolve(self, issue):
        url = self.build_request_url(issue.project_id, issue.issue_id)
        res = self.fetch(url)
        self.process(issue, res)

    def fetch(self, url):
        r = self.session.get(url)
        r.raise_for_status()
        payload = r.json()
        return payload


class HistoryResolver(AbstractResolver):
    """Resolver that builds an ordered list of historical events."""

    def process(self, issue, res):
        """Sort the events by start time. Add store on HistoryMixin.history"""
        events = self.process_history(res)
        issue.history.add_events(events)

    @abstractmethod
    def process_history(self, res):  # pragma: no cover
        raise NotImplementedError()


class GitlabIssuesRepository(AbstractRepository):
    """This is specifically a GitLab Issue repository. Current GitLab version is 13.11.0-pre."""

    def __init__(self, session, group=None, milestone=None, state=None, resolvers=[]):
        """Initialize a repository.

        Required:
        session: session object
        group: group name or id
        milestone: milestone name or id
        state: issue state filter, e.g. 'closed'

        Optional:
        resolvers: Specify classes to use to resolve additional fields.
        """
        if not group or not milestone:
            raise ValueError("Requires group and milestone")

        self._session = session
        self._group = group
        self._milestone = milestone
        self._state = state
        self._resolvers = resolvers

        self._url = self._build_request_url()

    @property
    def url(self):
        return self._url

    def list(self):
        """Return issues from the repository."""
        return [x for x in self._page_results()]

    # XXX modify this to return a tuple of url and list of params
    def _build_request_url(self):
        url = "groups/{0}/issues".format(self._group)

        # XXX rebuild using sorted tuples for caching effectiveness
        # see also https://cachecontrol.readthedocs.io/en/latest/tips.html#query-string-params
        params = {"pagination": "keyset", "scope": "all", "milestone": self._milestone}

        if self._state:
            params["state"] = self._state

        _log.debug("built url: %s", url)
        _log.debug("built params: %s", params)
        return "{0}?{1}".format(url, urlencode(params))

    def _page_results(self):
        """Generator of issues from pages of results."""

        # starting request
        url = self.url

        hasMore = True
        while hasMore:
            # XXX modify this to use url and list of params, e.g. requests.get(url, params=...)
            # make request
            r1 = self._session.get(url)
            r1.raise_for_status()

            # extract the issues from the response body
            payload = r1.json()
            # count = len(payload)
            # print(f'processing {count} items');
            for item in payload:
                issue = self._build_issue_from(item)
                self._resolve_fields(issue)
                yield issue

            if r1.links and "next" in r1.links:
                # setup next page request
                next_link = r1.links["next"]
                url = next_link["url"]
                # print("next page:", url, file=sys.stderr)
            else:
                hasMore = False

    def _build_issue_from(self, item):
        # print('creating Issue from item', json.dumps(item))
        issue_id = item["iid"]
        project_id = item["project_id"]
        opened_at = date_parser.parse(item["created_at"])
        issue_type = self._find_type_label(item)
        issue = Issue(issue_id, project_id, opened_at, issue_type=issue_type)
        return issue

    def _find_type_label(self, item):
        type_labels = [t.lstrip("type::") for t in item.get("labels", []) if t.startswith("type::")][:1]
        return type_labels[0] if type_labels else None

    def _resolve_fields(self, issue):
        for resolver_cls in self._resolvers:
            resolver = resolver_cls(self._session)
            resolver.resolve(issue)


class GitlabScopedLabelResolver(HistoryResolver):
    """Add workflow events to an item

    Workflow events are an array of tuples. But should probably be changed to an object.
    """

    def __init__(self, session, scope="workflow", *args, **kwargs):
        """Initialize the resolve with your GitlabSession object.

        Optionally, provide the scoped label, the start of a scoped label up to the double-colon (::).
        """
        self._session = session
        self._scope = scope + "::"
        super().__init__(*args, **kwargs)

    @property
    def session(self):
        return self._session

    def build_request_url(self, project_id, issue_id):
        # /api/v4/projects/8279995/issues/191/resource_label_events
        url = "projects/{0}/issues/{1}/resource_label_events".format(project_id, issue_id)
        return url

    def process_history(self, label_events):
        """Process transitions through workflow steps.

        Produces a standard record of events so that the `metrics` module can easily
        process them.

        opened => step1 => step2 => ... => closed

        List of tuples containing "step" and "datetime", e.g. ('opened', 2021-02-09T16:59:37.783Z')

        The data structure will contain enough information to build transitions. Transitions are
        different than GitLab's adding and removing of Labels on a date. Therefore, we will use the
        created_at date to signify the transition point of time.

        Assumes:
        - GitLab orders events by date (oldest first)
        - Scoped Labels exist until next label or the issue is closed. (see Limitations)

        Limitations:
        - Does not deal with a user removing a scoped label entirely (without either adding another
          label or closing the issue).
        """

        def accumulate_start_end_datetimes(acc, event):
            try:
                action, label, datetimestr = self._get_workflow_steps(event)
                dt = date_parser.parse(datetimestr)

                if action == "add":
                    acc.append((label, dt, None))
                elif action == "remove":
                    for i, x in enumerate(acc):
                        if x[0] == label and x[2] is None:
                            acc[i] = (x[0], x[1], dt)
                            break

            except TypeError:
                pass

            return acc

        return reduce(accumulate_start_end_datetimes, label_events, [])

    def _get_workflow_steps(self, event):
        """Returns a tuple containing: action, step_name, date

        Return None for non-qualifying label events.
        """
        if not event["label"]["name"].startswith(self._scope):
            return None

        step_name = event["label"]["name"].lstrip(self._scope)
        action_name = event["action"]
        action_date = event["created_at"]

        return action_name, step_name, action_date


class GitLabStateEventResolver(HistoryResolver):
    def __init__(self, session, *args, **kwargs):
        self._session = session
        super().__init__(*args, **kwargs)

    @property
    def session(self):
        return self._session

    def build_request_url(self, project_id, issue_id):
        url = "projects/{0}/issues/{1}/resource_state_events".format(project_id, issue_id)
        return url

    def process_history(self, res):
        def accumulate_state_events(acc, event):
            state, datetimestr = event["state"], event["created_at"]
            dt = date_parser.parse(datetimestr)
            acc.append((state, dt, None))
            return acc

        return reduce(accumulate_state_events, res, [])


DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


class Issue(object):
    def __init__(
        self,
        issue_id,
        project_id,
        opened_at,
        issue_type=None,
    ):
        """initializes an issue.

        label_events: array of tuples containing label:str, created_at:datetime
        """
        self._issue_id = issue_id
        self._project_id = project_id
        self._issue_type = issue_type
        self._history = History(opened_at)

    @property
    def issue_id(self):
        return self._issue_id

    @property
    def project_id(self):
        return self._project_id

    @property
    def opened_at(self):
        """Quick accessor for the 'opened' datetime.

        This is suitable for simple filters without having to do a lookup in the history.
        """
        return self._history[0][1]

    @property
    def closed_at(self):
        """Quick accessor for the 'closed' datetime.

        This is suitable for simple filters without having to do a lookup in the history.
        """
        end = self._history[-1]
        return end[1] if end[0] == "closed" else None

    @property
    def issue_type(self):
        return self._issue_type

    @property
    def history(self):
        return self._history

    def __str__(self):  # pragma: no cover
        return f"Issue(id:{self.issue_id}, " f"p:{self.project_id}, " f"t:{self.issue_type} " f"h:{self.history})"


class History(Sequence):
    def __init__(self, opened_at):
        self._history = []
        self._history.append(("opened", opened_at, None))

    def add_events(self, events):
        ordered_events = sorted(self._history + events, key=itemgetter(1))
        assert ordered_events[0][0] == "opened"
        ordered_events = self._fill_enddate(ordered_events)
        self._history = ordered_events

    def _fill_enddate(self, events):
        """Each previous event ends when the next event starts, if end is not already supplied."""
        cur = 1
        max = len(events)
        while cur < max:
            prev = events[cur - 1]
            if prev[2] is None:
                events[cur - 1] = (prev[0], prev[1], events[cur][1])
            cur += 1
        return events

    def __getitem__(self, key):
        return self._history.__getitem__(key)

    def __len__(self):
        return self._history.__len__()

    def __str__(self):
        return f"{[(x[0], x[1].strftime(DATETIME_FORMAT)) for x in self._history]}"

""" Issues module interacts with a backend system API, e.g. GitLab.
"""
import sys
import requests

from datetime import datetime
from dateutil import parser as date_parser
from urllib.parse import urlencode, urljoin

from .func import foldl

class IssuesError(Exception):
    pass


class Session(object):
    def get(self):
        raise IssuesError("Not Implemented")


class GitlabSession(Session):
    def __init__(self, base_url, access_token=None):
        if not base_url.endswith("/"):
            base_url += "/"
        self._base_url = base_url
        self._access_token = access_token

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
        headers = {"PRIVATE-TOKEN": self._access_token}
        return requests.get(url, headers=headers)

    @property
    def baseurl(self):
        return self._base_url


class AbstractRepository(object):
    def list(self):
        raise IssuesError()


class AbstractResolver(object):
    def resolve(self):
        raise IssuesError()


class GitlabIssuesRepository(AbstractRepository):
    """This is specifically a GitLab Issue repository. Current GitLab version is 13.11.0-pre.
    """
    def __init__(self, session, group=None, milestone=None, resolvers=[]):
        """Initialize a repository.

        Required:
        session: session object
        group: group name or id
        milestone: milestone name or id

        Optional:
        resolvers: Specify classes to use to resolve additional fields.
        """
        if not group or not milestone:
            raise ValueError("Requires group and milestone")

        self._session = session
        self._group = group
        self._milestone = milestone
        self._resolvers = resolvers

        self._url = self._build_request_url()

    @property
    def url(self):
        return self._url

    def list(self):
        """Return issues from the repository."""
        return [x for x in self._page_results()]

    def _build_request_url(self):
        url = "groups/{0}/issues".format(self._group)
        params = {
            "pagination": "keyset",
            "scope": "all",
            "milestone": self._milestone}
        #print("built url:", url, file=sys.stderr)
        #print("built params:", params, file=sys.stderr)
        return "{0}?{1}".format(url, urlencode(params))

    def _page_results(self):
        """Generator of issues from pages of results."""

        # starting request
        url = self.url

        hasMore = True
        while hasMore:
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
                #print("next page:", url, file=sys.stderr)
            else:
                hasMore = False


    def _build_issue_from(self, item):
        # print('creating Issue from item', json.dumps(item))
        issue_id = item["iid"]
        project_id = item["project_id"]
        opened_at = date_parser.parse(item["created_at"])
        closed_at_str = item.get("closed_at")
        closed_at = date_parser.parse(closed_at_str) if closed_at_str else None
        label_events = None
        issue = Issue(
            issue_id, project_id, opened_at, closed_at=closed_at
        )
        return issue


    def _resolve_fields(self, issue):
        for resolver_cls in self._resolvers:
            resolver = resolver_cls(self._session)
            resolver.resolve(issue)


class GitlabScopedLabelResolver(AbstractResolver):
    """Add workflow events to an item

    Workflow events are an array of tuples. But should probably be changed to an object.
    """

    def __init__(self, session, scope="workflow"):
        """Initialize the resolve with your GitlabSession object.

        Optionally, provide the scoped label, the start of a scoped label up to the double-colon (::).
        """
        self._session = session
        self._scope = scope + "::"

    def resolve(self, issue):
        url = self._build_request_url(issue.project_id, issue.issue_id)
        res = self._fetch_results(url)

        # XXX Adding a named to a dictionary is problematic, refactor this better.
        #return {"_scoped_labels": self._find_scoped_labels(item, res)}
        issue.label_events = self._find_scoped_labels(res)

    def _build_request_url(self, project_id, issue_id):
        # /api/v4/projects/8279995/issues/191/resource_label_events
        url = "projects/{0}/issues/{1}/resource_label_events".format(
            project_id, issue_id
        )
        return url

    def _fetch_results(self, url):
        r = self._session.get(url)
        r.raise_for_status()

        payload = r.json()
        return payload

    def _find_scoped_labels(self, label_events):
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
                    acc.append((label, dt, datetime.max))
                elif action == "remove":
                    for i, x in enumerate(acc):
                        if x[0] == label and x[2] == datetime.max:
                            acc[i] = (x[0], x[1], dt)
                            break

            except TypeError:
                pass

            return acc

        return foldl(accumulate_start_end_datetimes, [], label_events)

    def _get_workflow_steps(self, event):
        """Returns a tuple containing: action, step_name, date

        Return None for non-qualifying label events.
        """
        if not event["label"]["name"].startswith(self._scope):
            return None

        step_name = event["label"]["name"]
        action_name = event["action"]
        action_date = event["created_at"]

        return action_name, step_name, action_date


class Issue(object):
    def __init__(
        self, issue_id, project_id, opened_at, closed_at=None, label_events=None
    ):
        """initializes an issue.

        label_events: array of tuples containing label:str, created_at:datetime
        """
        self._issue_id = issue_id
        self._project_id = project_id
        self._opened_at = opened_at
        self._closed_at = closed_at
        self._label_events = label_events

    @property
    def issue_id(self):
        return self._issue_id

    @property
    def project_id(self):
        return self._project_id

    @property
    def opened_at(self):
        return self._opened_at

    @property
    def closed_at(self):
        return self._closed_at

    @property
    def label_events(self):
        return self._label_events

    @label_events.setter
    def label_events(self, label_events):
        self._label_events = label_events

    def __str__(self): # pragma: no cover
        return f"Issue(id:{self.issue_id}, p:{self.project_id}, o:{self.opened_at}, c:{self.closed_at}, e:{self.label_events})"

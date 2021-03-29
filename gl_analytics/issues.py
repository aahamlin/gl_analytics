""" Issues module interacts with a backend system API, e.g. GitLab.
"""
import sys
import requests

from dateutil import parser as date_parser
from urllib.parse import urlencode

GITLAB_URL_BASE = "https://gitlab.com/api/v4"


class IssuesError(Exception):
    pass


class Session(object):
    def get(self):
        raise IssuesError("Not Implemented")


class GitlabSession(Session):
    def __init__(self, access_token=None):
        self._access_token = access_token

    def get(self, url):
        headers = {"PRIVATE-TOKEN": self._access_token}
        return requests.get(url, headers=headers)


class AbstractRepository(object):
    def list(self):
        raise IssuesError()


class AbstractResolver(object):
    def resolve(self):
        raise IssuesError()


class GitlabIssuesRepository(AbstractRepository):
    """This is specifically a GitLab Issue repository. Current GitLab version is 13.11.0-pre.

    If ever we needed it, an AbstractRepository could be extracted.
    """

    # XXX Create a Workflow Resolver to fetch workflow states for each issue. Replaces the Gitlabissueworkflowrepository.
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
        url = "{0}/groups/{1}/issues".format(GITLAB_URL_BASE, self._group)
        params = {"pagination": "keyset", "milestone": self._milestone}
        print("built url:", url, file=sys.stderr)
        print("built params:", params, file=sys.stderr)
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
                item = self._resolve_fields(item)
                yield issue_from(item)

            if r1.links and "next" in r1.links:
                # setup next page request
                next_link = r1.links["next"]
                url = next_link["url"]
                print("next page:", url, file=sys.stderr)
            else:
                hasMore = False

    def _resolve_fields(self, item):
        for resolver_cls in self._resolvers:
            resolver = resolver_cls(self._session)
            item.update(resolver.resolve(item))
        return item


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

    def resolve(self, item):
        url = self._build_request_url(item["project_id"], item["iid"])
        res = self._fetch_results(url)

        # XXX Adding a named to a dictionary is problematic, refactor this better.
        return {"_scoped_labels": self._find_scoped_labels(item, res)}

    def _build_request_url(self, project_id, issue_id):
        # /api/v4/projects/8279995/issues/191/resource_label_events
        url = "{0}/projects/{1}/issues/{2}/resource_label_events".format(
            GITLAB_URL_BASE, project_id, issue_id
        )
        return url

    def _fetch_results(self, url):
        r = self._session.get(url)
        r.raise_for_status()

        payload = r.json()
        return payload

    def _find_scoped_labels(self, item, payload):
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

        # TODO Implement the handling of label removal, resolving the limitation noted above.
        events = []

        for label_event in payload:
            try:
                action_name, step_name, action_datetime = self._get_workflow_step(
                    label_event
                )
                if action_name == "add":
                    events.append((step_name, action_datetime))
            except TypeError:
                # non-qualifying label event returned None
                pass

        return events

    def _get_workflow_step(self, event):
        """Returns a tuple containing: action, step_name, date

        Return None for non-qualifying label events.
        """
        if not event["label"]["name"].startswith(self._scope):
            return None

        step_name = event["label"]["name"]
        action_name = event["action"]
        action_date = event["created_at"]

        return action_name, step_name, action_date


def issue_from(item):
    # print('creating Issue from item', json.dumps(item))
    issue_id = item["iid"]
    project_id = item["project_id"]
    opened_at = date_parser.parse(item["created_at"])
    closed_at_str = item.get("closed_at")
    closed_at = date_parser.parse(closed_at_str) if closed_at_str else None
    label_events = None
    # XXX ScopeLabelResolver added this entry to the dictionary. Find a better way
    if "_scoped_labels" in item:
        label_events = list(
            map(lambda x: (x[0], date_parser.parse(x[1])), item["_scoped_labels"])
        )

    issue = Issue(
        issue_id, project_id, opened_at, closed_at=closed_at, label_events=label_events
    )
    return issue


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

    def __eq__(self, other):
        return (
            self.issue_id,
            self.project_id,
            self.opened_at,
            self.closed_at,
            self.label_events,
        ) == (
            other.issue_id,
            other.project_id,
            other.opened_at,
            other.closed_at,
            other.label_events,
        )

    def __str__(self):
        return f"Issue(id:{self.issue_id}, p:{self.project_id}, o:{self.opened_at}, c:{self.closed_at}, e:{self.label_events})"

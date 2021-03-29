"""Gather statistics out of GitLab for generating of reports.

"""
import os
from dotenv import load_dotenv
from .issues import GitlabSession, GitlabIssuesRepository, GitlabScopedLabelResolver
from .metrics import Transitions, CumulativeFlow

#
#  TODO:
#    1. Take parameters to build workflow steps from scoped labels, i.e. --scope=workflow \
#      --scope-include='Ready, In Progress, Code Review'
#    2. Query GitLab to validate scoped labels exist (no typos) and retrieve their IDs, then use label
#      IDs, instead of strings, when processing resource_label_events.
#
#    3. Figure out how to provide scope to the GitlabWorkflowResolver class __init__ function.
#      3a. Either, figure a way to pass arguments down the heirarchy
#      3b. Subclass GitlabWorkflowResolver with specific scopes.
#


DEFAULT_SERIES = [
    "opened",
    "workflow::Designing",
    "workflow::Needs Design Approval",
    "workflow::Ready",
    "workflow::In Progress",
    "workflow::Code Review",
    "closed",
]


def build_transitions(issues):
    """Create a list of transitions from a list of issues."""
    return [
        Transitions(i.opened_at, i.closed_at, workflow_transitions=i.label_events)
        for i in issues
    ]


def main(access_token=None, group=None, milestone=None, days=30):
    session = GitlabSession(access_token=access_token)
    repository = GitlabIssuesRepository(
        session,
        group="gozynta",
        milestone="mb_v1.3",
        resolvers=[GitlabScopedLabelResolver],
    )
    issues = repository.list()
    # grab all the transitions from the elements in the list
    transitions = build_transitions(issues)
    wfh = CumulativeFlow(transitions, days=days, series=DEFAULT_SERIES)
    print(wfh.to_csv())


if __name__ == "__main__":
    load_dotenv()
    main(access_token=os.getenv("TOKEN"), group="gozynta", milestone="mb_v1.3", days=30)

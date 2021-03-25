"""Gather statistics out of GitLab for generating of reports.

"""
import os
import sys
from dotenv import load_dotenv
from .issues import GitlabSession, GitlabIssuesRepository, GitlabScopedLabelResolver
from .metrics import Transitions, CumulativeFlow
from .report import CsvReport

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


def main(access_token=None, group=None, milestone=None, days=30, file=sys.stdout):
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
    cf = CumulativeFlow(transitions, labels=DEFAULT_SERIES, days=days)
    report = CsvReport(cf.get_data_frame(), file=file)
    report.export()


if __name__ == "__main__":
    load_dotenv()
    main(access_token=os.getenv("TOKEN"), group="gozynta", milestone="mb_v1.3")

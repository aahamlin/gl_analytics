"""Gather statistics out of GitLab for generating of reports.

"""
import argparse
import os
import sys

from dotenv import dotenv_values

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

CONFIG = {
    "GITLAB_BASE_URL": "https://gitlab.com/api/v4",
    "GITLAB_GROUP": "Gozynta",
    **dotenv_values(".env"),
    **os.environ,
}


def create_parser():

    parser = argparse.ArgumentParser(
        prog = "gl-analytics",
        description="Analyze data from GitLab projects"
    )

    parser.add_argument(
        "-m",
        "--milestone",
        metavar="milestone",
        nargs="?",
        default=None,
        help="Milestone id, e.g. mb_v1.3"
    )

    parser.add_argument(
        "-d",
        "--days",
        metavar="days",
        type=int,
        nargs="?",
        default=30,
        help="Number of days to analyze, default 30"
    )

    # parser.add_argument(
    #     "-l",
    #     "--label",
    #     metavar="label",
    #     nargs="+",
    #     default=DEFAULT_SERIES
    # )

    parser.add_argument(
        "-g",
        "--group",
        metavar="group",
        nargs="?",
        default=CONFIG.get("GITLAB_GROUP"),
        help="GitLab Group name, default %s"%CONFIG.get("GITLAB_GROUP")
    )

    parser.add_argument(
        "-o",
        "--outfile",
        metavar="Filepath",
        nargs="?",
        default=None,
        help="File to output, default stdout"
    )

    return parser

def build_transitions(issues):
    """Create a list of transitions from a list of issues."""
    return [
        Transitions(i.opened_at, i.closed_at, workflow_transitions=i.label_events)
        for i in issues
    ]


def main(args=None):
    #access_token=config.get("TOKEN"), group="gozynta", milestone="mb_v1.3"
    #access_token=None, group=None, milestone=None, days=30, file=sys.stdout
    parser = create_parser()
    prog_args = parser.parse_args(args)

    token = CONFIG["TOKEN"]
    baseurl = CONFIG["GITLAB_BASE_URL"]

    session = GitlabSession(baseurl, access_token=token)
    repository = GitlabIssuesRepository(
        session,
        group=prog_args.group,
        milestone=prog_args.milestone,
        resolvers=[GitlabScopedLabelResolver],
    )
    issues = repository.list()
    # grab all the transitions from the elements in the list
    transitions = build_transitions(issues)
    cf = CumulativeFlow(transitions, labels=DEFAULT_SERIES, days=prog_args.days)
    report = CsvReport(cf.get_data_frame(), file=(prog_args.outfile or sys.stdout))
    report.export()


if __name__ == "__main__":
    main(args=sys.argv[1:])

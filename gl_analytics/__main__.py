"""Gather statistics out of GitLab for generating of reports.

"""
import argparse
import logging
import os
import sys

import datetime

from .issues import GitlabSession, GitlabIssuesRepository, GitlabScopedLabelResolver
from .metrics import IssueStageTransitions, CumulativeFlow
from .report import CsvReport, PlotReport
from .utils import timer
from .config import load_config

logging.basicConfig()
logging.getLogger().setLevel(logging.INFO)
# logging.getLogger('gl_analytics.utils').setLevel(logging.DEBUG)

DEFAULT_SERIES = [
    "opened",
    "In Progress",
    "Code Review",
    "closed",
]

def create_parser(config):

    parser = argparse.ArgumentParser(
        prog = "gl-analytics",
        description="Analyze data from GitLab projects"
    )

    parser.add_argument(
        "-m",
        "--milestone",
        metavar="milestone",
        nargs="?",
        default="#started",
        help="Milestone id, e.g. mb_v1.3 or #started"
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
        default=config.get("GITLAB_GROUP"),
        help="GitLab Group name, default %s"%config.get("GITLAB_GROUP")
    )

    parser.add_argument(
        "-r",
        "--report",
        choices=["csv", "plot"],
        default="csv",
        help="Specify output report type"
    )

    parser.add_argument(
        "-o",
        "--outfile",
        metavar="Filepath",
        nargs="?",
        default=None,
        help="File to output or default"
    )

    return parser

def build_transitions(issues):
    """Create a list of transitions from a list of issues.
    """
    return [
        IssueStageTransitions(i.opened_at, i.closed_at, label_events=i.label_events)
        for i in issues
    ]


class Main:

    def __init__(self, args=None):
        self.config = load_config()

        parser = create_parser(self.config)
        self.prog_args = parser.parse_args(args)

        timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.supported_reports = {
            'csv': (CsvReport, sys.stdout),
            'plot': (PlotReport, f"cfd_{timestamp_str}.png"),
        }

    def run(self):
        token = self.config["TOKEN"]
        baseurl = self.config["GITLAB_BASE_URL"]
        outfile = self.prog_args.outfile
        days = self.prog_args.days

        session = GitlabSession(baseurl, access_token=token)
        repository = GitlabIssuesRepository(
            session,
            group=self.prog_args.group,
            milestone=self.prog_args.milestone,
            resolvers=[GitlabScopedLabelResolver],
        )

        log = logging.getLogger("main")

        with timer("Listing issues"):
            issues = repository.list()

        # grab all the transitions from the elements in the list
        with timer("Building data"):
            transitions = build_transitions(issues)

        with timer("Aggregations"):
            cf = CumulativeFlow(transitions, stages=DEFAULT_SERIES, days=days)

        report_cls, default_file = self.supported_reports[self.prog_args.report]
        report = report_cls(
            cf.get_data_frame(),
            file=(outfile or default_file),
            title=self.prog_args.milestone
        )

        with timer("Export"):
            report.export()

        if outfile:
            print(f"Created '{outfile}'.")

if __name__ == "__main__":  # pragma: no cover
    Main(args=sys.argv[1:]).run()

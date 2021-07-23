"""Gather statistics out of GitLab for generating of reports.

"""
import argparse
import logging

import sys

import datetime

from collections import namedtuple
from types import SimpleNamespace

from .config import load_config
from .issues import GitlabSession, GitlabIssuesRepository, GitlabScopedLabelResolver, GitLabStateEventResolver
from .metrics import CumulativeFlow, LeadCycleTimes, build_transitions
from .report import CsvReport, PlotReport
from .utils import timer


logging.getLogger().setLevel(logging.INFO)
# logging.getLogger('gl_analytics.utils').setLevel(logging.DEBUG)
# logging.getLogger("gl_analytics.issues").setLevel(logging.DEBUG)

DEFAULT_SERIES = [
    "opened",
    "In Progress",
    "Code Review",
    "closed",
]

DEFAULT_PIVOT = "In Progress"


def create_parser(config):

    parser = argparse.ArgumentParser(prog="gl-analytics", description="Analyze data from GitLab projects")

    common_parser = argparse.ArgumentParser(add_help=False)

    common_parser.add_argument(
        "-m",
        "--milestone",
        metavar="milestone",
        nargs="?",
        default="#started",
        help="Milestone id, e.g. mb_v1.3 or #started",
    )

    # parser.add_argument(
    #     "-l",
    #     "--label",
    #     metavar="label",
    #     nargs="+",
    #     default=DEFAULT_SERIES
    # )

    common_parser.add_argument(
        "-g",
        "--group",
        metavar="group",
        nargs="?",
        default=config.get("GITLAB_GROUP"),
        help="GitLab Group name, default %s" % config.get("GITLAB_GROUP"),
    )

    common_parser.add_argument(
        "-r", "--report", choices=["csv", "plot"], default="csv", help="Specify output report type"
    )

    common_parser.add_argument(
        "-o", "--outfile", metavar="Filepath", nargs="?", default=None, help="File to output or default"
    )

    subparsers = parser.add_subparsers(
        title="Available commands", description="Commands to analyze GitLab Issue metrics.", dest="subparser_name"
    )

    cumulative_flow_parser = subparsers.add_parser(
        "cumulativeflow",
        aliases=["cf", "flow"],
        parents=[common_parser],
        help="Generate cumulative flow data in the given report format.",
    )

    cumulative_flow_parser.add_argument(
        "-d", "--days", metavar="days", type=int, nargs="?", default=30, help="Number of days to analyze, default 30"
    )

    cumulative_flow_parser.set_defaults(func=cumulative_flow_factory, extra_args=dict(stages=DEFAULT_SERIES))

    cycletime_parser = subparsers.add_parser(
        "cycletime",
        aliases=["cy"],
        parents=[common_parser],
        help="Generate cycletime data in the given report format.",
    )
    cycletime_parser.set_defaults(func=cycle_time_factory, extra_args=dict(stage=DEFAULT_PIVOT))

    return parser


def cumulative_flow_factory(session, args):
    repository = GitlabIssuesRepository(
        session,
        group=args.group,
        milestone=args.milestone,
        resolvers=[GitlabScopedLabelResolver, GitLabStateEventResolver],
    )
    return repository, cumulative_flow_cls_factory


def cumulative_flow_cls_factory(issues, *args, **kwargs):
    transitions = build_transitions(issues)
    return CumulativeFlow(transitions, *args, **kwargs)


def cycle_time_factory(session, args):
    repository = GitlabIssuesRepository(
        session,
        group=args.group,
        milestone=args.milestone,
        state="closed",
        resolvers=[GitlabScopedLabelResolver, GitLabStateEventResolver],
    )
    return repository, cycle_time_cls_factory


def cycle_time_cls_factory(issues, *args, **kwargs):
    # TODO: eliminate the need for transitions here
    return LeadCycleTimes(issues, *args, **kwargs)


class Main:
    def __init__(self, args=None):
        self.config = load_config()

        parser = create_parser(self.config)
        self.prog_args = parser.parse_args(args)

        timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.supported_reports = {
            "csv": (CsvReport, sys.stdout),
            "plot": (PlotReport, f"cfd_{timestamp_str}.png"),
        }

    def run(self):
        token = self.config["TOKEN"]
        baseurl = self.config["GITLAB_BASE_URL"]
        session = GitlabSession(baseurl, access_token=token)
        QueryArgs = namedtuple("QueryArgs", ["group", "milestone"])
        query_args = QueryArgs(group=self.prog_args.group, milestone=self.prog_args.milestone)
        ReportArgs = namedtuple("ReportArgs", ["report", "outfile"])
        report_args = ReportArgs(report=self.prog_args.report, outfile=self.prog_args.outfile)

        repository, aggregator_cls = self.prog_args.func(session, query_args)

        # create a simple dictionary with the rest of the argparser arguments to pass to the aggregator class
        aggregator_args = {
            k: v
            for k, v in self.prog_args.__dict__.items()
            if k not in query_args._asdict() and k not in report_args._asdict() and k != "extra_args"
        }
        aggregator_args.update(self.prog_args.extra_args)
        # print(f"built args for aggregator class {aggregator_cls} {aggregator_args}")

        log = logging.getLogger("main")

        with timer("Listing issues"):
            issues = repository.list()
            log.info(f"Retrieved {len(issues)} issues for {query_args.milestone}")

        with timer("Aggregations"):
            result = aggregator_cls(issues, **aggregator_args)

        report_cls, default_file = self.supported_reports[report_args.report]
        report = report_cls(
            result.get_data_frame(), file=(report_args.outfile or default_file), title=query_args.milestone
        )

        with timer("Export"):
            report.export()

        if report_args.outfile:
            print(f"Created '{report_args.outfile}'.")


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig()
    Main(args=sys.argv[1:]).run()

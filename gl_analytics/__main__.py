"""Gather statistics out of GitLab for generating of reports.

"""
import argparse
import logging
import sys

from .config import load_config
from .command import CumulativeFlowCommand, CycleTimeCommand

logging.basicConfig()
logging.getLogger().setLevel(logging.INFO)
# logging.getLogger('gl_analytics.utils').setLevel(logging.DEBUG)
# logging.getLogger("gl_analytics.issues").setLevel(logging.DEBUG)


# TODO: other organizations/projects may use different workflow labels
DEFAULT_STAGES = [
    "opened",
    "In Progress",
    "Code Review",
    "closed",
]

DEFAULT_WIP = "In Progress"


log = logging.getLogger("main")


config = load_config()


def create_parser():

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
        title="Available commands", description="Commands to analyze GitLab Issue metrics.", dest="command"
    )
    subparsers.required = True

    cumulative_flow_parser = subparsers.add_parser(
        "cumulativeflow",
        aliases=["cf", "flow"],
        parents=[common_parser],
        help="Generate cumulative flow data in the given report format.",
    )

    cumulative_flow_parser.add_argument(
        "-d", "--days", metavar="days", type=int, nargs="?", default=30, help="Number of days to analyze, default 30"
    )

    cumulative_flow_parser.set_defaults(func=CumulativeFlowCommand, extra_args=dict(stages=DEFAULT_STAGES))

    cycletime_parser = subparsers.add_parser(
        "cycletime",
        aliases=["cy"],
        parents=[common_parser],
        help="Generate cycletime data in the given report format.",
    )
    cycletime_parser.set_defaults(func=CycleTimeCommand, extra_args=dict(wip=DEFAULT_WIP, stages=DEFAULT_STAGES))

    return parser


def main(args):
    parser = create_parser()
    prog_args = parser.parse_args(args)
    cmd = prog_args.func(config, prog_args)
    cmd.execute()


if __name__ == "__main__":  # pragma: no cover
    main(args=sys.argv[1:])

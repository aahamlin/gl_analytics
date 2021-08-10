import datetime
import logging
import sys
from abc import ABC, abstractmethod
from collections import namedtuple

from .issues import (
    GitlabSession,
    GitLabClosedByMergeRequestResolver,
    GitlabIssuesRepository,
    GitlabScopedLabelResolver,
    GitLabStateEventResolver,
)
from .metrics import CumulativeFlow, LeadCycleTimes, build_transitions
from .report import CsvReport, PlotReport
from .utils import timer

_log = logging.getLogger(__name__)


class AbstractCommand(ABC):  # pragma: no cover
    def __init__(self, config, prog_args, *args, **kwargs):
        self.config = config
        self.prog_args = prog_args

    @abstractmethod
    def execute(self):
        raise NotImplementedError()


class AggregationCommand(AbstractCommand):
    def __init__(self, config, prog_args, *args, **kwargs):
        super().__init__(config, prog_args, *args, **kwargs)

        timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        # XXX these report classes should be associated with the aggregation classes themselves
        #      and the "format" is the only thing necessary to pass from CLI args, csv file or plot?
        self.supported_reports = {
            "csv": (CsvReport, sys.stdout),
            "plot": (PlotReport, f"cfd_{timestamp_str}.png"),
        }

    def build_repo(self):
        token = self.config["TOKEN"]
        baseurl = self.config["GITLAB_BASE_URL"]
        session = GitlabSession(baseurl, access_token=token)

        # XXX currently the repo only supports a group level query
        repository = GitlabIssuesRepository(session, group=self.prog_args.group, resolvers=self.resolvers)
        return repository

    @abstractmethod
    def list(self, repository):  # pragma: no cover
        raise NotImplementedError()

    @property
    @abstractmethod
    def resolvers(self):  # pragma: no cover
        raise NotImplementedError()

    def execute(self):

        ReportArgs = namedtuple("ReportArgs", ["report", "outfile"])
        report_args = ReportArgs(report=self.prog_args.report, outfile=self.prog_args.outfile)

        # create a simple dictionary with the rest of the argparser arguments to pass to the aggregator class
        # stripping out args that are expressly used for other purposes.
        aggregator_args = {
            k: v
            for k, v in self.prog_args.__dict__.items()
            if k not in report_args._asdict() and k not in ["command", "func", "group", "milestone", "extra_args"]
        }
        aggregator_args.update(self.prog_args.extra_args)

        repository = self.build_repo()

        # XXX refactor this now that repository.list() takes kwargs, rethink the design
        with timer("Listing issues"):
            issues = self.list(repository)

        _log.info(f"Retrieved {len(issues)} issues")

        with timer("Aggregations"):
            result = self.aggregate_results(issues, **aggregator_args)

        report_cls, default_file = self.supported_reports[report_args.report]
        report = report_cls(
            result.get_data_frame(), file=(report_args.outfile or default_file), title=self.prog_args.milestone
        )

        with timer("Export"):
            report.export()

        if report_args.outfile:
            print(f"Created '{report_args.outfile}'.")

    @abstractmethod
    def aggregate_results(self, issues, *args, **kwargs):
        raise NotImplementedError()  # pragma: no cover


class CumulativeFlowCommand(AggregationCommand):
    def __init__(self, config, prog_args, *args, **kwargs):
        super().__init__(config, prog_args, *args, **kwargs)

    def list(self, repository):
        return repository.list(milestone=self.prog_args.milestone)

    @property
    def resolvers(self):
        return [GitlabScopedLabelResolver, GitLabStateEventResolver]

    def aggregate_results(self, issues, *args, **kwargs):
        transitions = build_transitions(issues)
        return CumulativeFlow(transitions, *args, **kwargs)


class CycleTimeCommand(AggregationCommand):
    def __init__(self, config, prog_args, *args, **kwargs):
        super().__init__(config, prog_args, *args, **kwargs)

    def list(self, repository):
        return repository.list(milestone=self.prog_args.milestone, state="closed")

    @property
    def resolvers(self):
        return [GitlabScopedLabelResolver, GitLabStateEventResolver, GitLabClosedByMergeRequestResolver]

    def aggregate_results(self, issues, *args, **kwargs):
        return LeadCycleTimes(issues, *args, **kwargs)


import os
from dotenv import load_dotenv
from itertools import chain
from .issues import GitlabSession, find_issues
from .metrics import WorkflowHistory


def main():
    load_dotenv()
    ACCESS_TOKEN = os.getenv('TOKEN')
    session = GitlabSession(access_token=ACCESS_TOKEN)

    # XXX work on these interfaces:
    #  - single step to retrieve issues with label events (see GitlabIssuesRepository)
    #  - encapsulate event collection from issues
    issues = find_issues(session, group="gozynta", milestone="mb_v1.3")
    events = [e for e in chain([i.workflow for i in issues])]

    wfh = WorkflowHistory(events, days=60)
    print(wfh.to_csv())

    # XXX use WorkflowHistory to generate cumulative flow diagram image, hopefully! =D


if __name__ == "__main__":
    main()


import os
from dotenv import load_dotenv
from itertools import chain
from .issues import GitlabSession, GitlabIssuesRepository, GitlabWorkflowResolver
from .metrics import WorkflowHistory


def main(repository=None):
    if not repository:
        raise TypeError()

    issues = repository.list()
    events = [e for e in chain([i.workflow for i in issues])]

    wfh = WorkflowHistory(events, days=60)
    print(wfh.to_csv())

if __name__ == "__main__":
    load_dotenv()
    ACCESS_TOKEN = os.getenv('TOKEN')
    session = GitlabSession(access_token=ACCESS_TOKEN)
    issueRepo = GitlabIssuesRepository(session, group="gozynta", milestone="mb_v1.3", resolvers=[GitlabWorkflowResolver])
    main(session=session, repository=issueRepo)

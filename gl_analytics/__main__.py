
import os
from dotenv import load_dotenv
from .issues import GitlabSession, GitlabIssuesRepository, GitlabWorkflowResolver
from .metrics import build_transitions, WorkflowHistory

def main(repository=None):
    if not repository:
        raise TypeError()

    issues = repository.list()
    # grab all the transitions from the elements in the list
    transitions = build_transitions(issues)
    wfh = WorkflowHistory(transitions, days=60)
    print(wfh.to_csv())

if __name__ == "__main__":
    load_dotenv()
    ACCESS_TOKEN = os.getenv('TOKEN')
    session = GitlabSession(access_token=ACCESS_TOKEN)
    issueRepo = GitlabIssuesRepository(session, group="gozynta", milestone="mb_v1.3", resolvers=[GitlabWorkflowResolver])
    main(session=session, repository=issueRepo)

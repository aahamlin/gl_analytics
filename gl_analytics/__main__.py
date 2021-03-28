
import os
from dotenv import load_dotenv
from .issues import GitlabSession, GitlabIssuesRepository, GitlabWorkflowResolver
from .metrics import Transitions, CumulativeFlow


def build_transitions(issues):
    """Create a list of transitions from a list of issues.
    """
    return [Transitions(i.opened_at, i.closed_at, workflow_transitions=i.label_events) for i in issues]

def main(repository=None):
    if not repository:
        raise ValueError()

    issues = repository.list()
    # grab all the transitions from the elements in the list
    transitions = build_transitions(issues)
    wfh = CumulativeFlow(transitions, days=60)
    print(wfh.to_csv())

if __name__ == "__main__":
    load_dotenv()
    ACCESS_TOKEN = os.getenv('TOKEN')
    session = GitlabSession(access_token=ACCESS_TOKEN)
    issueRepo = GitlabIssuesRepository(session, group="gozynta", milestone="mb_v1.3", resolvers=[GitlabWorkflowResolver])
    main(session=session, repository=issueRepo)

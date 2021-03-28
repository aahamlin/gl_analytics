
import os
from dotenv import load_dotenv
from .issues import GitlabSession, GitlabIssuesRepository, GitlabWorkflowResolver
from .metrics import Transitions, CumulativeFlow


def build_transitions(issues):
    """Create a list of transitions from a list of issues.
    """
    return [Transitions(i.opened_at, i.closed_at, workflow_transitions=i.label_events) for i in issues]

def main(access_token=None, group=None, milestone=None, days=30):
    session = GitlabSession(access_token=access_token)
    repository = GitlabIssuesRepository(session, group="gozynta", milestone="mb_v1.3", resolvers=[GitlabWorkflowResolver])
    issues = repository.list()
    # grab all the transitions from the elements in the list
    transitions = build_transitions(issues)
    wfh = CumulativeFlow(transitions, days=days)
    print(wfh.to_csv())

if __name__ == "__main__":
    load_dotenv()
    main(access_token=os.getenv('TOKEN'), group="gozynta", milestone="mb_v1.3", days=30)

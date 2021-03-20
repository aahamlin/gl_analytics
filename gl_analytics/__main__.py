
import os
from dotenv import load_dotenv
from .issues import GitlabSession, GitlabIssuesRepository, WorkflowHistogram


if __name__ == "__main__":
    load_dotenv()
    ACCESS_TOKEN = os.getenv('TOKEN')
    session = GitlabSession(access_token=ACCESS_TOKEN)
    repo = GitlabIssuesRepository(session, group="gozynta", milestone="mb_v1.3")
    issues = repo.list()

    histogram = WorkflowHistogram(session, issues=issues)
    for issue in histogram.issues:
        print(str(issue))


import os
from dotenv import load_dotenv
from .issues import GitlabSession, get_issues


if __name__ == "__main__":
    load_dotenv()
    ACCESS_TOKEN = os.getenv('TOKEN')
    session = GitlabSession(access_token=ACCESS_TOKEN)
    issues = get_issues(session, group="gozynta", milestone="mb_v1.3")

    print([str(ix) for ix in issues])
    # XXX use WorkflowHistory to print the results

    # XXX use WorkflowHistory to generate cumulative flow diagram image, hopefully! =D


import os
from dotenv import load_dotenv
from .issues import GitlabSession, Repository


if __name__ == "__main__":
    load_dotenv()
    ACCESS_TOKEN = os.getenv('TOKEN')
    session = GitlabSession(access_token=ACCESS_TOKEN)
    repo = Repository(session=session, group="gozynta", milestone="mb_v1.3")
    json = repo.list()
    print(json)

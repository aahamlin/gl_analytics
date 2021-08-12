import os
from dotenv import dotenv_values


def load_config():
    config = {
        "GITLAB_BASE_URL": "https://gitlab.com/api/v4",
        "GITLAB_GROUP": "Gozynta",
        **dotenv_values(".env"),
        **os.environ,
    }

    return config

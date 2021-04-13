import pytest
import pandas as pd
import datetime

from pathlib import Path

from gl_analytics.issues import GitlabSession
from gl_analytics.metrics import daterange

from .data import TestData, to_bytes, to_link_header


class TestDateTimes:
    mar_01_2021 = datetime.datetime(2021, 3, 1)
    mar_10_2021 = datetime.datetime(2021, 3, 10)
    mar_15_2021 = datetime.datetime(2021, 3, 15)
    mar_16_2021 = datetime.datetime(2021, 3, 16)
    mar_17_2021 = datetime.datetime(2021, 3, 17)
    mar_18_2021 = datetime.datetime(2021, 3, 18)
    mar_19_2021 = datetime.datetime(2021, 3, 19)
    mar_20_2021 = datetime.datetime(2021, 3, 20)
    created_at = mar_10_2021
    start = mar_15_2021
    end = mar_19_2021


@pytest.fixture
def datetimes():
    return TestDateTimes()


@pytest.fixture
def stages():
    return ["todo", "inprogress", "review", "done"]


@pytest.fixture
def df():
    """Return a dataframe with 5 rows and 3 columns: todo, inprogress, done."""
    dates = [
        d for d in daterange(datetime.date(2021, 3, 15), datetime.date(2021, 3, 20))
    ]
    data = {
        "todo": [3, 2, 1, 0, 0],
        "inprogress": [0, 1, 2, 3, 1],
        "done": [0, 0, 0, 1, 2],
    }
    df = pd.DataFrame(data, index=dates, columns=data.keys())
    return df


@pytest.fixture
def filepath_csv(tmp_path):
    tmp_filepath = tmp_path.joinpath("t.csv")
    return tmp_filepath


@pytest.fixture
def filepath_png(tmp_path):
    tmp_filepath = tmp_path.joinpath("t.png")
    return tmp_filepath


@pytest.fixture
def filepath_dotenv(tmp_path):
    tmp_filepath = tmp_path.joinpath(".env")
    with tmp_filepath.open(mode="w", encoding="utf-8") as f:
        f.write("TOKEN=test_token")

    tmp_filepath.link_to(".env")
    print(f"created tmp_filepath {tmp_filepath}")
    link = Path(".env")
    yield link
    link.unlink()


@pytest.fixture
def session():
    session = GitlabSession("https://gitlab.com/api/v4/", access_token="x")
    return session


@pytest.fixture
def get_issues(requests_mock):
    requests_mock.get(
        "https://gitlab.com/api/v4/groups/gozynta/issues",
        body=to_bytes(TestData.issues.iid2.body),
    )


@pytest.fixture
def get_paged_issues(requests_mock):
    requests_mock.get(
        "https://gitlab.com/api/v4/groups/gozynta/issues",
        body=to_bytes(TestData.issues.iid2.body),
        headers=to_link_header(TestData.issues.iid2.headers.link),
    )

    requests_mock.get(
        "https://gitlab.com/api/v4/groups/gozynta/issues?id=gozynta&milestone=mb_v1.3&page=2&pagination=keyset",
        body=to_bytes(TestData.issues.iid3.body),
    )


@pytest.fixture
def get_workflow_labels(requests_mock):
    requests_mock.get(
        "https://gitlab.com/api/v4/projects/8273019/issues/2/resource_label_events",
        body=to_bytes(TestData.resource_label_events[0]),
    )


@pytest.fixture
def get_mixed_labels(requests_mock):
    requests_mock.get(
        "https://gitlab.com/api/v4/projects/8273019/issues/2/resource_label_events",
        body=to_bytes(TestData.resource_label_events[1]),
    )

import pytest
import pandas as pd
import datetime

from gl_analytics.issues import GitlabSession

from .data import TestData, to_bytes, to_link_header


@pytest.fixture
def stages():
    return ["opened", "todo", "inprogress", "review", "done", "closed"]


@pytest.fixture
def df():
    """Return a dataframe with 5 rows and 3 columns: todo, inprogress, done."""
    data = {
        "todo": [3, 2, 1, 0, 0],
        "inprogress": [0, 1, 2, 3, 1],
        "done": [0, 0, 0, 1, 2],
    }
    df = pd.DataFrame(
        data,
        index=pd.date_range(start="2021-03-15", end="2021-03-19", freq="D", name="datetime", tz="UTC"),
        columns=data.keys(),
    )
    return df


@pytest.fixture
def fake_timestamp():
    """2021 Apr 1, 12:00 AM"""
    return datetime.datetime(2021, 4, 1, tzinfo=datetime.timezone.utc)


@pytest.fixture
def patch_datetime_now(monkeypatch, fake_timestamp):
    """Patch the datetime.datetime.now function.

    Important note: Callers **must** match the usage exactly:
    ```
      import datetime
      datetime.datetime.now()
    ```
    """

    class mydatetime:
        @classmethod
        def now(cls, *args, **kwargs):
            return fake_timestamp

    monkeypatch.setattr(datetime, "datetime", mydatetime)


@pytest.fixture
def filepath_csv(tmp_path):
    tmp_filepath = tmp_path.joinpath("t.csv")
    return tmp_filepath


@pytest.fixture
def filepath_png(tmp_path):
    tmp_filepath = tmp_path.joinpath("t.png")
    return tmp_filepath


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
def get_closed_issues(requests_mock):
    requests_mock.get(
        "https://gitlab.com/api/v4/groups/gozynta/issues",
        body=to_bytes(TestData.issues.closed.body),
    )


@pytest.fixture
def get_paged_issues(requests_mock):
    requests_mock.get(
        "https://gitlab.com/api/v4/groups/gozynta/issues?milestone=mb_v1.3&pagination=keyset&scope=all",
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
        body=to_bytes(TestData.resource_label_events.stages),
    )
    requests_mock.get(
        "https://gitlab.com/api/v4/projects/8273019/issues/2/resource_state_events",
        body=to_bytes(TestData.resource_state_events.empty),
    )


@pytest.fixture
def get_closed_workflow_labels(requests_mock):
    requests_mock.get(
        "https://gitlab.com/api/v4/projects/8273019/issues/2/resource_label_events",
        body=to_bytes(TestData.resource_label_events.closed),
    )
    requests_mock.get(
        "https://gitlab.com/api/v4/projects/8273019/issues/2/resource_state_events",
        body=to_bytes(TestData.resource_state_events.closed),
    )


@pytest.fixture
def get_empty_resource_events(requests_mock):
    requests_mock.get(
        "https://gitlab.com/api/v4/projects/8273019/issues/2/resource_label_events",
        body=to_bytes("[]"),
    )
    requests_mock.get(
        "https://gitlab.com/api/v4/projects/8273019/issues/2/resource_state_events",
        body=to_bytes("[]]"),
    )


@pytest.fixture
def get_closed_by_empty(requests_mock):
    requests_mock.get(
        "https://gitlab.com/api/v4/projects/8273019/issues/2/closed_by", body=to_bytes(TestData.closed_by.empty)
    )


@pytest.fixture
def get_closed_by_merge_request(requests_mock):
    requests_mock.get(
        "https://gitlab.com/api/v4/projects/8273019/issues/2/closed_by", body=to_bytes(TestData.closed_by.merge)
    )


@pytest.fixture
def get_mixed_labels(requests_mock):
    requests_mock.get(
        "https://gitlab.com/api/v4/projects/8273019/issues/2/resource_label_events",
        body=to_bytes(TestData.resource_label_events.excluded_stages),
    )


@pytest.fixture
def get_issues_with_label(requests_mock):
    requests_mock.get(
        "https://gitlab.com/api/v4/groups/gozynta/issues",
        body=to_bytes(TestData.issues.labeled.body),
    )

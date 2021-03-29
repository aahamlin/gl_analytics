import io
import datetime

from gl_analytics.__main__ import main, build_transitions
from gl_analytics.issues import GITLAB_URL_BASE, Issue

def test_build_transitions_from_issues():
    created_at = datetime.datetime(2021, 3, 13, 10, tzinfo=datetime.timezone.utc)
    wfData =  [
        ('ready', datetime.datetime(2021, 3, 14, 10, tzinfo=datetime.timezone.utc)),
        ('in progress', datetime.datetime(2021, 3, 15, 10, tzinfo=datetime.timezone.utc)),
        ('done', datetime.datetime(2021, 3, 16, 10, tzinfo=datetime.timezone.utc))
    ]

    issues = [Issue(1, 2, created_at, label_events=wfData), Issue(2, 2, created_at, label_events=wfData)]
    transitions = build_transitions(issues)
    assert len(transitions) == 2
    assert all([len(t)==4 for t in transitions]) # opened, ready, in progress, done

def test_main(requests_mock):
    """Test that the main function runs without error.
    """
    requests_mock.get(
        GITLAB_URL_BASE + '/groups/gozynta/issues',
        body=io.BytesIO(b'[{"id":8000234,"iid":2,"project_id":"8273019","title":"test title","created_at":"2021-03-09T17:59:43.041Z"}]'))
    requests_mock.get(
        GITLAB_URL_BASE + '/projects/8273019/issues/2/resource_label_events',
        body=io.BytesIO(b'[{"created_at": "2021-02-09T16:59:37.783Z","resource_type": "Issue","label":{"id": 18205357,"name": "workflow::Designing"},"action": "add"},{"created_at": "2021-02-09T17:00:49.416Z","resource_type": "Issue","label": {"id": 18205410,"name": "workflow::In Progress"},"action": "add"},{"created_at": "2021-02-09T17:00:49.416Z","resource_type": "Issue","label": {"id": 18205357,"name": "workflow::Designing"},"action": "remove"}]'))

    main(access_token="x", group="gozynta", milestone="mb_v1.3")

    assert True

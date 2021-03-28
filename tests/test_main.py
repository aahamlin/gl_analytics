import io
import datetime

from gl_analytics.__main__ import main, build_transitions
from gl_analytics.issues import GitlabSession, GitlabIssuesRepository, GitlabWorkflowResolver, Issue

from . import build_http_response, FakeRequestFactory

def test_build_transitions_from_issues():
    created_at = datetime.datetime(2021, 3,13,10,tzinfo=datetime.timezone.utc)
    wfData =  [
        ('ready', datetime.datetime(2021, 3,14,10,tzinfo=datetime.timezone.utc)),
        ('in progress', datetime.datetime(2021, 3,15,10,tzinfo=datetime.timezone.utc)),
        ('done', datetime.datetime(2021, 3,16,10,tzinfo=datetime.timezone.utc))
    ]

    issues = [Issue(1, 2, created_at, label_events=wfData), Issue(2, 2, created_at, label_events=wfData)]
    transitions = build_transitions(issues)
    assert len(transitions) == 2
    assert all([len(t)==4 for t in transitions]) # opened, ready, in progress, done

def test_main():
    """Test that the main function runs without error.
    """
    resp = []
    resp.append(build_http_response(
        200,
        bytes=io.BytesIO(b'[{"id":8000234,"iid":2,"project_id":"8273019","title":"test title","created_at":"2021-03-09T17:59:43.041Z"}]')))

    resp.append(build_http_response(
        status_code=200,
        # XXX load payload from string to bytes more easily...
        bytes=io.BytesIO(b'[{"created_at": "2021-02-09T16:59:37.783Z","resource_type": "Issue","label":{"id": 18205357,"name": "workflow::Designing"},"action": "add"},{"created_at": "2021-02-09T17:00:49.416Z","resource_type": "Issue","label": {"id": 18205410,"name": "workflow::In Progress"},"action": "add"},{"created_at": "2021-02-09T17:00:49.416Z","resource_type": "Issue","label": {"id": 18205357,"name": "workflow::Designing"},"action": "remove"}]')))

    fake = FakeRequestFactory()
    fake.responses = resp
    session = GitlabSession(access_token="x", request_factory=fake)

    repo = GitlabIssuesRepository(session, group="gozynta", milestone="mb_v1.3", resolvers=[GitlabWorkflowResolver])

    main(repository=repo)

    assert True

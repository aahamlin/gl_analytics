import io

from gl_analytics.__main__ import main

from . import build_http_response, FakeRequestFactory

from gl_analytics.issues import GitlabSession, GitlabIssuesRepository, GitlabWorkflowResolver

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

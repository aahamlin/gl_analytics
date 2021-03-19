import pytest

import io

from urllib.parse import urlparse
from requests import Response

import gl_analytics.issues as issues

class FakeSession():

    def __init__(self, responses=None):
        """Initialize a fake to test requests.

       response: provide a complete HTTP response object
       cb: callback will be called on every get()
       """
        self.path = None
        self.params = None
        if isinstance(responses, list):
            self.responses = responses
        elif responses:
            self.responses = [responses]
        else:
            resp = Response()
            resp.status_code = 500
            self.responses = [resp]

        self.headers = {}
        self.params = {}

        self._call_index = -1
        self._call_instances = []

    def get(self, url, **kwargs):
        self._call_index += 1

        o = urlparse(url)
        self.path = o.path
        self.params = o.query
        self.headers = kwargs.get('headers')
        self._call_instances.append({'url': url, 'headers': self.headers})

        return self.responses[self._call_index]

    @property
    def call_instances(self):
        return self._call_instances

def build_fake_request(responses=None):
    fake = FakeSession(responses=responses)
    return fake

def build_http_response(status_code, bytes=None, headers=None):
    # simple setup of fake response data
    response = Response()
    response.status_code = status_code
    response.encoding = 'utf-8'
    if bytes:
        response.raw = bytes
    if headers:
        response.headers.update(headers)
    return response

# XXX apply the fake session to the session object via Mixin?
def setup_fake_request(session, fake):
    # install our _get handler for testing
    session._get = fake.get

def test_abstract_session():
    with pytest.raises(issues.IssuesError):
        issues.Session().get()

def test_gitlab_session():
    s = issues.GitlabSession(access_token="x")
    assert s != None

def test_gitlab_session_get():
    s = issues.GitlabSession(access_token="x")
    resp = build_http_response(
        200,
        bytes=io.BytesIO(b'[{"id":8000234,"iid":2,"project_id":"8273019","title":"test title"}]'))
    fake = build_fake_request(responses=resp)
    setup_fake_request(s, fake)
    url = s.build_request_url("gozynta", "mb_v1.3")
    s.get(url)

    assert fake.path != None
    assert fake.path.endswith("/groups/gozynta/issues")
    assert fake.params.endswith("pagination=keyset&milestone=mb_v1.3")
    assert 'PRIVATE-TOKEN' in fake.headers

def test_repo_list_pagination():
    """Make sure we page correctly.

    The GitLab API, when using the pagination=keyset parameter, returns the pages referenced
    as first, next, last via the link response header.
    """
    s = issues.GitlabSession(access_token="x")
    resp = []
    resp.append(build_http_response(
        200,
        headers={'link': '<https://gitlab.com/api/v4/groups/gozynta/issues?id=gozynta&milestone=mb_v1.3&non_archived=true&order_by=created_at&page=2&pagination=keyset&per_page=5&sort=desc&state=all&with_labels_details=false>; rel="next", <https://gitlab.com/api/v4/groups/gozynta/issues?id=gozynta&milestone=mb_v1.3&non_archived=true&order_by=created_at&page=1&pagination=keyset&per_page=5&sort=desc&state=all&with_labels_details=false>; rel="first", <https://gitlab.com/api/v4/groups/gozynta/issues?id=gozynta&milestone=mb_v1.3&non_archived=true&order_by=created_at&page=9&pagination=keyset&per_page=5&sort=desc&state=all&with_labels_details=false>; rel="last"'},
        bytes=io.BytesIO(b'[{"id":8000234,"iid":2,"project_id":"8273019","title":"test title"}]')))

    resp.append(build_http_response(
        200,
        headers={'link': '<https://gitlab.com/api/v4/groups/gozynta/issues?id=gozynta&milestone=mb_v1.3&non_archived=true&order_by=created_at&page=1&pagination=keyset&per_page=5&sort=desc&state=all&with_labels_details=false>; rel="first", <https://gitlab.com/api/v4/groups/gozynta/issues?id=gozynta&milestone=mb_v1.3&non_archived=true&order_by=created_at&page=9&pagination=keyset&per_page=5&sort=desc&state=all&with_labels_details=false>; rel="last"'},
        bytes=io.BytesIO(b'[{"id":8000235, "iid":3,"project_id":"8273019","title":"test title 2"}]')))

    fake = build_fake_request(responses=resp)
    setup_fake_request(s, fake)

    repo = issues.Repository(session=s, group="gozynta", milestone="mb_v1.3")
    issue_list = repo.list()
    assert len(fake.call_instances) == 2
    print('Issue listing', issue_list)
    assert len(issue_list) == 2

from . import context

from requests import Response
from urllib.parse import urlparse, parse_qs

from gl_analytics.issues import AbstractRequestFactory

class FakeRequestFactory(AbstractRequestFactory):

    def __init__(self):
        """Initialize a fake to test requests.
        """
        self.responses = []
        self._call_index = -1
        self._call_instances = []

    def get(self, url, **kwargs):
        self._call_index += 1
        o = urlparse(url)
        info = FakeRequestInfo(path=o.path, params=parse_qs(o.query), headers=kwargs.get('headers'))
        print(info)
        self._call_instances.append(info)

        try:
            return self.responses[self._call_index]
        except IndexError:
            http500 = Response()
            http500.status_code = 500
            return http500

    @property
    def call_instances(self):
        return self._call_instances

class FakeRequestInfo(object):

    def __init__(self, path="", params={}, headers={}):
        self.path = path
        self.params = params
        self.headers = headers

    def __str__(self):
        return f"path:{self.path}, params:{self.params}, headers:{self.headers}"

def build_fake_http_response(status_code, bytes=None, headers=None):
    # simple setup of fake response data
    response = Response()
    response.status_code = status_code
    response.encoding = 'utf-8'
    if bytes:
        response.raw = bytes
    if headers:
        response.headers.update(headers)
    return response

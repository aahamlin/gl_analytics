import logging

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

_log = logging.getLogger(__name__)


@contextmanager
def timer(msg):
    start = datetime.now(tz=timezone.utc)
    try:
        yield
    finally:
        end = datetime.now(tz=timezone.utc)
        delta = (end - start) / timedelta(milliseconds=1)
        _log.debug(f"{msg} took {delta}ms")


from gl_analytics.func import foldl


def test_foldl_accumulates():

    result = foldl(lambda acc, val: acc * val, 1, [2, 4, 6, 8])

    assert 384 == result

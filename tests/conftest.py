import pytest
import pandas as pd
import datetime

from os import path

from gl_analytics.metrics import daterange


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
def filepath(tmp_path):
    tmp_filepath = path.join(tmp_path, "t.csv")
    return tmp_filepath

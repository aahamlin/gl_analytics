from . import context  # NOQA

import logging
import os

from contextlib import contextmanager
from datetime import timedelta
from enum import Enum

logging.getLogger("flake8").setLevel(logging.CRITICAL)


@contextmanager
def change_directory(new_path):
    prev_cwd = os.getcwd()
    os.chdir(new_path)
    yield
    os.chdir(prev_cwd)


def read_filepath(fpath):
    content = ""
    with open(fpath, mode="r", newline="", encoding="utf-8") as fbuf:
        while True:
            chunk = fbuf.read(2048)
            if not chunk:
                break
            content += chunk

    return content


class IncrementBy(Enum):
    MIN = 1
    HOUR = 2
    DAY = 3


increment_datetime = {
    IncrementBy.DAY: lambda dt: dt + timedelta(days=1),
    IncrementBy.HOUR: lambda dt: dt + timedelta(hours=1),
    IncrementBy.MIN: lambda dt: dt + timedelta(minutes=1),
}


def records(pid, iid, start, steps=None, inc_by=IncrementBy.DAY, _type=None):
    """Generator returns records of events formatted as the expected output from Pandas DataFrames.

    Args:
    pid - Project id
    iid - Issue id
    start - datetime the issue was created, always labeled as 'opened'
    steps - intermediate labels for state transitions
    inc_by - timedela increment to add to datetime for each transition
    _type - type label
    """
    all_steps = ["opened"]
    if steps:
        all_steps += steps

    def base_record(dt, name):
        return {
            "datetime": dt,
            "project": pid,
            "id": iid,
            "type": _type,
            name: 1,
        }

    datetime_value = start
    for i, name in enumerate(all_steps):
        if i == 0:
            yield base_record(datetime_value, name)
        else:
            prev_name = all_steps[i - 1]
            datetime_value = increment_datetime[inc_by](datetime_value)
            rec = base_record(datetime_value, name)
            rec.update({prev_name: 0})
            yield rec

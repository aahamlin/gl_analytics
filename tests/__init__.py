from . import context # NOQA

import os

from contextlib import contextmanager


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

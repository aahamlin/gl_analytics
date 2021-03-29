import os
import io
import json
from types import SimpleNamespace

path = os.path.abspath(__file__)
dir_path = os.path.dirname(path)


def _load_json(filename):
    filepath = os.path.join(dir_path, filename)
    with io.open(filepath, "r") as f:
        return json.load(f, object_hook=lambda d: SimpleNamespace(**d))


TestData = _load_json("data.json")


def to_bytes(obj):
    return io.BytesIO(bytearray(obj, encoding="UTF8"))


def to_link_header(obj):
    return {"link": obj}

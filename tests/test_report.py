import sys

from gl_analytics.report import CsvReport


def test_csv_return_string(df):
    report = CsvReport(df)
    content = report.export()
    assert ",todo,inprogress,done" in content
    assert "2021-03-19,0,1,2" in content


def test_csv_to_stdout(capsys, df):
    report = CsvReport(df, file=sys.stdout)
    capsys.readouterr()
    report.export()
    captured = capsys.readouterr()
    assert ",todo,inprogress,done" in captured.out
    assert "2021-03-19,0,1,2" in captured.out


def test_csv_to_filepath(filepath, df):
    report = CsvReport(df, file=filepath)
    report.export()
    content = read_filepath(filepath)
    assert ",todo,inprogress,done" in content
    assert "2021-03-19,0,1,2" in content


def test_csv_to_filebuf(filepath, df):
    with open(filepath, mode="w", newline="", encoding="utf-8") as fbuf:
        report = CsvReport(df, file=fbuf)
        report.export()

    content = read_filepath(filepath)
    assert ",todo,inprogress,done" in content
    assert "2021-03-19,0,1,2" in content


def read_filepath(fpath):
    content = ""
    with open(fpath, mode="r", newline="", encoding="utf-8") as fbuf:
        while True:
            chunk = fbuf.read(2048)
            if not chunk:
                break
            content += chunk

    return content

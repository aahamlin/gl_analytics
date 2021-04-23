import sys

from gl_analytics.report import CsvReport, PlotReport


def read_filepath(fpath):
    content = ""
    with open(fpath, mode="r", newline="", encoding="utf-8") as fbuf:
        while True:
            chunk = fbuf.read(2048)
            if not chunk:
                break
            content += chunk

    return content


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


def test_csv_to_filepath_csv(filepath_csv, df):
    report = CsvReport(df, file=filepath_csv)
    report.export()
    content = read_filepath(filepath_csv)
    assert ",todo,inprogress,done" in content
    assert "2021-03-19,0,1,2" in content


def test_csv_to_filebuf(filepath_csv, df):
    with filepath_csv.open(mode="w", newline="", encoding="utf-8") as fbuf:
        report = CsvReport(df, file=fbuf)
        report.export()

    content = read_filepath(filepath_csv)
    assert ",todo,inprogress,done" in content
    assert "2021-03-19,0,1,2" in content


def test_save_image(filepath_png, df):
    report = PlotReport(df, file=filepath_png.resolve())
    report.export()
    assert filepath_png.exists()

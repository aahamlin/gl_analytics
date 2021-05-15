import sys

from gl_analytics.report import CsvReport, PlotReport
from tests import read_filepath


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


def test_plot_should_generate_title(filepath_png, df):
    milestone = "m1"
    start_date = df.index.date[0]
    end_date = df.index.date[-1]
    report = PlotReport(df, file=filepath_png.resolve(), title=f"{milestone}")
    assert report.title == f"CFD {milestone} {start_date} {end_date}"


def test_plot_should_save_png_image(filepath_png, df):
    report = PlotReport(df, file=filepath_png.resolve())
    report.export()
    assert filepath_png.exists()

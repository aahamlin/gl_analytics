import sys

import matplotlib.pyplot as plt


class CsvReport:
    """Configure the output of a DataFrame csv format.
    """

    def __init__(self, df, file=None):
        """Prepare a CSV report format file.

        This is no more than a convenience wrapper to Pandas DataFrame API.

        Arguments:
        df - DataFrame (required)
        file - Write to given file path or open file buffer. Returns a string when None.
        """
        self._df = df
        self._file = file

    def export(self):
        """Export dataframe to CSV format.

        Todo: pass arguments directly to dataframe to_csv function.
        """
        return self._df.to_csv(
            self._file,
            date_format="%Y-%m-%d"
        )


class PlotReport:
    """Configure the output of a DataFrame to plot image (.png).
    """

    def __init__(self, df, file=None):
        """Prepare a plot file.

        This is no more than a convenience wrapper to Pandas DataFrame API.

        Arguments:
        df - DataFrame (required)
        file - Write to given file path or open file buffer. Returns a string when None.
        """
        self._df = df
        self._file = file

    def export(self):
        plt.close("all")
        ax = self._df.plot.area(
            title="Cumulative Flow",  # XXX generate title from query filter & datetimes
            legend="reverse",
            ylabel="Count of issues",
            xlabel="Days"
        )
        fig = ax.get_figure()
        fig.savefig(self._file)

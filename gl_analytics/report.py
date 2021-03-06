import matplotlib.pyplot as plt


class CsvReport:
    """Configure the output of a DataFrame csv format."""

    def __init__(self, df, file=None, **kwargs):
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
        return self._df.to_csv(self._file, date_format="%Y-%m-%d")


class PlotReport:
    """Configure the output of a DataFrame to plot image (.png)."""

    def __init__(self, df, file=None, title="CFD", **kwargs):
        """Prepare a plot file.

        This is no more than a convenience wrapper to Pandas DataFrame API.

        Arguments:
        df - DataFrame (required)
        file - Write to given file path or open file buffer. Returns a string when None.
        title - Extra title, typically represents the search criteria, e.g. milestone name
        """
        self._df = df[df.columns[::-1]]  # reverse order of columns
        self._file = file
        self.title = " ".join([title, str(df.index.date[0]), str(df.index.date[-1])])
        self.min = self._calc_min(df)
        self.max = self._calc_max(df)

    def _calc_min(self, df):
        _min = df[df.columns.values[-1]].min()
        return _min - (_min % 10)

    def _calc_max(self, df):
        _max = df.sum(axis=1).max()
        return round(_max + 5, -1)

    def export(self):
        plt.close("all")

        args = {
            "title": self.title,
            "legend": "reverse",
            "ylabel": "Count of Issues",
            "xlabel": "Days",
            "ylim": (self.min, self.max),
        }

        ax = self._df.plot.area(**args)
        fig = ax.get_figure()
        fig.savefig(self._file)

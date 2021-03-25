import sys


class CsvReport(object):
    """Configure the output of a DataFrame csv format."""

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
        return self._df.to_csv(self._file)

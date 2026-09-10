"""Two buoy-specific additions to ordinary xarray datasets."""

import json

import numpy as np
import xarray as xr

from .core import REPORT_ATTRIBUTE, _report_dataset


@xr.register_dataset_accessor("ndbc")
class NDBCAccessor:
    """Coverage and retrieval diagnostics; selection and plotting stay in xarray."""

    def __init__(self, dataset):
        self._obj = dataset

    def report(self) -> xr.Dataset:
        """Return original per-file download outcomes, including failed files.

        The report describes the original request even after selecting/subsetting
        the observations. Datasets without download provenance return an empty
        report. Records survive NetCDF export in a JSON string attribute.
        """
        return _report_dataset(json.loads(self._obj.attrs.get(REPORT_ATTRIBUTE, "[]")))

    def coverage(self, freq, start=None, end=None) -> xr.Dataset:
        """Percentage of time bins containing at least one valid observation.

        Parameters
        ----------
        freq : str
            Explicit xarray resampling frequency, for example 'D', 'h', or 'ME'.
        start, end : datetime-like, optional
            Inclusive UTC window. Defaults to the dataset's first and last
            timestamps. A date such as '2020-12-31' means midnight; specify the
            final time of day when the entire last day is intended.

        Returns
        -------
        xarray.Dataset
            Original variable names with percent units. Empty bins count against
            coverage, including bins outside the observed range when a wider
            window is supplied. Station, frequency, and depth dimensions survive.
            This measures occupied bins, not expected native sampling completeness.
        """
        dataset = self._obj
        if not isinstance(freq, str) or not freq.strip():
            raise ValueError(
                "freq must be an explicit resampling frequency, such as 'D'"
            )
        if "time" not in dataset.dims or dataset.time.ndim != 1:
            raise ValueError("Coverage requires a one-dimensional time coordinate")
        if not np.issubdtype(dataset.time.dtype, np.datetime64):
            raise TypeError("Coverage requires datetime64 UTC timestamps")
        if not dataset.sizes["time"] and (start is None or end is None):
            raise ValueError("Empty time coordinates require explicit start and end")
        times = dataset.time.values.astype("datetime64[ns]")
        if np.isnat(times).any():
            raise ValueError("time must not contain NaT")
        start = np.datetime64(start, "ns") if start is not None else times.min()
        end = np.datetime64(end, "ns") if end is not None else times.max()
        if np.isnat(start) or np.isnat(end) or start > end:
            raise ValueError("Coverage requires finite timestamps with start <= end")
        dataset = dataset.sortby("time").drop_duplicates("time", keep="first")
        selected = dataset.sel(time=slice(start, end))
        time_variables = [
            name for name, value in selected.data_vars.items() if "time" in value.dims
        ]
        if not time_variables:
            raise ValueError("Dataset contains no time-dependent observation variables")
        # Insert missing boundary samples so resampling counts the full requested
        # window, even when no observations occur near its beginning or end.
        grid = np.unique(
            np.concatenate(
                [selected.time.values.astype("datetime64[ns]"), [start, end]]
            )
        )
        # Numeric flags preserve empty bins as NaN with both resampling engines.
        presence = xr.where(selected[time_variables].notnull(), 1.0, np.nan).reindex(
            time=grid
        )
        try:
            occupied_bins = presence.resample(time=freq).max(skipna=True).fillna(0)
        except (ValueError, TypeError, ZeroDivisionError) as error:
            raise ValueError(f"Invalid coverage frequency {freq!r}: {error}") from error
        result = occupied_bins.mean("time") * 100
        for name in time_variables:
            result[name].attrs = {
                "long_name": f"{dataset[name].attrs.get('long_name', name)} coverage",
                "units": "%",
            }
        result.attrs = dict(
            frequency=freq,
            window_start=str(start),
            window_end=str(end),
            time_bins=occupied_bins.sizes["time"],
            definition="Percent of bins containing at least one nonmissing observation",
        )
        return result

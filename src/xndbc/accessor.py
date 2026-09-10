"""Station maps, archive availability, and diagnostics for xarray datasets."""

import json

import numpy as np
import xarray as xr

from .core import REPORT_ATTRIBUTE, _report_dataset


@xr.register_dataset_accessor("ndbc")
class NDBCAccessor:
    """Station maps, archive availability, measurement coverage, and download reports."""

    def __init__(self, dataset):
        """Bind station and observation helpers to an xarray dataset."""
        self._obj = dataset

    def plot_map(self, variable=None, *, ax=None, labels="auto"):
        """Plot this dataset's station locations.

        Args:
            variable: Optional measurement used to color stations. Select or
                reduce time, depth, and frequency to one value per station first.
            ax: Existing Cartopy axes, or None to create a map.
            labels: Whether to label IDs; "auto" labels at most ten stations.

        Returns:
            A Matplotlib (figure, axes) pair. Missing measurements appear gray;
            stations with missing coordinates are omitted with a warning.

        Raises:
            ValueError: If station coordinates or measurement dimensions are invalid.

        Coastline data may be downloaded by Cartopy on first use.
        """
        from ._plotting import plot_station_map

        return plot_station_map(self._obj, variable, ax=ax, labels=labels)

    def availability(self, years=None, *, mode="stdmet", refresh=False):
        """Inspect archive file availability for this dataset's station IDs.

        Args:
            years: Archive year or iterable of years. None includes all indexed years.
            mode: NOAA product, defaulting to standard meteorological observations.
            refresh: Reload NOAA archive indexes and current station metadata
                instead of reusing the copies cached in memory.

        Returns:
            An xarray Dataset with station_id and year dimensions, boolean
            available flags, and file URLs. Missing files have False and an
            empty URL. Coordinates describe current station locations.

        Raises:
            ValueError: If IDs, years, or the historical product are invalid.
            TypeError: If station IDs or years have unsupported types.

        This reads NOAA indexes, not observation files. A listed file does not
        guarantee valid measurements. Download observations to calculate
        measurement coverage with coverage(); inspect report() for outcomes.
        """
        from ._stations import _normalize_station_ids, availability

        return availability(
            _normalize_station_ids(self._obj), years=years, mode=mode, refresh=refresh
        )

    def report(self) -> xr.Dataset:
        """Return the original download outcomes without accessing NOAA.

        Returns:
            An xarray Dataset indexed by request, with station_id, year, url, status,
            and error variables. Realtime years are missing. Datasets without download
            provenance return an empty report.

        The report remains tied to the original request after observation selection.
        A successful file can still contain missing measurements; use coverage() to
        assess those. Report provenance survives NetCDF export as a JSON attribute.
        """
        return _report_dataset(json.loads(self._obj.attrs.get(REPORT_ATTRIBUTE, "[]")))

    def coverage(self, freq, start=None, end=None) -> xr.Dataset:
        """Calculate measurement coverage as the percentage of occupied time bins.

        Args:
            freq: Explicit bin frequency such as "D", "h", or "ME".
            start: Inclusive UTC window start; defaults to the earliest observation.
            end: Inclusive UTC window end; defaults to the latest observation. A date
                without a time means midnight at the beginning of that day.

        Returns:
            An xarray Dataset with the original measurement names and percent units.
            Station, depth, and frequency dimensions survive; time is reduced. Each
            bin with at least one nonmissing value counts once. Empty bins, including
            those outside the observation range, remain in the denominator.

        Raises:
            ValueError: If frequency, boundaries, or time coordinates are invalid, or
                an empty time coordinate lacks explicit start and end boundaries.
            TypeError: If time is not represented by datetime64 timestamps.

        This operates on loaded observations without network access. It measures
        occupied bins, not expected native sample completeness or archive file presence.
        Calculate it before averaging. Two occupied days in a three-day window give
        66.7 percent coverage, even if each occupied day has only one measurement.

        Examples:
            >>> coverage = data[["WSPD"]].ndbc.coverage(
            ...     "D", start="2020-01-01", end="2020-12-31T23:59:59"
            ... )
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

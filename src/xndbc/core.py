"""Download NOAA observations, combine station files, and report file outcomes."""

import json
import sys
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from numbers import Integral
from urllib.error import HTTPError

import numpy as np
import xarray as xr

from . import _http
from ._catalog import get_stations, historical_file_index
from ._parsing import parse_observation_table, table_to_dataset
from ._products import MODES, validate_mode
from ._stations import _attach_metadata, _normalize_station_ids, _normalize_years
from ._stations import stations as discover_stations

REPORT_ATTRIBUTE = "ndbc_report"
REALTIME_ROOT = "https://www.ndbc.noaa.gov/data/realtime2"


def _report_dataset(requests):
    """Convert JSON-ready outcome records to an xarray request dataset.

    Realtime years become NaN; empty records produce an empty report.
    """
    variables = {
        key: ("request", np.asarray([r[key] for r in requests], dtype=str))
        for key in ("station_id", "url", "status", "error")
    }
    variables["year"] = (
        "request",
        np.asarray(
            [r["year"] if r["year"] is not None else np.nan for r in requests],
            dtype=float,
        ),
    )
    return xr.Dataset(
        variables,
        coords={"request": np.arange(len(requests))},
        attrs={
            "description": "Original download request outcomes; year is missing for realtime"
        },
    )


class RetrievalError(RuntimeError):
    """Signal an entirely unsuccessful or explicitly strict download.

    Attributes:
        report: An xarray Dataset containing every original per-file outcome,
            including successful files when a strict request partially fails.
    """

    def __init__(self, message, records):
        """Attach an outcome report to the retrieval error."""
        super().__init__(message)
        self.report = _report_dataset(records)


def _validate_options(errors, progress, max_workers):
    """Validate failure policy, progress display, and bounded concurrency.

    Raises:
        ValueError: If errors or max_workers are invalid.
        TypeError: If progress is neither boolean nor None.
    """
    if errors not in ("warn", "raise"):
        raise ValueError("errors must be 'warn' or 'raise'")
    if progress is not None and not isinstance(progress, bool):
        raise TypeError("progress must be True, False, or None (automatic)")
    if (
        isinstance(max_workers, bool)
        or not isinstance(max_workers, Integral)
        or max_workers < 1
    ):
        raise ValueError("max_workers must be a positive integer")


def _record(station, year, url="", status="pending", error=""):
    """Create a JSON-ready outcome: pending until discovery or download finishes."""
    return dict(station_id=station, year=year, url=url, status=status, error=error)


def _resolve_stations(selection, bounds):
    """Resolve exactly one selector into normalized, nonempty station IDs.

    Args:
        selection: Station dataset, ID string, iterable, or ID DataArray.
        bounds: Geographic bounds, used only when selection is absent.

    Returns:
        A list of unique station IDs in selection order.

    Raises:
        ValueError: If selectors conflict, are absent, or resolve to no stations.
        TypeError: If station IDs are not strings.
    """
    if (selection is None) == (bounds is None):
        raise ValueError("Provide either stations or bounds, but not both")
    if bounds is not None:
        selection = discover_stations(bounds=bounds)
    return _normalize_station_ids(selection)


def historical(
    stations=None, *, years, bounds=None, mode="stdmet", errors="warn",
    progress=None, max_workers=6
) -> xr.Dataset:
    """Download historical observations for explicit archive years.

    Args:
        stations: Station dataset, ID string, iterable of ID strings, or scalar or
            one-dimensional ID DataArray. Datasets must have a station_id coordinate.
            Case and surrounding whitespace are normalized; duplicates are removed.
        years: Required archive year, iterable of years, or year DataArray.
        bounds: Geographic dictionary with north, south, west, and east in degrees.
            Resolves the same stations as stations(bounds=...). Supply either a
            station selection or bounds, never both.
        mode: NOAA product code; defaults to "stdmet". See list_modes().
        errors: "warn" returns partial results with a warning; "raise" requires
            every requested file to succeed. All-failed requests always raise.
        progress: True or False controls file progress; None detects interactive use.
        max_workers: Positive maximum number of concurrent downloads, default 6.

    Returns:
        An xarray Dataset with station_id and time dimensions, plus frequency or
        depth_bin for relevant products. Original UTC timestamps and missing values
        are preserved; measurements are not averaged. Even one station retains its
        station_id dimension. Use data.ndbc.report() for original file outcomes.

    Raises:
        ValueError: If selectors conflict, are absent or empty, or options are invalid.
        TypeError: If IDs or years have unsupported types.
        RetrievalError: If all files fail, or any file fails with errors="raise".
        OSError: If geographic station discovery cannot retrieve the catalog.

    Observation files are downloaded on every call. Station metadata and archive
    indexes may be reused from an in-memory cache. Archive availability describes
    file presence, not measurement coverage.

    Examples:
        >>> data = xndbc.historical("44013", years=2020)
        >>> data.ndbc.report()
    """
    years = _normalize_years(years)
    mode = validate_mode(mode)
    _validate_options(errors, progress, max_workers)
    ids = _resolve_stations(stations, bounds)
    requests = [_record(station, year) for station in ids for year in years]
    try:
        archive_index = historical_file_index(mode).reindex(
            station_id=ids, year=years, fill_value={"available": False, "url": ""}
        )
    except Exception as error:
        for request in requests:
            request.update(status="failed", error=f"Archive index unavailable: {error}")
        raise RetrievalError(
            f"Could not discover historical {mode} files: {error}", requests
        ) from error
    for request in requests:
        request["url"] = str(
            archive_index.url.sel(
                station_id=request["station_id"], year=request["year"]
            ).item()
        )
        if not request["url"]:
            request.update(status="unavailable", error="No file in the archive index")
    return _fetch(requests, "historical", mode, errors, progress, max_workers)


def realtime(
    stations=None, *, bounds=None, mode="stdmet", errors="warn",
    progress=None, max_workers=6
) -> xr.Dataset:
    """Download observations from NOAA’s current realtime feed.

    Args:
        stations: Station dataset, ID string, iterable of ID strings, or scalar or
            one-dimensional ID DataArray. Datasets must have a station_id coordinate.
            Case and surrounding whitespace are normalized; duplicates are removed.
        bounds: Geographic dictionary with north, south, west, and east in degrees.
            Resolves the same stations as stations(bounds=...). Supply either a
            station selection or bounds, never both.
        mode: NOAA product code; defaults to "stdmet". See list_modes().
        errors: "warn" returns partial results with a warning; "raise" requires
            every requested file to succeed. All-failed requests always raise.
        progress: True or False controls file progress; None detects interactive use.
        max_workers: Positive maximum number of concurrent downloads, default 6.

    Returns:
        An xarray Dataset with station_id and time dimensions, plus frequency or
        depth_bin for relevant products. Original UTC timestamps and missing values
        are preserved; measurements are not averaged. Even one station retains its
        station_id dimension. Use data.ndbc.report() for original file outcomes.

    Raises:
        ValueError: If selectors conflict, are absent or empty, or options are invalid.
        TypeError: If IDs have unsupported types.
        RetrievalError: If all files fail, or any file fails with errors="raise".
        OSError: If geographic station discovery cannot retrieve the catalog.

    Observation files are downloaded on every call. Station metadata and archive
    indexes may be reused from an in-memory cache. NOAA determines the feed’s
    time window; there is no years argument.

    Examples:
        >>> data = xndbc.realtime("44013")
        >>> data.ndbc.report()
    """
    mode = validate_mode(mode, "realtime")
    _validate_options(errors, progress, max_workers)
    ids = _resolve_stations(stations, bounds)
    requests = [
        _record(
            station,
            None,
            f"{REALTIME_ROOT}/{station.upper()}.{MODES[mode].realtime_extension}",
        )
        for station in ids
    ]
    return _fetch(requests, "realtime", mode, errors, progress, max_workers)


def _download(url, mode):
    """Download and parse one product file into an xarray dataset.

    Network and parsing errors propagate to the request collector.
    """
    frame = parse_observation_table(_http.read_noaa_text(url), mode)
    return table_to_dataset(frame, mode)


def _fetch(requests, feed, mode, errors, progress, max_workers):
    # Catalog access and cache population happen before worker threads start.
    """Retrieve files and assemble observations with metadata and provenance.

    Args:
        requests: Mutable per-file outcome records populated during retrieval.
        feed: Historical or realtime, used in diagnostics and attributes.
        mode: Validated product code.
        errors: Warn on partial results or raise on any unsuccessful file.
        progress: Whether to show progress, or None for interactive detection.
        max_workers: Positive concurrency limit.

    Returns:
        Observations with current metadata and serialized original request outcomes.

    Raises:
        RetrievalError: If no observations succeed or a strict request partly fails.

    Catalog outages preserve downloaded observations with a warning and NaN locations.
    """
    metadata_error = ""
    try:
        metadata = get_stations()
    except Exception as error:
        metadata = None
        metadata_error = f"Station metadata unavailable: {error}"

    datasets = _download_requests(requests, mode, progress, max_workers)
    failures = [request for request in requests if request["status"] != "success"]
    if failures:
        first = failures[0]
        summary = (
            f"{len(failures)} of {len(requests)} {feed} {mode} files unavailable or failed. "
            f"First: {first['station_id']} {first['year'] or ''}: {first['error']}."
        )
        if not datasets or errors == "raise":
            raise RetrievalError(summary, requests)
    else:
        summary = ""
    dataset = _combine_station_files(requests, datasets)
    dataset = _attach_metadata(dataset, metadata)
    dataset.attrs.update(
        source="NOAA National Data Buoy Center",
        feed=feed,
        ndbc_mode=mode,
        retrieved_at=datetime.now(UTC).isoformat(),
        ndbc_report=json.dumps(requests),
        sampling="Original observations; no temporal resampling",
    )
    if metadata_error:
        dataset.attrs["metadata_error"] = metadata_error
    if summary or metadata_error:
        details = [text for text in (summary, metadata_error) if text]
        details.append("Inspect data.ndbc.report() for file outcomes.")
        warnings.warn(" ".join(details), UserWarning, stacklevel=3)
    return dataset


def _download_requests(requests, mode, progress, max_workers):
    """Download files concurrently and update per-file outcomes in place.

    Args:
        requests: Mutable outcome records; only pending records are downloaded.
        mode: Validated product code passed to the parser.
        progress: Boolean display control, or None for interactive detection.
        max_workers: Positive number of worker threads.

    Returns:
        A mapping from original request index to successfully parsed datasets.
        Completion order does not change request order. HTTP 404 errors mark files
        unavailable; other download or parse exceptions mark files failed.
    """
    from tqdm import tqdm

    if progress is None:
        progress = sys.stderr.isatty() or "ipykernel" in sys.modules
    observations = {}
    pending = [
        i for i, request in enumerate(requests) if request["status"] == "pending"
    ]
    with (
        tqdm(
            total=len(requests),
            initial=len(requests) - len(pending),
            desc="Fetching files",
            unit="file",
            disable=not progress,
        ) as bar,
        ThreadPoolExecutor(max_workers=max_workers) as pool,
    ):
        futures = {pool.submit(_download, requests[i]["url"], mode): i for i in pending}
        for future in as_completed(futures):
            i = futures[future]
            try:
                observations[i] = future.result()
                requests[i]["status"] = "success"
            except Exception as error:
                status = (
                    "unavailable"
                    if isinstance(error, HTTPError) and error.code == 404
                    else "failed"
                )
                requests[i].update(
                    status=status, error=f"{type(error).__name__}: {error}"
                )
            bar.update(1)
    return observations


def _combine_station_files(requests, datasets):
    """Align successful observations by station and original timestamp.

    Args:
        requests: Ordered per-file records containing station IDs.
        datasets: Mapping of successful request indices to parsed datasets.

    Returns:
        An xarray Dataset with station_id/time dimensions and the union of other
        product coordinates. Absent observations become missing values without
        interpolation. Duplicate timestamps use the first file in request order;
        stations without successful files are omitted.
    """
    station_datasets = []
    for station in dict.fromkeys(request["station_id"] for request in requests):
        station_files = [
            datasets[i]
            for i, request in enumerate(requests)
            if request["station_id"] == station and i in datasets
        ]
        if station_files:
            combined = xr.concat(
                station_files,
                dim="time",
                join="outer",
                coords="minimal",
                compat="override",
            )
            combined = combined.sortby("time").drop_duplicates("time", keep="first")
            station_datasets.append(combined.expand_dims(station_id=[station]))
    dataset = xr.concat(
        station_datasets,
        dim="station_id",
        join="outer",
        coords="minimal",
        compat="override",
    )
    return dataset

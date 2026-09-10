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
from .stations import _attach_metadata, _normalize_station_ids, _normalize_years

REPORT_ATTRIBUTE = "ndbc_report"
REALTIME_ROOT = "https://www.ndbc.noaa.gov/data/realtime2"


def _report_dataset(requests):
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
    """A download failed. ``report`` contains its per-file outcomes as xarray."""

    def __init__(self, message, records):
        super().__init__(message)
        self.report = _report_dataset(records)


def _validate_options(errors, progress, max_workers):
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


def fetch_historical(
    station_ids, years, *, mode="stdmet", errors="warn", progress=None, max_workers=6
) -> xr.Dataset:
    """Download historical observations at their original timestamps.

    Parameters
    ----------
    station_ids : str, iterable of str, or xarray.DataArray
        One or more NDBC IDs. Case and surrounding whitespace are normalized.
    years : int, iterable of int, or xarray.DataArray
        Archive years, for example 2020 or range(2018, 2021).
    mode : str, default "stdmet"
        Product from xndbc.list_modes().
    errors : {"warn", "raise"}, default "warn"
        Summarize partial failures in one warning, or raise RetrievalError if any
        request fails. An entirely unsuccessful request always raises.
    progress : bool or None, default None
        Show completed-file progress. None automatically enables interactive output.
    max_workers : int, default 6
        Maximum concurrent file downloads and parses.

    Returns
    -------
    xarray.Dataset
        Observations with station_id and time dimensions, plus frequency or
        depth_bin where relevant. No automatic averaging is performed. Inspect
        data.ndbc.report() for missing or failed station/year requests.
    """
    ids, years = _normalize_station_ids(station_ids), _normalize_years(years)
    mode = validate_mode(mode)
    _validate_options(errors, progress, max_workers)
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


def fetch_realtime(
    station_ids, *, mode="stdmet", errors="warn", progress=None, max_workers=6
) -> xr.Dataset:
    """Download recent observations at their original timestamps.

    Parameters
    ----------
    station_ids : str, iterable of str, or xarray.DataArray
        One or more NDBC IDs. Case and surrounding whitespace are normalized.
    mode : str, default "stdmet"
        Product with realtime support from :func:`xndbc.list_modes`.
    errors : {"warn", "raise"}, default "warn"
        Summarize partial failures in one warning, or raise RetrievalError if any
        request fails. An entirely unsuccessful request always raises.
    progress : bool or None, default None
        Show completed-file progress. None automatically enables interactive output.
    max_workers : int, default 6
        Maximum concurrent file downloads and parses.

    Returns
    -------
    xarray.Dataset
        Observations at original timestamps, with station_id and time dimensions
        and frequency or depth_bin where relevant. NOAA determines the current
        feed's time window. Inspect data.ndbc.report() for download outcomes.

    See Also
    --------
    fetch_historical : Download specific archive years.
    """
    ids, mode = _normalize_station_ids(station_ids), validate_mode(mode, "realtime")
    _validate_options(errors, progress, max_workers)
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
    frame = parse_observation_table(_http.read_noaa_text(url), mode)
    return table_to_dataset(frame, mode)


def _fetch(requests, feed, mode, errors, progress, max_workers):
    # Catalog access and cache population happen before worker threads start.
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
    """Collect outcomes by request index, independent of worker completion order."""
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
    """Combine in request order so the first file wins at overlapping timestamps."""
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

"""Discover NDBC stations and historical files as xarray datasets."""

import re
import warnings
from collections.abc import Mapping
from numbers import Integral, Real

import numpy as np
import xarray as xr

from ._catalog import get_stations, historical_file_index
from ._products import validate_mode


def _normalize_station_ids(values):
    """Accept scalar or iterable IDs, normalize case, and retain first-seen order."""
    if isinstance(values, xr.DataArray):
        values = values.values
    if isinstance(values, np.ndarray) and values.ndim == 0:
        values = values.item()
    if isinstance(values, str):
        values = [values]
    try:
        array = np.asarray(list(values), dtype=object)
    except TypeError as error:
        raise TypeError("station_ids must be strings, for example '44013'") from error
    if array.ndim != 1 or not array.size:
        raise ValueError("station_ids must contain one or more station ID strings")
    if any(not isinstance(value, str) for value in array):
        raise TypeError("station_ids must be strings, for example '44013'")
    ids = [value.strip().lower() for value in array]
    if any(not re.fullmatch(r"[a-z0-9]+", value) for value in ids):
        raise ValueError("station_ids must be nonempty alphanumeric strings")
    return list(dict.fromkeys(ids))


def _normalize_years(values):
    """Accept scalar or iterable integer years and return sorted unique values."""
    if isinstance(values, xr.DataArray):
        values = values.values
    if isinstance(values, np.ndarray) and values.ndim == 0:
        values = values.item()
    if isinstance(values, Integral):
        values = [values]
    try:
        values = list(values)
    except TypeError as error:
        raise TypeError("years must be an integer or iterable of integers") from error
    if not values:
        raise ValueError("years must not be empty")
    if any(
        isinstance(v, (bool, np.bool_)) or not isinstance(v, Integral) for v in values
    ):
        raise TypeError(
            "years must contain integers, for example 2020 or range(2018, 2021)"
        )
    if any(not 1900 <= v <= 9999 for v in values):
        raise ValueError("years must be four-digit years from 1900 onwards")
    return sorted(set(int(v) for v in values))


def _validate_bounds(bounds):
    """Validate degree bounds; west > east deliberately allows dateline crossings."""
    if bounds is None:
        return None
    keys = ("west", "south", "east", "north")
    if not isinstance(bounds, Mapping) or set(bounds) != set(keys):
        raise ValueError(
            "bounds must be a dictionary with exactly these keys: "
            "north, south, west, east"
        )
    values = [bounds[key] for key in keys]
    if any(
        isinstance(value, (bool, np.bool_)) or not isinstance(value, Real)
        for value in values
    ):
        raise ValueError("bounds coordinates must be finite numbers in degrees")
    if not all(-180 <= value <= 180 for value in values):
        raise ValueError("bounds coordinates must be finite numbers within [-180, 180]")
    west, south, east, north = values
    if not (
        -180 <= west <= 180 and -180 <= east <= 180 and -90 <= south <= north <= 90
    ):
        raise ValueError(
            "Longitudes must be within [-180, 180] and -90 <= south <= north <= 90"
        )
    return west, south, east, north


def _filter_bounds(dataset, bounds):
    if bounds is None:
        return dataset
    west, south, east, north = bounds
    lon, lat = dataset.longitude, dataset.latitude
    longitude_mask = (
        ((lon >= west) & (lon <= east))
        if west <= east
        else ((lon >= west) | (lon <= east))
    )
    # Index instead of Dataset.where to preserve boolean availability and strings.
    mask = longitude_mask & (lat >= south) & (lat <= north)
    return dataset.isel(station_id=mask)


def search(station_ids=None, *, query=None, bounds=None, refresh=False) -> xr.Dataset:
    """Find stations by IDs, text, or geographic bounds.

    Parameters
    ----------
    station_ids : str, iterable of str, or xarray.DataArray, optional
        Limit the catalog to these IDs. Unknown IDs are omitted.
    query : str, optional
        Case-insensitive literal substring of station ID, name, owner, or type.
    bounds : mapping of str to float, optional
        Dictionary with exactly north, south, west, east keys, in degrees.
        Key order does not matter. West > east crosses the dateline.
    refresh : bool, default False
        Refresh the in-memory station catalog from NOAA.

    Returns
    -------
    xarray.Dataset
        Metadata along station_id with latitude/longitude coordinates. Positions
        describe the current catalog, not necessarily historical deployment sites.
    """
    ids = _normalize_station_ids(station_ids) if station_ids is not None else None
    bounds = _validate_bounds(bounds)
    if query is not None and not isinstance(query, str):
        raise TypeError("query must be a string")
    dataset = get_stations(refresh=refresh)
    if ids is not None:
        dataset = dataset.sel(
            station_id=[s for s in ids if s in dataset.station_id.values]
        )
    if query is not None:
        needle = query.strip().casefold()
        matches = xr.zeros_like(dataset.station_id, dtype=bool)
        for name in ("station_id", "name", "owner", "station_type"):
            text = dataset[name].astype(str)
            matches |= text.str.casefold().str.contains(needle, regex=False)
        dataset = dataset.isel(station_id=matches)
    return _filter_bounds(dataset, bounds)


def _attach_metadata(dataset, metadata):
    if metadata is None:
        return dataset.assign_coords(
            latitude=("station_id", np.full(dataset.sizes["station_id"], np.nan)),
            longitude=("station_id", np.full(dataset.sizes["station_id"], np.nan)),
        )
    metadata = metadata.reindex(station_id=dataset.station_id)
    coords = {name: metadata[name] for name in ("latitude", "longitude")}
    for name in ("name", "owner", "station_type", "notes"):
        if name in metadata:
            coords[name] = metadata[name].fillna("")
    return dataset.assign_coords(coords)


def availability(
    station_ids=None, *, years=None, mode="stdmet", bounds=None, refresh=False
) -> xr.Dataset:
    """Return historical file presence along station_id and year.

    Parameters
    ----------
    station_ids : str, iterable of str, or xarray.DataArray, optional
        Requested IDs. Absent IDs have available=False and an empty URL.
    years : int, iterable of int, or xarray.DataArray, optional
        Requested years. Defaults to years represented in the archive index.
    mode : str, default "stdmet"
        Historical product; see xndbc.list_modes().
    bounds : mapping of str to float, optional
        Dictionary with exactly north, south, west, east keys, in degrees.
        Key order does not matter. West > east crosses the dateline.
        Requires known station coordinates.
    refresh : bool, default False
        Refresh archive indexes and station metadata.

    Returns
    -------
    xarray.Dataset
        Boolean available and string url variables. Presence means a file exists,
        not that every measurement or time interval is populated. Archive-only
        stations remain in results with missing metadata unless bounds exclude them.
    """
    ids = _normalize_station_ids(station_ids) if station_ids is not None else None
    years = _normalize_years(years) if years is not None else None
    mode, bounds = validate_mode(mode), _validate_bounds(bounds)
    if refresh:
        historical_file_index.cache_clear()
    dataset = historical_file_index(mode).copy(deep=True)
    indexers = {}
    if ids is not None:
        indexers["station_id"] = ids
    if years is not None:
        indexers["year"] = years
    dataset = dataset.reindex(indexers, fill_value={"available": False, "url": ""})
    try:
        metadata = get_stations(refresh=refresh)
    except Exception as error:
        if bounds is not None:
            raise RuntimeError(
                "Station metadata is unavailable; geographic filtering cannot be applied"
            ) from error
        metadata = None
        warnings.warn(
            f"Archive availability returned without station metadata: {error}",
            UserWarning,
            stacklevel=2,
        )
    return _filter_bounds(_attach_metadata(dataset, metadata), bounds)


def plot_map(dataset, variable=None, *, ax=None, labels="auto"):
    """Plot station locations, optionally colored by one value per station.

    Accepts catalog or observation datasets, including scalar station selections.
    Select a time or explicitly reduce other dimensions before coloring.
    Returns a Matplotlib ``(figure, axes)`` pair.
    """
    from ._plotting import plot_station_map

    return plot_station_map(dataset, variable, ax=ax, labels=labels)

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
    """Normalize dataset or array IDs into unique strings in first-seen order.

    Args:
        values: Dataset with station_id coordinates, string, iterable, or DataArray.

    Returns:
        Nonempty lowercase station ID strings with surrounding whitespace removed.

    Raises:
        ValueError: If coordinates are absent, IDs are empty, multidimensional, or invalid.
        TypeError: If any ID is not a string.
    """
    if isinstance(values, xr.Dataset):
        if "station_id" not in values.coords:
            raise ValueError("Station datasets require a station_id coordinate")
        values = values.station_id
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
    """Normalize integer archive years into a sorted, unique list.

    Raises:
        TypeError: If years are not integers; booleans are not years.
        ValueError: If the selection is empty or years are not four-digit values.
    """
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
    """Select stations inside validated bounds, preserving variable dtypes.

    Unknown coordinates fail the mask; west greater than east crosses the dateline.
    """
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


def stations(station_ids=None, *, bounds=None, refresh=False) -> xr.Dataset:
    """Find stations by geographic bounds or known IDs.

    Args:
        station_ids: Optional ID string, iterable of strings, or ID DataArray.
            Unknown IDs are omitted; None includes all catalog stations.
        bounds: Optional dictionary with north, south, west, and east in degrees.
            West greater than east crosses the antimeridian. Combined with IDs,
            both filters apply. Unknown locations cannot match geographic bounds.
        refresh: Reload NOAA's catalog instead of using its in-memory cached copy.

    Returns:
        An xarray Dataset indexed by station_id, with latitude/longitude coordinates
        and name, owner, station_type, and notes. Locations describe the current
        catalog, not necessarily historical deployments. No matches returns an
        empty dataset. Pass the result directly to historical() or realtime().

    Raises:
        ValueError: If IDs or geographic bounds are invalid.
        TypeError: If IDs are not strings.
        OSError: If the station catalog cannot be retrieved from NOAA.

    Examples:
        >>> selected = xndbc.stations(["44013", "41043"])
        >>> data = xndbc.historical(selected, years=2020)
    """
    ids = _normalize_station_ids(station_ids) if station_ids is not None else None
    bounds = _validate_bounds(bounds)
    dataset = get_stations(refresh=refresh)
    if ids is not None:
        dataset = dataset.sel(
            station_id=[s for s in ids if s in dataset.station_id.values]
        )
    return _filter_bounds(dataset, bounds)


def _attach_metadata(dataset, metadata):
    """Attach current catalog coordinates and descriptive fields by station ID.

    Missing catalogs or unknown IDs retain NaN coordinates. Returns a new dataset.
    """
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
    """Read historical archive file presence, optionally filtered by IDs and bounds.

    Args:
        station_ids: Optional station selection; absent files retain requested IDs.
        years: Optional year selection; None includes every indexed year.
        mode: Historical product code, default "stdmet".
        bounds: Optional named geographic bounds; requires known station locations.
        refresh: Reload archive indexes and current catalog instead of cached copies.

    Returns:
        An xarray Dataset with station_id/year dimensions, boolean available flags,
        and URLs. Absent files have False and an empty URL. Archive-only stations
        retain missing metadata unless geographic filtering excludes them.

    Raises:
        ValueError: If selectors or product are invalid.
        TypeError: If IDs or years have unsupported types.
        RuntimeError: If bounds require station metadata that cannot be retrieved.
        OSError: If the archive index cannot be retrieved.

    Only indexes and metadata are retrieved. File presence does not measure valid
    observations; public callers use the dataset availability() accessor.
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

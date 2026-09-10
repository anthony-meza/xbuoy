"""Discover and cache NOAA stations and historical file URLs."""

import re
from functools import lru_cache

import numpy as np
import xarray as xr

from . import _http
from ._parsing.stations import parse_station_table

HISTORICAL_ROOT = "https://www.ndbc.noaa.gov/data/historical"
STATION_TABLE_URL = "https://www.ndbc.noaa.gov/data/stations/station_table.txt"


# Enough for the supported products, while keeping arbitrary internal calls bounded.
@lru_cache(maxsize=16)
def historical_file_index(mode: str) -> xr.Dataset:
    """Read and cache a product's NOAA archive index.

    Args:
        mode: Validated historical product code used in the archive directory URL.

    Returns:
        An xarray Dataset indexed by station_id and year, containing boolean
        available flags and URLs. Missing combinations are False and empty strings.
        The last duplicate link wins. This cached dataset must not be mutated;
        callers copy it or construct selections before modifying results.

    Raises:
        OSError: If the NOAA directory listing cannot be downloaded.
    """
    root = f"{HISTORICAL_ROOT}/{mode}/"
    rows = []
    for filename in re.findall(r'href="([^"/]+\.txt\.gz)"', _http.read_noaa_text(root)):
        # NOAA names files with a station ID, one product letter, and a four-digit year.
        match = re.fullmatch(r"([a-zA-Z0-9]+)[a-z](\d{4})\.txt\.gz", filename)
        if match:
            station, year = match.groups()
            rows.append((station.lower(), int(year), root + filename))
    stations = sorted({row[0] for row in rows})
    years = sorted({row[1] for row in rows})
    station_index = {value: i for i, value in enumerate(stations)}
    year_index = {value: i for i, value in enumerate(years)}
    urls = np.full(
        (len(stations), len(years)),
        "",
        dtype=f"U{max((len(r[2]) for r in rows), default=1)}",
    )
    for station, year, url in rows:
        urls[station_index[station], year_index[year]] = url
    return xr.Dataset(
        {
            "available": (("station_id", "year"), urls != ""),
            "url": (("station_id", "year"), urls),
        },
        coords={
            "station_id": np.asarray(stations, dtype=str),
            "year": np.asarray(years, dtype=int),
            "mode": mode,
        },
        attrs={
            "source": root,
            "description": "Archive file presence, not measurement completeness",
        },
    )


@lru_cache(maxsize=1)
def _station_catalog() -> xr.Dataset:
    """Download and parse the station catalog once per cache lifetime."""
    dataset = parse_station_table(_http.read_noaa_text(STATION_TABLE_URL))
    dataset.attrs["source"] = STATION_TABLE_URL
    return dataset


def get_stations(*, refresh=False) -> xr.Dataset:
    """Return a private copy so callers cannot change the cached catalog."""
    if refresh:
        _station_catalog.cache_clear()
    return _station_catalog().copy(deep=True)

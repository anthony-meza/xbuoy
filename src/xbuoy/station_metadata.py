"""
Station metadata retrieval for NOAA NDBC stations.
"""

import pandas as pd
import xarray as xr

NDBC_STATION_TABLE_URL = "https://www.ndbc.noaa.gov/data/stations/station_table.txt"


def _latitude_sign(direction: str) -> int:
    """Convert latitude direction to sign multiplier."""
    return 1 if direction == "N" else -1


def _longitude_sign(direction: str) -> int:
    """Convert longitude direction to sign multiplier."""
    return 1 if direction == "E" else -1


def _get_latitude(number: str, direction: str) -> float:
    """Convert latitude value and direction to signed float."""
    return float(number) * _latitude_sign(direction)


def _get_longitude(number: str, direction: str) -> float:
    """Convert longitude value and direction to signed float."""
    return float(number) * _longitude_sign(direction)


def get_buoy_metadata() -> xr.Dataset:
    """
    Fetch metadata for NDBC buoy stations from the public station table.

    Returns
    -------
    xr.Dataset
        Dataset indexed by station_id with NDBC station table fields.
    """
    stations = pd.read_csv(
        NDBC_STATION_TABLE_URL,
        sep="|",
        na_values="",
    ).iloc[1:].fillna(" ")

    stations.rename(columns={stations.columns[0]: "station_id"}, inplace=True)
    stations = stations.rename(columns=lambda x: x.strip())
    stations["station_id"] = stations["station_id"].astype(str).str.strip().str.lower()

    # Keep the package's existing "buoy station" behavior.
    stations = stations[stations.iloc[:, 2].str.lower().str.contains("buoy")]
    return stations.set_index("station_id").to_xarray()


def get_buoy_stations() -> xr.Dataset:
    """
    Get simplified buoy station information.

    Returns
    -------
    xr.Dataset
        Station locations and notes.
    """
    bmetadata = get_buoy_metadata().to_dataframe()

    buoy_stations = pd.DataFrame(index=bmetadata.index.astype(str))
    buoy_stations["notes"] = bmetadata["NOTE"]
    buoy_stations["latitude"] = bmetadata["LOCATION"].apply(
        lambda x: _get_latitude(x.split()[0], x.split()[1])
    )
    buoy_stations["longitude"] = bmetadata["LOCATION"].apply(
        lambda x: _get_longitude(x.split()[2], x.split()[3])
    )

    return buoy_stations.to_xarray()


def get_historical_bounds(station_id: str):
    """
    Return first and last available stdmet years for backward compatibility.
    """
    from .data_retrieval import list_available

    available = list_available(mode="stdmet").to_dataframe()
    years = available.loc[available["station_id"] == str(station_id).lower(), "year"]
    if years.empty:
        return {station_id: (pd.NA, pd.NA)}
    return {station_id: (str(years.min()), str(years.max()))}


def fetch_station_historical_bounds(station_ids: list[str]):
    """
    Return historical stdmet bounds for multiple stations.

    This compatibility helper derives bounds from the stdmet directory index
    instead of scraping each station history page.
    """
    from .data_retrieval import list_available

    available = list_available(mode="stdmet").to_dataframe()
    grouped = available.groupby("station_id")["year"].agg(["min", "max"])
    bounds = []
    for station_id in station_ids:
        key = str(station_id).lower()
        if key in grouped.index:
            row = grouped.loc[key]
            bounds.append({station_id: (str(row["min"]), str(row["max"]))})
        else:
            bounds.append({station_id: (pd.NA, pd.NA)})
    return bounds

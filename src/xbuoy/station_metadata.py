"""
Metadata retrieval for NDBC buoy stations.

This module provides functions to fetch and process metadata for NOAA NDBC buoy stations,
including station locations, available time ranges, and other station information.
"""

import warnings
import pandas as pd
import numpy as np
from ndbc_api import NdbcApi
import concurrent.futures
from typing import Union, Dict, Tuple, List
from tqdm import tqdm

# Suppress deprecation warnings from ndbc_api
warnings.filterwarnings('ignore', category=DeprecationWarning, module='ndbc_api')

# Initialize the NDBC API object
api = NdbcApi()


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


def get_historical_bounds(station_id: str) -> Dict[str, Tuple[str, str]]:
    """
    Retrieve the first and last available historical data years for a station.

    Parameters
    ----------
    station_id : str
        ID of the station.

    Returns
    -------
    dict
        Dictionary with station_id as the key and a tuple (min_year, max_year) as the value.
        If data retrieval fails, returns (np.nan, np.nan).
    """
    try:
        # Fetch available historical data as a DataFrame
        historical_df = api.available_historical(station_id=station_id, as_df=True)
        # Retain only the first row and drop columns with NA values
        historical_df = historical_df.iloc[[0], :].dropna(axis=1)
        # Extract years from the column names (excluding columns with spaces)
        available_historical = np.array([col for col in historical_df.columns if " " not in col])

        return {station_id: (min(available_historical), max(available_historical))}
    except Exception:
        return {station_id: (np.nan, np.nan)}


def fetch_station_historical_bounds(station_ids: List[str]) -> List[Dict[str, Tuple[str, str]]]:
    """
    Fetch the historical bounds (min and max years) for multiple stations using parallel processing.

    Parameters
    ----------
    station_ids : list of str
        List of station IDs to fetch historical bounds for.

    Returns
    -------
    list of dict
        A list of dictionaries, each containing the station ID as the key and
        a tuple (min_year, max_year) as the value.
    """
    # Use ThreadPoolExecutor for parallel processing with progress bar
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Submit all tasks
        futures = {executor.submit(get_historical_bounds, sid): sid for sid in station_ids}

        # Collect results with progress bar
        observation_bounds = []
        for future in tqdm(
            concurrent.futures.as_completed(futures),
            total=len(station_ids),
            desc="Fetching station metadata",
            unit="station"
        ):
            observation_bounds.append(future.result())

    return observation_bounds


def get_buoy_metadata() -> pd.DataFrame:
    """
    Fetch metadata for all NDBC buoy stations.

    Returns
    -------
    pd.DataFrame
        DataFrame containing station metadata including location, observation bounds,
        and other station information. Index is station_id.
    """
    # Load the station data, skip the first row, and replace NaN with a space
    stations = pd.read_csv(
        "https://www.ndbc.noaa.gov/data/stations/station_table.txt",
        sep="|",
        na_values=""
    ).iloc[1:].fillna(" ")

    # Rename the first column to 'station_id'
    stations.rename(columns={stations.columns[0]: "station_id"}, inplace=True)

    # Filter stations to only include buoys
    stations = stations[stations.iloc[:, 2].str.lower().str.contains("buoy")]

    # Extract station IDs and convert them to strings
    station_id = stations.iloc[:, 0].astype(str).tolist()

    # Fetch observation bounds for all stations
    observation_bounds = fetch_station_historical_bounds(station_id)

    # Convert the list of dicts into a single dict
    observation_bounds_dict = {k: v for d in observation_bounds for k, v in d.items()}

    # Create a DataFrame, filter out stations with NaN bounds
    observation_bounds_df = pd.DataFrame(observation_bounds_dict).dropna(axis=1)

    # Filter the stations DataFrame to include only stations with valid bounds
    stations_filt = stations[stations['station_id'].isin(observation_bounds_df.columns)]

    # Reshape the bounds DataFrame and merge it with the filtered stations DataFrame
    observation_bounds_filt = (
        observation_bounds_df.T
        .reset_index()
        .rename(columns={"index": "station_id", 0: "min_year", 1: "max_year"})
    )

    # Set station_id as the index for merging
    stations_filt.set_index("station_id", inplace=True)
    observation_bounds_filt.set_index("station_id", inplace=True)

    # Merge the filtered stations with their corresponding observation bounds
    stations_filt = stations_filt.merge(observation_bounds_filt, left_index=True, right_index=True)
    stations_filt = stations_filt.rename(columns=lambda x: x.strip())

    return stations_filt


def get_buoy_stations(data_format: str = "xarray") -> Union[pd.DataFrame, 'xr.Dataset']:
    """
    Get a simplified dataset of buoy station information.

    Parameters
    ----------
    data_format : str, optional
        Format of returned data. Either "xarray" (default) or "pandas".

    Returns
    -------
    xr.Dataset or pd.DataFrame
        Dataset containing station locations (latitude, longitude), time bounds
        (min_year, max_year), and notes.
    """
    bmetadata = get_buoy_metadata()

    # Create simplified station dataset
    buoy_stations = bmetadata[["min_year", "max_year"]].astype(float)
    buoy_stations['notes'] = bmetadata['NOTE']
    buoy_stations["latitude"] = bmetadata["LOCATION"].apply(
        lambda x: _get_latitude(x.split()[0], x.split()[1])
    )
    buoy_stations["longitude"] = bmetadata["LOCATION"].apply(
        lambda x: _get_longitude(x.split()[2], x.split()[3])
    )
    buoy_stations.index = buoy_stations.index.astype(str)

    if data_format == "xarray":
        return buoy_stations.to_xarray()
    else:
        return buoy_stations

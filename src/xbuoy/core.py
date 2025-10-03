"""
High-level user-facing API for xbuoy.

This module provides simplified functions that combine multiple backend operations
into easy-to-use interfaces for common workflows.
"""

import xarray as xr
import pandas as pd
from typing import List, Union, Optional

from .station_metadata import get_buoy_stations as _get_stations_metadata
from .data_retrieval import get_station_records as _fetch_records
from .data_processing import add_latitude_longitude, compute_data_coverage
from .geographic_filters import box_filter_buoys


def list_stations(
    region: Optional[dict] = None,
    data_format: str = "xarray"
) -> Union[xr.Dataset, pd.DataFrame]:
    """
    Get a list of all available NDBC buoy stations with their metadata.

    Parameters
    ----------
    region : dict, optional
        Geographic bounding box to filter stations. Should contain keys:
        'lon_min', 'lon_max', 'lat_min', 'lat_max'.
        If None, returns all stations globally.
    data_format : str, optional
        Format of returned data: "xarray" (default) or "pandas".

    Returns
    -------
    xr.Dataset or pd.DataFrame
        Dataset containing station locations (latitude, longitude),
        time bounds (min_year, max_year), and notes.

    Examples
    --------
    Get all stations:
    >>> stations = xbuoy.list_stations()

    Get stations in the Caribbean:
    >>> caribbean = xbuoy.list_stations(
    ...     region={'lon_min': -85, 'lon_max': -60, 'lat_min': 10, 'lat_max': 25}
    ... )
    """
    stations = _get_stations_metadata(data_format=data_format)

    # Apply geographic filter if specified
    if region is not None and data_format == "xarray":
        stations = box_filter_buoys(
            stations,
            lon1=region.get('lon_min', -180),
            lon2=region.get('lon_max', 180),
            lat1=region.get('lat_min', -90),
            lat2=region.get('lat_max', 90)
        )

    return stations


def fetch_data(
    station_ids: Union[str, List[str]],
    years: Union[int, List[int]],
    sample_rate: str = "D",
    add_location: bool = True
) -> xr.Dataset:
    """
    Fetch historical buoy data for specified stations and years.

    This is the main function for retrieving buoy observational data. It handles
    data download and optionally adds location coordinates.

    Parameters
    ----------
    station_ids : str or list of str
        Station ID(s) to fetch data for. Can be a single station ID or a list.
    years : int or list of int
        Year(s) to fetch data for. Can be a single year or a list/range.
    sample_rate : str, optional
        Temporal resampling rate (default: "D" for daily).
        Options: "D" (daily), "W" (weekly), "M" (monthly), "H" (hourly).
    add_location : bool, optional
        Whether to add latitude/longitude coordinates to the dataset (default: True).

    Returns
    -------
    xr.Dataset
        Dataset containing buoy observations with time and station_id dimensions.

    Examples
    --------
    Fetch data for a single station and year:
    >>> data = xbuoy.fetch_data("tplm2", 2020)

    Fetch multiple years of data:
    >>> data = xbuoy.fetch_data("tplm2", range(2015, 2021))

    Fetch data from multiple stations:
    >>> data = xbuoy.fetch_data(["tplm2", "44013"], range(2018, 2021))

    Fetch with weekly averaging:
    >>> data = xbuoy.fetch_data("tplm2", 2020, sample_rate="W")

    Compute coverage after fetching:
    >>> data = xbuoy.fetch_data("tplm2", range(2015, 2021))
    >>> data = xbuoy.compute_data_coverage(data, variable="WTMP")
    """
    # Normalize inputs to lists
    if isinstance(station_ids, str):
        station_ids = [station_ids]
    if isinstance(years, int):
        years = [years]
    elif isinstance(years, range):
        years = list(years)

    # Fetch the data
    dataset = _fetch_records(
        station_list=station_ids,
        years=years,
        sample_rate=sample_rate,
        debugging=False
    )

    # Add location coordinates if requested
    if add_location:
        reference_stations = _get_stations_metadata(data_format="xarray")
        dataset = add_latitude_longitude(dataset, reference_stations)

    return dataset


def filter_by_region(
    ds: xr.Dataset,
    lon_min: float = -180,
    lon_max: float = 180,
    lat_min: float = -90,
    lat_max: float = 90
) -> xr.Dataset:
    """
    Filter buoy dataset to a specific geographic region.

    Parameters
    ----------
    ds : xr.Dataset
        The dataset to filter.
    lon_min, lon_max : float, optional
        Longitude bounds (default: global coverage).
    lat_min, lat_max : float, optional
        Latitude bounds (default: global coverage).

    Returns
    -------
    xr.Dataset
        Filtered dataset containing only stations within the specified region.

    Examples
    --------
    Filter to US East Coast:
    >>> east_coast = xbuoy.filter_by_region(data, lon_min=-80, lon_max=-65,
    ...                                      lat_min=25, lat_max=45)
    """
    return box_filter_buoys(ds, lon1=lon_min, lon2=lon_max, lat1=lat_min, lat2=lat_max)

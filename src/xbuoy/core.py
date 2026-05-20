"""
High-level user-facing API for xbuoy.

This module provides simplified functions that combine multiple backend operations
into easy-to-use interfaces for common workflows.
"""

import xarray as xr
from typing import List, Union, Optional

from .geographic_filters import box_filter_buoys


def list_stations(
    region: Optional[dict] = None,
) -> xr.Dataset:
    """
    Get a list of all available NDBC buoy stations with their metadata.

    Parameters
    ----------
    region : dict, optional
        Geographic bounding box to filter stations. Should contain keys:
        'lon_min', 'lon_max', 'lat_min', 'lat_max'.
        If None, returns all stations globally.
    Returns
    -------
    xr.Dataset
        Dataset containing station locations (latitude, longitude) and notes.

    Examples
    --------
    Get all stations:
    >>> stations = xbuoy.list_stations()

    Get stations in the Caribbean:
    >>> caribbean = xbuoy.list_stations(
    ...     region={'lon_min': -85, 'lon_max': -60, 'lat_min': 10, 'lat_max': 25}
    ... )
    """
    from .station_metadata import get_buoy_stations as _get_stations_metadata

    stations = _get_stations_metadata()

    # Apply geographic filter if specified
    if region is not None:
        stations = box_filter_buoys(
            stations,
            lon1=region.get('lon_min', -180),
            lon2=region.get('lon_max', 180),
            lat1=region.get('lat_min', -90),
            lat2=region.get('lat_max', 90)
        )

    return stations


def list_available(mode: Optional[str] = "stdmet") -> xr.Dataset:
    """
    List available NDBC historical files.

    Parameters
    ----------
    mode : str, optional
        Historical data mode to list. Use None to list all modes.

    Returns
    -------
    xr.Dataset
        Availability dataset with one row per historical file.
    """
    from .data_retrieval import list_available as _list_available

    return _list_available(mode=mode)


def fetch_data(
    station_ids: Union[str, List[str]],
    years: Optional[Union[int, List[int]]] = None,
    sample_rate: str = "D",
    add_location: bool = True,
    data_type: str = "historical",
    mode: Union[str, List[str]] = "stdmet",
    max_workers: int = 6,
) -> xr.Dataset:
    """
    Fetch historical or realtime buoy data for specified stations.

    This is the main function for retrieving buoy observational data. It handles
    data download and optionally adds location coordinates.

    Parameters
    ----------
    station_ids : str or list of str
        Station ID(s) to fetch data for. Can be a single station ID or a list.
    years : int or list of int, optional
        Year(s) to fetch data for. Can be a single year or a list/range.
        Required for historical data and ignored for realtime data.
    sample_rate : str, optional
        Temporal resampling rate (default: "D" for daily).
        Options: "D" (daily), "W" (weekly), "M" (monthly), "H" (hourly).
    add_location : bool, optional
        Whether to add latitude/longitude coordinates to the dataset (default: True).
    data_type : {"historical", "realtime"}, optional
        Which NDBC feed to retrieve. Historical data is the default.
    mode : str or list of str, optional
        Which NDBC data mode(s) to retrieve (default is "stdmet").
    max_workers : int, optional
        Maximum number of concurrent file reads per station.

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

    Fetch realtime data:
    >>> data = xbuoy.fetch_data("tplm2", data_type="realtime", sample_rate="H")

    Compute coverage after fetching:
    >>> data = xbuoy.fetch_data("tplm2", range(2015, 2021))
    >>> data = xbuoy.compute_data_coverage(data, variable="WTMP")
    """
    from .data_processing import add_latitude_longitude
    from .data_retrieval import get_station_records as _fetch_records
    from .station_metadata import get_buoy_stations as _get_stations_metadata

    # Normalize inputs to lists
    if isinstance(station_ids, str):
        station_ids = [station_ids]
    station_ids = [str(station_id).lower() for station_id in station_ids]
    data_type = data_type.lower()
    if isinstance(mode, str):
        mode = mode.lower()
    else:
        mode = [m.lower() for m in mode]
    if years is not None:
        if isinstance(years, int):
            years = [years]
        elif isinstance(years, range):
            years = list(years)

    # Fetch the data
    dataset = _fetch_records(
        station_list=station_ids,
        years=years,
        sample_rate=sample_rate,
        debugging=False,
        data_type=data_type,
        mode=mode,
        max_workers=max_workers,
    )

    # Add location coordinates if requested
    if add_location:
        reference_stations = _get_stations_metadata()
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

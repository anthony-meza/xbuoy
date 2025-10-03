"""
Geographic filtering functions for buoy datasets.

This module provides functions to filter buoy station datasets based on
geographic criteria such as bounding boxes and regions.
"""

import xarray as xr


def box_filter_buoys(
    ds: xr.Dataset,
    lon1: float = -180,
    lon2: float = 180,
    lat1: float = -90,
    lat2: float = 90
) -> xr.Dataset:
    """
    Filter the dataset to include only stations within a specified geographic box.

    Parameters
    ----------
    ds : xr.Dataset
        The dataset containing station data with latitude and longitude coordinates.
    lon1 : float, optional
        Minimum longitude bound for the box filter (default: -180).
    lon2 : float, optional
        Maximum longitude bound for the box filter (default: 180).
    lat1 : float, optional
        Minimum latitude bound for the box filter (default: -90).
    lat2 : float, optional
        Maximum latitude bound for the box filter (default: 90).

    Returns
    -------
    xr.Dataset
        Filtered dataset containing only stations within the specified geographic box.

    Examples
    --------
    Filter buoys in the Caribbean region:
    >>> caribbean_buoys = box_filter_buoys(ds, lon1=-85, lon2=-60, lat1=10, lat2=25)

    Filter buoys along the US East Coast:
    >>> east_coast = box_filter_buoys(ds, lon1=-80, lon2=-65, lat1=25, lat2=45)
    """
    # Create a boolean mask for the longitude and latitude conditions
    longitude_box = (ds.longitude >= lon1) * (ds.longitude <= lon2)
    latitude_box = (ds.latitude >= lat1) * (ds.latitude <= lat2)

    # Apply the mask to the dataset and drop stations outside the specified box
    return ds.where(longitude_box * latitude_box, drop=True)

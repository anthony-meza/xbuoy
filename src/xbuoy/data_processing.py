"""
Data processing and analysis functions for buoy datasets.

This module provides functions to add derived variables, compute coverage statistics,
and enhance buoy datasets with additional metadata.
"""

import xarray as xr
import numpy as np
from typing import Optional


def add_latitude_longitude(xsdf: xr.Dataset, reference_station_ds: xr.Dataset) -> xr.Dataset:
    """
    Add latitude and longitude coordinates to the dataset based on a reference dataset.

    Parameters
    ----------
    xsdf : xr.Dataset
        Dataset containing station data.
    reference_station_ds : xr.Dataset
        Reference dataset containing latitude and longitude for stations.

    Returns
    -------
    xr.Dataset
        Dataset with added latitude and longitude coordinates.
    """
    xsdf["latitude"] = reference_station_ds.sel(station_id=xsdf.station_id).latitude
    xsdf["longitude"] = reference_station_ds.sel(station_id=xsdf.station_id).longitude

    return xsdf


def add_variable_coverage(xsdf: xr.Dataset, varname: str = "WTMP") -> xr.Dataset:
    """
    Add a data coverage variable representing the percentage of valid data.

    Parameters
    ----------
    xsdf : xr.Dataset
        Dataset containing station data.
    varname : str, optional
        Name of the variable to compute coverage for (default is "WTMP").

    Returns
    -------
    xr.Dataset
        Dataset with added coverage variable named "{varname}_coverage".

    Examples
    --------
    >>> ds = add_variable_coverage(ds, varname="WTMP")
    >>> ds = add_variable_coverage(ds, varname="WSPD")
    """
    numerator = (~np.isnan(xsdf[varname])).sum(dim="time")
    denominator = len(xsdf.time)
    xsdf[f"{varname}_coverage"] = 100 * numerator / denominator
    xsdf[f"{varname}_coverage"].attrs["description"] = (
        f"percentage of existing {varname} data across specified interval length"
    )

    return xsdf


def compute_data_coverage(ds: xr.Dataset, variable: str = "WTMP") -> xr.Dataset:
    """
    Compute data coverage percentage for a variable.

    This is an alias for add_variable_coverage with a clearer name.

    Parameters
    ----------
    ds : xr.Dataset
        Dataset containing station data.
    variable : str, optional
        Name of the variable to compute coverage for (default is "WTMP").

    Returns
    -------
    xr.Dataset
        Dataset with added coverage variable named "{variable}_coverage".
    """
    return add_variable_coverage(ds, varname=variable)

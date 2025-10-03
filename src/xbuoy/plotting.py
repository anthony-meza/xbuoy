"""
Visualization functions for buoy station data.

This module provides functions to create maps and visualizations of buoy station
locations and their associated data variables.
"""

import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import xarray as xr
from typing import Tuple


def plot_stations(ds: xr.Dataset, variable: str = None) -> Tuple[plt.Figure, plt.Axes]:
    """
    Plot buoy station locations on a map, optionally colored by a data variable.

    Parameters
    ----------
    ds : xr.Dataset
        The dataset containing station data with latitude and longitude coordinates.
    variable : str, optional
        Name of a data variable to use for coloring the station points.
        If None, plots simple station locations. Common variables: 'WTMP', 'wtemp_coverage'.

    Returns
    -------
    tuple of (Figure, Axes)
        A tuple containing the figure and axis objects of the plot.

    Examples
    --------
    Plot station locations:
    >>> fig, ax = plot_stations(stations)

    Plot stations colored by water temperature coverage:
    >>> fig, ax = plot_stations(data, variable='wtemp_coverage')
    """
    # Create a figure and axis with a Plate Carree projection
    fig, ax = plt.subplots(subplot_kw={'projection': ccrs.PlateCarree()})

    if variable is None:
        # Plot each station's location as a simple scatter point
        for station in ds.station_id:
            station_coords = ds.sel(station_id=station)
            ax.scatter(station_coords.longitude, station_coords.latitude,
                      transform=ccrs.PlateCarree())
    else:
        # Plot stations colored by the specified variable
        cm = ax.scatter(ds.longitude, ds.latitude, c=ds[variable].values,
                       transform=ccrs.PlateCarree())
        # Add a colorbar to indicate the range of the variable
        fig.colorbar(cm, label=variable)

    # Add coastlines to the map with some transparency
    ax.coastlines(alpha=0.5)

    # Add gridlines with labels on the map, disabling top and right labels
    gl = ax.gridlines(crs=ccrs.PlateCarree(), draw_labels=True, alpha=0.0)
    gl.top_labels = False
    gl.right_labels = False

    return fig, ax

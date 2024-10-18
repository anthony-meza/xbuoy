import pandas as pd
import numpy as np
import xarray as xr
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.mpl.ticker as cticker
from ndbc_api import NdbcApi
import concurrent.futures
import os 


def plot_stations(ds):
    """
    Plots the locations of stations on a map using their latitude and longitude.
    
    Parameters:
    ds (xarray.Dataset): The dataset containing station data with latitude and longitude coordinates.
    
    Returns:
    tuple: A tuple containing the figure and axis objects of the plot.
    """
    # Create a figure and axis with a Plate Carree projection (flat map projection)
    fig, ax = plt.subplots(subplot_kw={'projection': ccrs.PlateCarree()})

    # Plot each station's location as a scatter point
    for station in ds.station_id:
        station_coords = ds.sel(station_id=station)
        ax.scatter(station_coords.longitude, station_coords.latitude, transform=ccrs.PlateCarree())

    # Add coastlines to the map with some transparency
    ax.coastlines(alpha=0.5)

    # Add gridlines with labels on the map, disabling top and right labels
    gl = ax.gridlines(crs=ccrs.PlateCarree(), draw_labels=True, alpha=0.0)
    gl.top_labels = False
    gl.right_labels = False

    return fig, ax

def plot_stations_variable(ds, var="WTMP"):
    """
    Plots the locations of stations on a map and colors them based on the value of a specified variable.
    
    Parameters:
    ds (xarray.Dataset): The dataset containing station data with latitude, longitude, and the specified variable.
    var (str): The name of the variable to use for coloring the station points (default: 'WTMP' for water temperature).
    
    Returns:
    tuple: A tuple containing the figure and axis objects of the plot.
    """
    # Create a figure and axis with a Plate Carree projection
    fig, ax = plt.subplots(subplot_kw={'projection': ccrs.PlateCarree()})

    # Plot stations' locations as scatter points colored by the specified variable
    cm = ax.scatter(ds.longitude, ds.latitude, c=ds[var].values, transform=ccrs.PlateCarree())

    # Add coastlines to the map with some transparency
    ax.coastlines(alpha=0.5)

    # Add gridlines with labels on the map, disabling top and right labels
    gl = ax.gridlines(crs=ccrs.PlateCarree(), draw_labels=True, alpha=0.0)
    gl.top_labels = False
    gl.right_labels = False
    
    # Add a colorbar to the figure to indicate the range of the variable
    fig.colorbar(cm)
    
    return fig, ax

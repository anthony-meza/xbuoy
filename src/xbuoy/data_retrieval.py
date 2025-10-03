"""
Data retrieval functions for NDBC buoy observations.

This module provides functions to fetch historical observational data from NOAA NDBC buoys,
including temperature, wave, wind, and other oceanographic measurements.
"""

import warnings
import pandas as pd
import numpy as np
import xarray as xr
from ndbc_api import NdbcApi
import concurrent.futures
import os
from typing import List, Optional
from tqdm import tqdm

# Suppress deprecation warnings from ndbc_api
warnings.filterwarnings('ignore', category=DeprecationWarning, module='ndbc_api')

# Initialize the NDBC API object
api = NdbcApi()


def has_extra_headers(url: str) -> bool:
    """
    Check if the given URL's CSV file contains extra header rows.

    Parameters
    ----------
    url : str
        URL to the CSV file.

    Returns
    -------
    bool
        True if the second line contains alphabetic characters, indicating extra headers.
    """
    # Read the first line of the file
    first_line = pd.read_csv(url, delim_whitespace=True, nrows=1).values[0]
    # Check if the second line has alphabetic characters, indicating headers
    return any(~np.isreal(char) for char in first_line)


def extract_historical_year(
    yr: int,
    station_id: str = 'tplm2',
    sample_rate: str = "D",
    display_error: bool = False
) -> Optional[xr.Dataset]:
    """
    Extract and process historical data for a specific year and station.

    Parameters
    ----------
    yr : int
        Year to extract data for.
    station_id : str, optional
        ID of the station (default is 'tplm2').
    sample_rate : str, optional
        Resampling rate for pandas resample (default is daily "D").
        Examples: "D" (daily), "W" (weekly), "M" (monthly).
    display_error : bool, optional
        Whether to print error messages (default is False).

    Returns
    -------
    xr.Dataset or None
        Processed data resampled to the specified sample rate.
        Returns None if data extraction fails.
    """
    try:
        # Column name mappings for date/time fields
        replace_names = {
            'YY': "year", "#YY": "year", "YYYY": "year",
            'MM': "month", "DD": 'day', 'hh': 'hour', 'mm': "minute"
        }

        # Fetch available historical data as a DataFrame
        historical_df = api.available_historical(station_id=station_id, as_df=True)

        # Get the link for the specific year
        slink = historical_df[str(int(yr))].iloc[0]
        slink = slink.replace("download_data", "view_text_file")

        # Check if the file has extra headers and read it accordingly
        if has_extra_headers(slink):
            sdf = pd.read_csv(slink, delimiter=r"\s+", skiprows=[1])
        else:
            sdf = pd.read_csv(slink, delimiter=r"\s+")

        # If "WTMP" (water temperature) is not in the columns, return None
        if ("WTMP" not in sdf.columns) and display_error:
            print(f"WTMP not found for station {station_id}, year {yr}")
            return None

        # Replace invalid values (99, 999, 9999) with NaN
        sdf = sdf.replace([99, 999, 9999], np.nan)

        # Adjust year column if it uses a two-digit format
        if "YY" in sdf.columns:
            sdf["YY"] = 1900 + sdf["YY"]

        # Ensure 'mm' and 'hh' columns are present, fill missing with default values
        sdf["mm"] = 0 if "mm" not in sdf.columns else sdf["mm"]
        sdf["hh"] = 1 if 'hh' not in sdf.columns else sdf["hh"]

        # Rename columns based on the mapping dictionary
        sdf = sdf.rename(columns=replace_names)

        # Convert the date-related columns to a datetime object
        dt_cols = ["year", "month", "day", "hour", "minute"]
        sdf['time'] = pd.to_datetime(sdf[dt_cols])

        # Drop date-related columns and set 'time' as the index
        sdf = sdf.drop(columns=dt_cols).set_index("time")

        # Convert the DataFrame to an xarray Dataset, sort by time, and resample
        return sdf.to_xarray().sortby("time").resample(time=sample_rate).mean("time")

    except Exception as e:
        if display_error:
            print(f"Error extracting data for station {station_id}, year {yr}: {e}")
        return None


def get_station_records(
    station_list: List[str],
    years: List[int],
    sample_rate: str = "D",
    debugging: bool = False
) -> xr.Dataset:
    """
    Retrieve and process historical records for multiple stations and years.

    This function fetches data in parallel for efficiency and combines all
    station records into a single xarray Dataset.

    Parameters
    ----------
    station_list : list of str
        List of station IDs to fetch data for.
    years : list of int
        List of years to extract data for.
    sample_rate : str, optional
        Resampling rate (default is daily "D").
    debugging : bool, optional
        If True, processes data sequentially for easier debugging (default is False).

    Returns
    -------
    xr.Dataset
        Merged dataset containing historical records for all stations and years.
        Includes a 'station_id' dimension.
    """
    # Determine the number of workers for parallel processing
    max_workers = max(os.cpu_count() - 1, 1)

    # List to store the results for each station
    xxsdf = []

    # Iterate through each station with a progress bar
    for station_id in tqdm(station_list, desc="Fetching stations", unit="station"):
        # Define a lambda function to process each year for the current station
        particular_historical_record = lambda yr: extract_historical_year(
            yr, station_id=station_id, sample_rate=sample_rate
        )

        # If debugging is enabled, process the data sequentially
        if debugging:
            results = []
            for yr in years:
                results.append(particular_historical_record(yr))
        else:
            # Use ThreadPoolExecutor for parallel processing of years
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                results = list(executor.map(particular_historical_record, years))

        # Filter out None results
        results = [r for r in results if r is not None]

        # If there are multiple results, concatenate them and handle duplicates
        if len(results) > 1:
            xsdf = xr.concat(results, dim="time").sortby("time")
            xsdf = xsdf.drop_duplicates("time")  # sometimes the records overlap
            xsdf = xsdf.assign_coords(station_id=station_id).expand_dims("station_id")
            xxsdf.append(xsdf)

    # Merge the results for all stations into a single xarray Dataset
    return xr.merge(xxsdf)

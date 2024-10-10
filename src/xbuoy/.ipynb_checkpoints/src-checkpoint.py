import pandas as pd
import numpy as np
import xarray as xr
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.mpl.ticker as cticker
from ndbc_api import NdbcApi
import concurrent.futures
from tqdm.contrib.concurrent import process_map, thread_map
from tqdm.autonotebook import tqdm
import os 

# Initialize the NDBC API object
api = NdbcApi()


latitude_sign = lambda x: 1 if x == "N" else -1
longitude_sign = lambda x: 1 if x == "E" else -1
get_latitude = lambda number, direction: float(number) * latitude_sign(direction)
get_longitude = lambda number, direction: float(number) * longitude_sign(direction)

def get_buoy_metadata():
    # Load the station data, skip the first row, and replace NaN with a space
    stations = pd.read_csv("https://www.ndbc.noaa.gov/data/stations/station_table.txt", sep="|", na_values="").iloc[1:].fillna(" ")
    
    # Rename the first column to 'station_id'
    stations.rename(columns={stations.columns[0]: "station_id"}, inplace=True)
    
    # Filter stations to only include buoys
    stations = stations[stations.iloc[:, 2].str.lower().str.contains("buoy")]
    
    # Extract station IDs and convert them to strings
    station_id = stations.iloc[:, 0].astype(str).tolist()
    
    # Extract and convert latitude and longitude
    station_location = stations.iloc[:, 6]
    station_latitude = [get_latitude(loca.split()[0], loca.split()[1]) for loca in station_location]
    station_longitude = [get_longitude(loca.split()[2], loca.split()[3]) for loca in station_location]
    
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


def get_buoy_stations(data_format = "xarray"):

    bmetadata = get_buoy_metadata()
    #space_time_data
    buoy_stations = bmetadata[["min_year", "max_year"]].astype(float)
    buoy_stations['notes'] = bmetadata['NOTE']
    buoy_stations["latitude"] = bmetadata["LOCATION"].apply(lambda x: get_latitude(x.split()[0], x.split()[1]))
    buoy_stations["longitude"] = bmetadata["LOCATION"].apply(lambda x: get_longitude(x.split()[2], x.split()[3]))
    buoy_stations.index = buoy_stations.index.astype(str)

    if data_format == "xarray":
        return buoy_stations.to_xarray()
    else:
        return buoy_stations

def box_filter_buoys(ds, lon1=-180, lon2=180, lat1=-90, lat2=90):
    """
    Filters the dataset to include only stations within a specified geographic box.
    
    Parameters:
    ds (xarray.Dataset): The dataset containing station data with latitude and longitude coordinates.
    lon1, lon2 (float): Longitude bounds for the box filter (default: global coverage from -180 to 180).
    lat1, lat2 (float): Latitude bounds for the box filter (default: global coverage from -90 to 90).
    
    Returns:
    xarray.Dataset: Filtered dataset containing only stations within the specified geographic box.
    """
    # Create a boolean mask for the longitude and latitude conditions
    longitude_box = (ds.longitude >= lon1) * (ds.longitude <= lon2)
    latitude_box = (ds.latitude >= lat1) * (ds.latitude <= lat2)

    # Apply the mask to the dataset and drop stations outside the specified box
    return ds.where(longitude_box * latitude_box, drop=True)

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

def has_extra_headers(url):
    """
    Checks if the given URL's CSV file contains extra headers.
    
    Parameters:
    url (str): URL to the CSV file.
    
    Returns:
    bool: True if the second line of the file contains alphabetic characters, indicating extra headers.
    """
    # Read the first line of the file
    first_line = pd.read_csv(url, delim_whitespace=True, nrows=1).values[0]
    # Check if the second line has alphabetic characters, indicating headers
    return any(~np.isreal(char) for char in first_line)

def get_historical_bounds(station_id):
    """
    Retrieves the first and last available historical data years for a given station.
    
    Parameters:
    station_id (str): ID of the station.
    
    Returns:
    dict: Dictionary with station_id as the key and a tuple (min year, max year) as the value.
    If data retrieval fails, returns (np.nan, np.nan).
    """
    try: 
        # Fetch available historical data as a DataFrame
        historical_df = api.available_historical(station_id=station_id, as_df=True)
        # Retain only the first row and drop columns with NA values
        historical_df = historical_df.iloc[[0], :].dropna(axis = 1)
        # Extract years from the column names (excluding columns with spaces)
        available_historical = np.array([col for col in historical_df.columns if not(" " in col)])
        
        return {station_id: (min(available_historical), max(available_historical))}
    except:
        return {station_id: (np.nan, np.nan)}

def extract_historical_year(yr, station_id='tplm2', sample_rate="D", display_error = False):
    """
    Extracts and processes historical temperature data for a specific year and station.
    
    Parameters:
    yr (int): Year to extract data for.
    station_id (str): ID of the station (default is 'tplm2').
    sample_rate (str): Resampling rate (default is daily "D").
    
    Returns:
    xarray.Dataset: Processed temperature data resampled to the specified sample rate.
    Returns None if data extraction fails.
    """
    try: 
        # Replace column name mappings
        replace_names = {'YY': "year", "#YY": "year", "YYYY": "year", 'MM': "month", 
                         "DD": 'day', 'hh': 'hour', 'mm': "minute"}
        
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
            print("WTMP not found")
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

    except: 
        return None

def get_station_records(station_list, years, sample_rate="D", debugging=False):
    """
    Retrieves and processes historical records for multiple stations and years.
    
    Parameters:
    station_list (list): List of station IDs.
    years (list): List of years to extract data for.
    sample_rate (str): Resampling rate (default is daily "D").
    debugging (bool): If True, processes data sequentially for debugging purposes.
    
    Returns:
    xarray.Dataset: Merged dataset containing historical records for all stations and years.
    """
    # Determine the number of workers for parallel processing
    max_workers = max(os.cpu_count() - 1, 1)

    # List to store the results for each station
    xxsdf = []
    i = 0
    
    # Iterate through each station in the station list
    for station_id in station_list:
        # Define a lambda function to process each year for the current station
        particular_historical_record = lambda yr: extract_historical_year(yr, station_id=station_id, sample_rate=sample_rate)
        
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
        
        # Print progress every 10 stations
        if (i % 10) == 0: 
            print(np.round(100 * i / len(station_list)), "% done")
        i += 1 
    
    # Merge the results for all stations into a single xarray Dataset
    return xr.merge(xxsdf)

def add_latitude_longitude(xsdf, reference_station_ds):
    """
    Adds latitude and longitude coordinates to the dataset based on a reference dataset.
    
    Parameters:
    xsdf (xarray.Dataset): Dataset containing station data.
    reference_station_ds (xarray.Dataset): Reference dataset containing latitude and longitude for stations.
    
    Returns:
    xarray.Dataset: Dataset with added latitude and longitude coordinates.
    """
    xsdf["latitude"] = reference_station_ds.sel(station_id=xsdf.station_id).latitude
    xsdf["longitude"] = reference_station_ds.sel(station_id=xsdf.station_id).longitude

    return xsdf

def add_wtemp_coverage(xsdf):
    """
    Adds a water temperature density variable to the dataset, representing the percentage of valid temperature data.
    
    Parameters:
    xsdf (xarray.Dataset): Dataset containing station data.
    
    Returns:
    xarray.Dataset: Dataset with added water temperature density variable.
    """
    numerator = (~np.isnan(xsdf["WTMP"])).sum(dim="time")
    denominator = len(xsdf.time)
    xsdf["wtemp_coverage"] = 100 * numerator / denominator
    xsdf["wtemp_coverage"].attrs["decription"] = "percentage of existing water temperature data across entire time interval length"

    return xsdf

def fetch_station_historical_bounds(station_ids):
    """
    Fetches the historical bounds (min and max years) for a list of station IDs using parallel processing.

    Parameters:
    station_ids (list): List of station IDs to fetch historical bounds for.

    Returns:
    list: A list of dictionaries, each containing the station ID as the key and a tuple (min_year, max_year) as the value.
    """
    # Use ThreadPoolExecutor for parallel processing of the get_historical_bounds function
    with concurrent.futures.ThreadPoolExecutor() as executor:
        observation_bounds = list(executor.map(get_historical_bounds, station_ids))

    return observation_bounds

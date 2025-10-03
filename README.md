# xbuoy

A Python package for accessing and analyzing NOAA NDBC buoy data. Built on top of [ndbc-api](https://github.com/CDJellen/ndbc-api), `xbuoy` provides a simple interface to fetch, process, and visualize oceanographic buoy observations as xarray datasets.

<img width="585" alt="Screenshot 2024-10-16 at 5 13 39 PM" src="https://github.com/user-attachments/assets/9a64a9b2-21a4-48b6-8452-36e5807dcc2f">

## Features

- 🌊 **Easy data access** - Fetch buoy data with just a few lines of code
- 📊 **xarray integration** - Work with familiar scientific Python tools
- 🗺️ **Geographic filtering** - Filter stations by region
- 📈 **Built-in visualization** - Create maps with Cartopy
- ⚡ **Parallel downloads** - Fast data retrieval using concurrent processing

## Installation

### Using pip (recommended for users)

```bash
pip install git+https://github.com/anthony-meza/xbuoy.git@main
```

### Using a virtual environment (recommended)

```bash
# Create a virtual environment
python -m venv xbuoy-env

# Activate the virtual environment
# On macOS/Linux:
source xbuoy-env/bin/activate
# On Windows:
xbuoy-env\Scripts\activate

# Install xbuoy
pip install git+https://github.com/anthony-meza/xbuoy.git@main
```

### For developers (using Poetry)

```bash
# Clone the repository
git clone https://github.com/anthony-meza/xbuoy.git
cd xbuoy

# Install dependencies with Poetry
poetry install

# Build the package
poetry build

# Install locally
pip install ./dist/xbuoy-X.X.X-py3-none-any.whl
```

## Quick Start

```python
import xbuoy

# List all available buoy stations
stations = xbuoy.list_stations()

# Filter to a specific region (e.g., Caribbean)
caribbean = xbuoy.list_stations(
    region={'lon_min': -85, 'lon_max': -60, 'lat_min': 10, 'lat_max': 25}
)

# Visualize station locations
fig, ax = xbuoy.plot_stations(caribbean)

# Fetch historical data for specific stations
data = xbuoy.fetch_data(
    station_ids=["tplm2", "44013"],
    years=range(2018, 2021),
    sample_rate="D"  # Daily averages
)

# Plot stations colored by data coverage
fig, ax = xbuoy.plot_stations(data, variable="wtemp_coverage")
```

## Core Functions

The package provides a simple, high-level API:

- **`list_stations()`** - Get metadata for all NDBC buoy stations
- **`fetch_data()`** - Download historical buoy observations
- **`filter_by_region()`** - Filter datasets by geographic bounds
- **`plot_stations()`** - Visualize station locations on a map

See the [getting started notebook](examples/getting_started.ipynb) for more examples.

## Examples

Check out the `examples/getting_started.ipynb` notebook for a comprehensive tutorial covering:
- Listing and filtering buoy stations
- Fetching historical data from NDBC
- Visualizing station locations on maps
- Computing temperature anomalies
- Working with multiple stations

To run the notebook:
```bash
pip install jupyter
jupyter notebook examples/getting_started.ipynb
```

## Advanced Usage

For advanced users, all backend functions are still accessible:

```python
from xbuoy import station_metadata, data_retrieval, data_processing

# Get detailed metadata
metadata = station_metadata.get_buoy_metadata()

# Low-level data retrieval
records = data_retrieval.get_station_records(
    station_list=["tplm2"],
    years=[2020],
    sample_rate="H"  # Hourly
)

# Add custom processing
processed = data_processing.compute_data_coverage(records, variable="WSPD")
```

## Contributing

Interested in contributing? Check out the contributing guidelines. Please note that this project is released with a Code of Conduct. By contributing to this project, you agree to abide by its terms.

## License

`xbuoy` was created by Anthony Meza. It is licensed under the terms of the MIT license.

## Credits

`xbuoy` was created with [`cookiecutter`](https://cookiecutter.readthedocs.io/en/latest/) and the `py-pkgs-cookiecutter` [template](https://github.com/py-pkgs/py-pkgs-cookiecutter).

Development setup follows the [`py-pkgs`](https://py-pkgs.org/03-how-to-package-a-python.html) guide using Poetry for dependency management.

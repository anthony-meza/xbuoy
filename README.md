# xbuoy

A Python package for accessing and analyzing NOAA NDBC buoy data. Built on top of [ndbc-api](https://github.com/CDJellen/ndbc-api), `xbuoy` provides a simple interface to fetch, process, and visualize oceanographic buoy observations as xarray datasets.

<img width="585" alt="Screenshot 2024-10-16 at 5 13 39 PM" src="https://github.com/user-attachments/assets/9a64a9b2-21a4-48b6-8452-36e5807dcc2f">

## Installation

### Using a Python virtual environment (recommended)

```bash
# Create and activate a virtual environment
$ python -m venv xbuoy-env
$ source xbuoy-env/bin/activate  # On macOS/Linux
$ xbuoy-env\Scripts\activate     # On Windows

# Install xbuoy
$ pip install git+https://github.com/anthony-meza/xbuoy.git@main
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

## Documentation

- **Quick Start:** See [getting_started.ipynb](examples/getting_started.ipynb)
- **API Reference:** Main functions are `list_stations()`, `fetch_data()`, `filter_by_region()`, `plot_stations()`
- **Examples:** Check the `examples/` directory for Jupyter notebooks

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


## Contributing

Interested in contributing? Check out the contributing guidelines. Please note that this project is released with a Code of Conduct. By contributing to this project, you agree to abide by its terms.

## License

`xbuoy` was created by Anthony Meza. It is licensed under the terms of the MIT license.

## Credits

`xbuoy` was created with [`cookiecutter`](https://cookiecutter.readthedocs.io/en/latest/) and the `py-pkgs-cookiecutter` [template](https://github.com/py-pkgs/py-pkgs-cookiecutter).

Development setup follows the [`py-pkgs`](https://py-pkgs.org/03-how-to-package-a-python.html) guide using Poetry for dependency management.

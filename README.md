# xndbc

[![Documentation](https://readthedocs.org/projects/xndbc/badge/?version=latest)](https://xndbc.readthedocs.io/en/latest/)

**NOAA buoy observations, in xarray.** Find National Data Buoy Center
stations and load historical or recent measurements into ordinary
`xarray.Dataset` objects. Explore weather, waves, and ocean currents with the
same selection, plotting, and export tools you use for other climate data.

[Documentation](https://xndbc.readthedocs.io/en/latest/) ·
[Example notebooks](https://xndbc.readthedocs.io/en/latest/docs/examples.html) ·
[API reference](https://xndbc.readthedocs.io/en/latest/docs/api.html)

## Install

Python 3.12 or newer is required; 3.12–3.14 is tested. Install from GitHub:

```bash
pip install "xndbc @ git+https://github.com/anthony-meza/xndbc.git@main"
```

Plotting and maps are included. Every installation also includes `xarray[complete]`
for file I/O, parallel computing, visualization, and accelerated operations.

## Your first buoy dataset

Download a year of observations from the Boston buoy and plot daily water
temperature:

```python
import xndbc

data = xndbc.fetch_historical("44013", years=2020)
print(data)
print(data.ndbc.report())  # Per-file download outcomes

temperature = data.WTMP.sel(station_id="44013")
daily = temperature.resample(time="D").mean(keep_attrs=True)
daily.plot.line(x="time")
```

Downloads preserve original timestamps in UTC. Units and descriptions live in
variable attributes. You choose how to average measurements; directions require
circular or vector averaging.

## Find your next dataset

```python
stations = xndbc.stations.search(query="Boston")
files = xndbc.stations.availability(station_ids="44013", years=[2020, 2021])
recent = xndbc.fetch_realtime("44013")
products = xndbc.list_modes()
```

Station discovery and availability also return xarray datasets. Archive file
availability does not guarantee complete measurements. Partial downloads warn
and return a report; entirely unsuccessful requests raise `xndbc.RetrievalError`.
Use `errors="raise"` when every requested file must succeed.

## Learn by example

Start with [getting started](examples/getting_started.ipynb), then try
[wind speed and direction](examples/wind_speed_direction.ipynb) or
[finding stations](examples/finding_stations.ipynb).
The [full notebook collection](https://xndbc.readthedocs.io/en/latest/docs/examples.html)
also covers historical comparisons, realtime observations, current profiles, and
wave spectra. Each notebook runs independently.

Version 0.2 is in development and replaces the 0.1 API. Existing users should
read the [migration guide](https://xndbc.readthedocs.io/en/latest/docs/migration.html).

## Contribute

From a local checkout:

```bash
conda env create -f docs/environment.yml
conda activate xndbc-dev
pytest -q
sphinx-build -W --keep-going -b html . docs/_build/html
```

CI checks the code, executes notebooks against offline fixtures, and builds the
website. API pages come from docstrings; product and variable tables come from
code; new notebooks appear automatically in the website's download gallery.
See [development notes](docs/notes.rst) for the documentation workflow and live checks.

Issues and pull requests with reproducible examples are welcome. Keep discussions
respectful and constructive. Created by Anthony Meza; [MIT licensed](LICENSE).

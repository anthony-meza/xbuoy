# xndbc

[![Documentation](https://readthedocs.org/projects/xndbc/badge/?version=latest)](https://xndbc.readthedocs.io/en/latest/)

**NOAA buoy observations, in xarray.** Choose stations, download historical or
realtime observations, and analyze weather, waves, and currents with ordinary
`xarray.Dataset` objects.

[Documentation](https://xndbc.readthedocs.io/en/latest/) ·
[Notebook downloads](https://xndbc.readthedocs.io/en/latest/docs/examples.html) ·
[API reference](https://xndbc.readthedocs.io/en/latest/docs/api.html)

## Install

Python 3.12 or newer is required; 3.12–3.14 is tested.

```bash
pip install "xndbc @ git+https://github.com/anthony-meza/xndbc.git@main"
```

Plotting, maps, and `xarray[complete]` are included.

## Choose stations and download observations

Select a region near Massachusetts, download a year of observations, and plot
daily water temperature:

```python
import xndbc

region = {"north": 43, "south": 42, "west": -71, "east": -70}
stations = xndbc.stations(bounds=region)
data = xndbc.historical(stations, years=2020)

daily = data.WTMP.resample(time="D").mean(keep_attrs=True)
daily.plot.line(x="time", hue="station_id")
```

`stations()` returns IDs, locations, and metadata. `historical()` and `realtime()`
return observations. All three return xarray datasets you can inspect and select.
Downloads preserve original UTC timestamps and missing measurements; you choose
how to average. Units and descriptions live in variable attributes.

## Already know the station—or want realtime observations?

```python
data = xndbc.historical("44013", years=2020)
recent = xndbc.realtime(stations)
```

Both download functions accept a station dataset, an ID string, or a list of IDs.
They also accept `bounds=region` directly. NOAA determines the realtime window.

## Continue exploring

Start with [getting started](examples/getting_started.ipynb), then try
[finding stations](examples/finding_stations.ipynb) or
[wind speed and direction](examples/wind_speed_direction.ipynb).
The website guide explains archive availability, download reports, measurement
coverage, product selection, and export. The
[notebook collection](https://xndbc.readthedocs.io/en/latest/docs/examples.html)
also covers historical comparisons, realtime observations, current profiles,
and wave spectra. Each notebook runs independently.

## Contribute

From a local checkout:

```bash
conda env create -f docs/environment.yml
conda activate xndbc-dev
pytest -q
sphinx-build -W --keep-going -b html . docs/_build/html
```

CI checks the code, executes notebooks against offline fixtures, and builds the
website. API pages come from code docstrings; product and variable tables
come from code; notebooks appear automatically in the download gallery.
See [development notes](docs/notes.rst) for the documentation workflow.

Issues and pull requests with reproducible examples are welcome. Keep discussions
respectful and constructive. Created by Anthony Meza; [MIT licensed](LICENSE).

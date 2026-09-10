Understanding datasets and plots
========================================

Dimensions and coordinates
----------------------------------

* Station catalogs use ``station_id`` and retain names, owners, types, and notes.
* Availability uses ``station_id`` and ``year`` with ``available`` and ``url``
  variables. Absent requested files have ``False`` and an empty URL.
* Observations use ``station_id`` and ``time``. Different station time axes align
  to their union; alignment gaps are missing, not interpolated.
* ADCP observations add ``depth_bin``. Actual measurement depths are stored in
  ``DEP`` and may vary over time. ``depth_bin`` itself is not depth in metres.
* Wave spectra add ``frequency``, in Hz. Realtime spectral density also includes
  ``SEP_FREQ`` when supplied by NOAA.

Times represent UTC. Station coordinates come from the current catalog and need
not match a historical deployment. Archive-only stations can have missing
coordinates; geographic filtering excludes unknown locations.

Measurement names follow NDBC, for example ``WTMP`` and ``WSPD``. Known variables
carry units and descriptive names; unknown columns retain header units when
available. Numeric missing codes are applied only to verified variable mappings,
never to every number in a file. NOAA ``MM`` and ``N/A`` markers become missing.
Definitions are based on
`NOAA measurement descriptions <https://www.ndbc.noaa.gov/faq/measdes.shtml>`_.

Choose a plot for the question
--------------------------------------

A station map shows positions; it works with one or many stations. Colored maps
require one value per station. Select a time or reduce explicitly:

.. code-block:: python

   snapshot = data.sel(time="2020-01-01T00:00:00")
   xndbc.stations.plot_map(snapshot, variable="WTMP")
   mean_temperature = data[["WTMP"]].mean("time", keep_attrs=True)
   xndbc.stations.plot_map(mean_temperature, variable="WTMP")

The map displays points without spatial interpolation. Stations with missing
values are gray; missing locations are omitted with a warning. Scalar station
selections also work. Labels are automatic for ten or fewer stations.

Use native xarray plots for temporal comparisons and multidimensional data:

.. code-block:: python

   data.WTMP.sel(station_id="44013").plot.line(x="time")
   data.WTMP.plot.line(x="time", hue="station_id")
   heatmap = data.WTMP.assign_coords(
       station_number=("station_id", list(range(data.sizes["station_id"])))
   )
   artist = heatmap.plot.pcolormesh(x="time", y="station_number")
   artist.axes.set_yticks(heatmap.station_number.values, labels=heatmap.station_id.values)
   adcp.SPD.isel(station_id=0).plot.pcolormesh(x="time", y="depth_bin")
   spectral.SWDEN.isel(station_id=0).plot.pcolormesh(x="time", y="frequency")

Use small overlays for a few stations and heatmaps or explicit facets for larger
selections. Select depth or frequency before making a simple time series.

Sampling and coverage
-----------------------------

Fetching preserves original timestamps. Explicitly average scalar variables:

.. code-block:: python

   monthly = data[["WTMP", "WSPD"]].resample(time="ME").mean(keep_attrs=True)

Directions require circular or vector averaging. See :doc:`wind` for wind
conventions, missing and calm observations, and the difference between mean
speed and the magnitude of a mean vector.

Coverage requires a frequency and counts bins with at least one nonmissing
observation. Bins with no observations count against the denominator. Explicit
start/end boundaries include bins outside the downloaded observation range:

.. code-block:: python

   coverage = data[["WTMP"]].ndbc.coverage(
       "D", start="2020-01-01", end="2020-12-31T23:59:59",
   )

The window is inclusive; a date-only end means midnight at the start of that day.
Coverage is not native sample completeness: one valid sample can fill a daily
bin. Calculate coverage before averaging to retain this interpretation.

Failures, caching, and export
-------------------------------------

Partial downloads return successful stations and emit one summarized warning.
Inspect ``data.ndbc.report()`` for unavailable or failed requests. Failed stations
are not represented as fabricated observation rows. An all-failed request or any
failure under ``errors="raise"`` raises ``xndbc.RetrievalError``; its ``report``
attribute is an xarray dataset. Metadata outages preserve successful observations
with missing coordinates and a warning.

The report describes the original request even after selecting observations.
File presence and successful parsing do not guarantee a particular measurement.
Data variables may be entirely missing for some stations.

Catalogs and indexes are cached in memory. Use discovery's ``refresh=True`` to
refresh them after upstream updates. Observation files are downloaded on every
fetch. ``progress=False`` suppresses progress, not warnings.

.. code-block:: python

   data.to_netcdf("observations.nc", engine="scipy")
   import xarray as xr
   with xr.open_dataset("observations.nc") as restored:
       report = restored.ndbc.report()

NetCDF engines, including SciPy, are installed with xndbc. Provenance is serialized
as a JSON attribute so exports do not depend on custom Python objects.

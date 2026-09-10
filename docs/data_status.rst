Archive availability and measurement coverage
=============================================

Finding a station, finding a file, and finding valid measurements are separate
steps. Use the result that answers your question:

.. list-table:: What each operation tells you
   :header-rows: 1

   * - Operation
     - Question
     - Result and network access
   * - ``xndbc.stations()``
     - Which stations match my selection?
     - Station metadata; reads NOAA's catalog, with in-memory caching.
   * - ``stations.ndbc.availability()``
     - Does NOAA list an archive file for this station, year, and product?
     - Boolean flags and URLs; reads cached or downloaded archive indexes.
   * - ``xndbc.historical()`` / ``xndbc.realtime()``
     - What observations can I retrieve?
     - Measurement datasets; downloads observation files on each call.
   * - ``data.ndbc.report()``
     - What happened to the requested files?
     - Original per-file outcomes; no network access.
   * - ``data.ndbc.coverage()``
     - How much of this time window has valid measurements?
     - Occupied-bin percentages for each variable; no NOAA requests.

Archive availability: before downloading
----------------------------------------

.. code-block:: python

   import xndbc

   stations = xndbc.stations("44013")
   files = stations.ndbc.availability(years=[2020, 2021])

``files`` has ``station_id`` and ``year`` dimensions. ``available=True`` means
NOAA lists the file; ``url`` identifies it. An absent file has ``False`` and an
empty URL. Choose a product with ``mode=``: a station may have a meteorological
archive but no current-profile archive. Omitted years include all indexed years.
This operation does not inspect the measurements inside those files.

To retain stations with at least one requested archive file:

.. code-block:: python

   selected = stations.sel(station_id=files.station_id.where(
       files.available.any("year"), drop=True
   ))
   if selected.sizes["station_id"]:
       data = xndbc.historical(selected, years=[2020, 2021])

Download reports: after retrieval
---------------------------------

``data.ndbc.report()`` describes each requested file: station, year, URL, status,
and error. A listed file can fail to download or parse. A successful file can
still contain missing measurements. Reports refer to the original request, even
after selecting a subset of the resulting observations.

Measurement coverage: after downloading
---------------------------------------

Coverage is calculated separately for each variable. A day with one valid wind
speed has wind-speed coverage even if every wind-direction measurement is missing.
The same file can therefore have different coverage for different variables.

Consider a hypothetical archive that exists and downloads successfully, containing
these observations. This small example needs no NOAA access:

.. code-block:: python

   import numpy as np
   import xarray as xr
   import xndbc

   example = xr.Dataset(
       {"WSPD": ("time", [5.0, np.nan, 7.0]),
        "WDIR": ("time", [350.0, np.nan, np.nan])},
       coords={"time": np.array(
           ["2020-01-01", "2020-01-02", "2020-01-03"], dtype="datetime64[ns]"
       )},
   )
   coverage = example.ndbc.coverage("D", start="2020-01-01", end="2020-01-03")

Wind speed has two occupied days out of three: **66.7% coverage**. Wind direction
has one: **33.3% coverage**. The archive's availability and successful retrieval
do not change those percentages. A zero wind speed is a valid measurement; NaN
means missing. A day without any timestamp also counts as empty.

Coverage is the percentage of occupied bins, not the percentage of expected
native samples. One observation fills a daily bin. Choose ``"h"`` for hourly
bins, and inspect sample counts when assessing whether averages represent the
whole period. Calculate coverage before averaging observations.

Specify the window you intend to assess. Without explicit boundaries, coverage
uses the earliest and latest observation timestamps, which may exclude missing
periods at either end. Boundaries are inclusive; a date-only end is midnight at
the beginning of that day. For a full year use ``end="2020-12-31T23:59:59"``.
Additional station, depth, and frequency dimensions remain in the result.

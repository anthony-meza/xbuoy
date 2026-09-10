First observations
==================

Choose stations
---------------

Select a region by its latitude and longitude bounds. The result contains
station IDs, locations, and descriptive metadata:

.. code-block:: python

   import xndbc

   region = {"north": 43, "south": 42, "west": -71, "east": -70}
   stations = xndbc.stations(bounds=region)
   stations

Download observations
---------------------

Pass the station dataset directly to a download function:

.. code-block:: python

   data = xndbc.historical(stations, years=2020)
   data

The result has ``station_id`` and ``time`` dimensions, original UTC timestamps,
and measurement attributes containing units and descriptions. Failed individual
files produce a warning when other downloads succeed. Inspect their outcomes
with ``data.ndbc.report()``; see :doc:`downloads` for failure handling.

Analyze with xarray
-------------------

.. code-block:: python

   daily = data.WTMP.resample(time="D").mean(keep_attrs=True)
   daily.plot.line(x="time", hue="station_id")

The download retains original observations. Resampling explicitly creates daily
water-temperature averages. Directional variables require circular or vector
averaging, explained in :doc:`wind`.

Known stations and realtime observations
----------------------------------------

Discovery is optional when you already know the IDs:

.. code-block:: python

   data = xndbc.historical("44013", years=2020)
   recent = xndbc.realtime(stations)
   two_stations = xndbc.realtime(["44013", "41043"])

A single station still retains its station dimension. NOAA determines the
realtime window. Continue with :doc:`discovery` for station selections and maps,
then :doc:`downloads` for products and retrieval outcomes.

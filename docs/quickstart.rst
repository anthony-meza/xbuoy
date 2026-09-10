First observations
==========================

Download one station
----------------------------

.. code-block:: python

   import xndbc

   data = xndbc.fetch_historical("44013", years=2020)
   data                       # Ordinary xarray.Dataset
   data.ndbc.report()         # Download status, including failures

A successful single-station request still has a ``station_id`` dimension. Data
remain at their original observation times. Variable attributes provide units
and descriptions; times are UTC.

Select, average, and plot explicitly
--------------------------------------------

.. code-block:: python

   temperature = data.WTMP.sel(station_id="44013")
   daily = temperature.resample(time="D").mean(keep_attrs=True)
   daily.plot.line(x="time")

Use native xarray plotting for time series. Use a map for spatial questions:

.. code-block:: python

   xndbc.stations.plot_map(data)

Continue through the user guide
-------------------------------

Use :doc:`discovery` to build a station selection and :doc:`downloads` to choose
products and handle download outcomes. :doc:`datasets` explains dimensions,
missing data, coverage, and export. For directional measurements, continue to
:doc:`wind` before averaging.

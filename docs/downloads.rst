Retrieving observations
=======================

Once you have station IDs, choose a product and time source. Historical requests
select archive years; realtime requests use the window currently published by
NOAA. Both return observations at their original timestamps.

Historical and realtime data
----------------------------

.. code-block:: python

   import xndbc

   historical = xndbc.fetch_historical("44013", years=[2020, 2021])
   recent = xndbc.fetch_realtime("44013")

IDs can be strings, iterables, or scalar or one-dimensional xarray DataArrays.
Even a single station retains its ``station_id`` dimension. Different station
time axes align to their union, with missing values where observations do not
coincide. The downloader does not interpolate or average them.

Choose a product
----------------

The default ``stdmet`` product contains standard meteorological observations.
Use ``xndbc.list_modes()`` or :doc:`reference` to inspect other products and their
historical/realtime support. For example:

.. code-block:: python

   profiles = xndbc.fetch_historical("41051", years=2013, mode="adcp")
   spectra = xndbc.fetch_historical("41018", years=1996, mode="swden")

Products have different dimensions: profiles add ``depth_bin`` and spectra add
``frequency``. See :doc:`datasets` before selecting or reducing those dimensions.
Product support does not imply that every station provides that product.

Inspect outcomes
----------------

.. code-block:: python

   report = historical.ndbc.report()

A partial download returns successful observations and emits one warning. An
entirely unsuccessful request raises ``xndbc.RetrievalError``. For workflows that
require every requested file, pass ``errors="raise"``. The exception's ``report``
attribute describes unsuccessful requests as an xarray dataset.

Reports describe the original request, including after selecting observations.
A successful file download does not guarantee complete measurements. Continue
with :doc:`datasets` to interpret missing values, measure coverage, and export.

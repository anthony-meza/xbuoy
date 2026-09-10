Selecting stations
==================

``xndbc.stations()`` returns the station catalog as an xarray dataset. Each row
is a station, identified by ``station_id``, with location and descriptive metadata.
It tells you where stations are; it does not promise observations for a given year
or measurement. Archive availability and measurement coverage are explained in
:doc:`data_status`.

Choose a region
---------------

.. code-block:: python

   import xndbc

   region = {"north": 43, "south": 42, "west": -71, "east": -70}
   stations = xndbc.stations(bounds=region)
   stations.ndbc.plot_map()

Bounds require exactly ``north``, ``south``, ``west``, and ``east`` in finite
degrees. Latitudes range from -90 to 90; longitudes range from -180 to 180.
South cannot exceed north. West greater than east crosses the antimeridian.
Unknown locations cannot match geographic bounds. Positions describe the current
catalog and may differ from historical deployments.

Select IDs or use xarray
------------------------

.. code-block:: python

   stations = xndbc.stations(["44013", "41043"])
   one_station = stations.sel(station_id="44013")
   data = xndbc.historical(one_station, years=2020)

Known IDs absent from the current catalog are omitted by ``stations()``. For a
historical station absent from that catalog, pass its ID directly to
``historical()``. Calling ``stations()`` without filters returns the full catalog.
When IDs and bounds are both supplied to discovery, both filters apply.

Download a selection
--------------------

.. code-block:: python

   stations = xndbc.stations(bounds=region)
   if stations.sizes["station_id"]:
       data = xndbc.historical(stations, years=2020)

Downloads accept station datasets, ID strings, ID iterables, and scalar or
one-dimensional ID DataArrays. Dataset selections supply their ``station_id``
coordinate, including after a scalar ``sel``. Empty selections raise an error.

For a direct regional request, use
``xndbc.historical(bounds=region, years=2020)`` or
``xndbc.realtime(bounds=region)``. These resolve the same station IDs as the
explicit discovery step. Downloads require either a selection or bounds, not both.
See :doc:`downloads` for selecting products and interpreting file outcomes.

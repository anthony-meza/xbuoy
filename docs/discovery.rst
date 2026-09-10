Selecting stations
==================

Station discovery answers two questions: where a station is, and which archived
files it has. The catalog describes current station metadata; the archive index
describes historical file availability. Both are xarray datasets indexed by
``station_id``.

Search the catalog
------------------

Search by name, ID, owner, or station type with a literal, case-insensitive query:

.. code-block:: python

   import xndbc

   catalog = xndbc.stations.search(query="Boston")
   xndbc.stations.plot_map(catalog)

Use ``station_ids="44013"`` to look up a known station. Catalog coordinates
describe current locations and may differ from historical deployments.

Choose a region and year
------------------------

Filter archive availability by geographic bounds and year, then keep IDs whose
files exist:

.. code-block:: python

   region = {"north": 25, "south": 10, "west": -85, "east": -60}
   available = xndbc.stations.availability(bounds=region, years=2020)
   selected = available.sel(year=2020)
   ids = selected.station_id.where(selected.available, drop=True)

Bounds require exactly ``north``, ``south``, ``west``, and ``east``. Values are
finite degrees, with latitudes from -90 to 90 and longitudes from -180 to 180.
South must not exceed north; west greater than east crosses the antimeridian.
Stations with unknown coordinates cannot pass geographic filtering.

Availability indicates file presence. A file can still contain missing values or
lack a particular measurement. Use :doc:`datasets` to assess coverage after
retrieval. Discovery may return no matches, so check the selection before fetching:

.. code-block:: python

   if ids.size:
       data = xndbc.fetch_historical(ids, years=2020)

Next, :doc:`downloads` explains product selection and download outcomes.

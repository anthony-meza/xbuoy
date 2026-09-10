Migrating from 0.1 to 0.2
=================================

Version 0.2 replaces the overloaded ``list_available`` and ``fetch_data`` entry
points. The old names are removed. Results remain xarray datasets.

.. list-table:: Public API changes
   :header-rows: 1
   :widths: 45 55

   * - Version 0.1
     - Version 0.2
   * - ``list_available(mode=None)``
     - ``stations.search()``
   * - ``list_available(mode="stdmet")``
     - ``stations.availability(mode="stdmet")``
   * - ``lon_min``, ``lat_min``, ``lon_max``, ``lat_max``
     - ``bounds={"north": north, "south": south, "west": west, "east": east}``
   * - ``fetch_data(ids, years=2020)``
     - ``fetch_historical(ids, years=2020)``
   * - ``fetch_data(ids, data_type="realtime")``
     - ``fetch_realtime(ids)``
   * - ``sample_rate="D"``
     - Explicit ``data[["WTMP"]].resample(time="D").mean(keep_attrs=True)``
   * - ``helpers.compute_data_coverage(data)``
     - ``data.ndbc.coverage("D", start=..., end=...)``
   * - ``helpers.plot_stations(data)``
     - ``xndbc.stations.plot_map(data)``

Availability now uses station/year dimensions instead of a flat file listing.
Select available IDs without converting to pandas:

.. code-block:: python

   available = xndbc.stations.availability(years=2020)
   selected = available.sel(year=2020)
   ids = selected.station_id.where(selected.available, drop=True)

Important behavior changes
----------------------------------

* Geographic bounds require a dictionary with ``north``, ``south``, ``west``, and
  ``east`` keys. Replace positional bounds tuples with named coordinates.
* Python 3.12 or newer is required; 3.12–3.14 is tested.
* Downloads preserve original timestamps and no longer average directions or
  scalar measurements implicitly. Prefer current xarray frequencies ``h`` and
  ``ME`` for hourly and month-end aggregation.
* Missing-value parsing no longer treats legitimate 99-degree directions as
  missing. These correctness fixes can change analysis results.
* Partial failures warn, all-failed requests raise, and outcomes are inspectable.
* Coverage measures occupied time bins over a stated window. It retains original
  variable names such as ``WTMP`` rather than adding a ``_coverage`` suffix.
* Catalog-independent historical discovery retains stations that the earlier
  metadata intersection excluded.

Update scripts to make averaging and coverage windows explicit, and compare
scientific results with these changes in mind.

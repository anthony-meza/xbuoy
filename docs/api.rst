API reference
=============

Signatures and descriptions below come directly from the public Python code.
Results are ordinary xarray datasets: use ``sel``, ``where``, ``resample``,
``plot``, and ``to_netcdf`` directly. See :doc:`reference` for supported products
and variable units.

Downloads and products
----------------------

.. automodule:: xndbc
   :members:
   :imported-members:
   :exclude-members: stations

Station discovery and maps
--------------------------

.. automodule:: xndbc.stations
   :members:

Dataset accessor
----------------

Importing ``xndbc`` registers ``dataset.ndbc``. These helpers operate on loaded
data and provenance.

.. autoclass:: xndbc.accessor.NDBCAccessor
   :members:

API reference
=============

For the complete workflow begin with
:doc:`quickstart`; see :doc:`data_status` for archive availability and measurement
coverage, and :doc:`reference` for products and variable units.

Stations and observations
-------------------------

.. automodule:: xndbc
   :members:
   :imported-members:

Dataset helpers
---------------

Importing ``xndbc`` registers ``dataset.ndbc``. Maps work with station or
observation datasets. Archive availability reads NOAA indexes; coverage and
reports operate on existing observations and provenance.

.. autoclass:: xndbc.accessor.NDBCAccessor
   :members:

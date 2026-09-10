API reference
=============

For the complete workflow begin with
:doc:`/examples/getting_started`; see :doc:`/examples/historical_analysis` for archive availability and measurement
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

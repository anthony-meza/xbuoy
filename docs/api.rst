API reference
=============

For the complete workflow begin with
:doc:`/examples/getting_started`; see :doc:`/examples/historical_analysis` for archive availability and measurement
coverage. Product and variable tables appear below.

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

.. _products-and-variables:

Products and variables
----------------------

These tables are generated from the same definitions used by the downloads and
parser on every documentation build. Product support does not guarantee files
or measurements at a particular station. Inspect ``xndbc.list_modes()`` and
``stations.ndbc.availability()`` when choosing a download.

Supported products
~~~~~~~~~~~~~~~~~~

.. ndbc-reference:: products

Variable metadata
~~~~~~~~~~~~~~~~~

Names follow NOAA headers. Units and descriptions are attached to data variable
attributes. Numeric missing codes below become missing values for their specific
variables; text markers such as ``MM`` and ``N/A`` are handled separately.
Unknown variables retain header units when available. A code of ``None`` means
no numeric sentinel is replaced for that variable.

.. ndbc-reference:: variables

See :doc:`/examples/historical_analysis` for dimensions, sampling, coverage, and missing data, and
`NOAA's measurement descriptions <https://www.ndbc.noaa.gov/faq/measdes.shtml>`_
for measurement conventions.

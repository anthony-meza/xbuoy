Products and variables
======================

These tables are generated from the same definitions used by the downloads and
parser on every documentation build. Product support does not guarantee files
or measurements at a particular station. Inspect ``xndbc.list_modes()`` and
``stations.ndbc.availability()`` when choosing a download.

Supported products
------------------

.. ndbc-reference:: products

Variable metadata
-----------------

Names follow NOAA headers. Units and descriptions are attached to data variable
attributes. Numeric missing codes below become missing values for their specific
variables; text markers such as ``MM`` and ``N/A`` are handled separately.
Unknown variables retain header units when available. A code of ``None`` means
no numeric sentinel is replaced for that variable.

.. ndbc-reference:: variables

See :doc:`datasets` for dimensions, sampling, coverage, and missing data, and
`NOAA's measurement descriptions <https://www.ndbc.noaa.gov/faq/measdes.shtml>`_
for measurement conventions.

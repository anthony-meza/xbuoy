xndbc: buoy observations in xarray
==================================

xndbc connects NOAA National Data Buoy Center observations to xarray. Find stations,
check their archives, and download weather, wave, or current measurements into
ordinary datasets. Observations retain their timestamps, units, and download
reports so you can choose how to analyze them.

The user guide follows a single workflow: select stations, retrieve observations,
and interpret the resulting dataset. Begin with :doc:`installation` and
:doc:`quickstart`. For a specific operation, use the API reference; for experiments
in Jupyter, download a notebook from :doc:`examples`.

.. toctree::
   :caption: User guide
   :maxdepth: 1

   installation
   quickstart
   discovery
   downloads
   data_status
   datasets
   wind

.. toctree::
   :caption: Reference and examples
   :maxdepth: 1

   api
   reference
   examples

.. toctree::
   :caption: Project
   :maxdepth: 1

   notes

:html_theme.sidebar_secondary.remove:

Buoy observations, in xarray
============================

Find NOAA National Data Buoy Center stations, download weather, waves, and
currents, and work with ordinary ``xarray.Dataset`` objects. xndbc preserves
observation timestamps, units, and download reports so you can choose how to
analyze your data.

.. grid:: 1 2 2 4
   :gutter: 3
   :class-container: homepage-links

   .. grid-item-card:: Quickstart
      :link: examples/getting_started
      :link-type: doc

      Choose stations and download your first observations.

   .. grid-item-card:: User guide
      :link: docs/user_guide
      :link-type: doc

      Follow the workflow from discovery to analysis.

   .. grid-item-card:: API reference
      :link: docs/api
      :link-type: doc

      Look up functions, arguments, and dataset helpers.

   .. grid-item-card:: Examples
      :link: docs/examples
      :link-type: doc

      Read worked examples with code, tables, and plots.

Install
-------

Use Python 3.12 or newer:

.. code-block:: bash

   pip install "xndbc @ git+https://github.com/anthony-meza/xndbc.git@main"

Plotting, maps, and ``xarray[complete]`` are included.
See :doc:`docs/installation` for environment setup.

From a station to a dataset
--------------------------------

Download historical observations for buoy 44013 and plot daily water temperature:

.. code-block:: python

   import xndbc

   data = xndbc.historical("44013", years=2020)
   daily = data.WTMP.resample(time="D").mean(keep_attrs=True)
   daily.plot.line(x="time", hue="station_id")

Downloads use NOAA services. For regional station selection, realtime data,
and interpreting download reports, continue with :doc:`/examples/getting_started`.

.. toctree::
   :hidden:
   :maxdepth: 2

   User guide <docs/user_guide>
   API reference <docs/api>
   Examples <docs/examples>
   Development <docs/notes>

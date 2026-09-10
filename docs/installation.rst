Installation
============

Python 3.12–3.14 is tested. Use Python 3.14 for a new development environment.

.. code-block:: bash

   pip install "xndbc @ git+https://github.com/anthony-meza/xndbc.git@main"

Every installation includes Matplotlib, Cartopy, and ``xarray[complete]``.
Xarray's complete extra supplies its I/O, parallel computing, visualization,
and acceleration dependencies, including NetCDF engines and Dask. See
`xarray's installation guide <https://docs.xarray.dev/en/stable/getting-started-guide/installing.html>`_.

Matplotlib is constrained below 3.11 because of a verified
`Cartopy map-rendering regression <https://github.com/SciTools/cartopy/issues/2682>`_.
Maps may download Cartopy coastline data on their first use.

Development and notebooks
-------------------------

From the repository root:

.. code-block:: bash

   conda env create -f docs/environment.yml
   conda activate xndbc-dev
   jupyter lab
   pytest -q

The environment includes plotting, notebook execution, SciPy, and Sphinx.
Run ``pytest -q -m integration`` to explicitly request tests against live NOAA.

Python 3.14 free threading
--------------------------

Standard Python 3.14 is the default. Its optional free-threaded build is tested
separately through the manually triggered CI workflow. This does not guarantee
all plotting or NetCDF dependencies support free threading. Check
``sys._is_gil_enabled()`` after importing dependencies when evaluating it.

The download pool also overlaps blocking network I/O on standard Python. The
package does not require free threading or claim an unmeasured speedup. See
`Python's free-threading documentation <https://docs.python.org/3/howto/free-threading-python.html>`_.

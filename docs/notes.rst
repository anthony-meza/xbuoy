Development notes
=================

From the repository root, with the development environment activated:

.. code-block:: bash

   pytest -q
   pytest -q -m integration
   sphinx-build -W --keep-going -b html . docs/_build/html
   test -s docs/_build/html/index.html

Offline tests cover scientific parsing, discovery, failures, coverage, maps,
NetCDF provenance, and notebook workflows. Live NOAA tests are explicit because
availability and network access vary independently of package changes.

The backend uses functions, small metadata dictionaries, in-memory caches, and
one bounded thread pool. Workers own their downloaded text and parsed data;
the caller assembles datasets and diagnostics. Plotting runs on the caller.

Please submit issues with a minimal reproducible example, package/Python
versions, and the download report when relevant. Keep discussions respectful,
constructive, and focused on the project.

Maintaining documentation
-------------------------

Edit each piece of information at its source:

* Public signatures and API descriptions belong in Python docstrings. Sphinx
  discovers public members and renders them in :doc:`api`, with source links.
* Products and variable metadata belong in ``src/xndbc/_products.py`` and
  ``src/xndbc/_variables.py``. :doc:`reference` renders those definitions directly.
* Tutorials belong in ``examples/*.ipynb``. Give each notebook a descriptive
  first Markdown heading and an introduction. The website lists notebook downloads
  automatically, and pytest executes every notebook against offline fixtures.
* The website homepage belongs in the repository-root ``index.rst``;
  ``docs/user_guide.rst`` organizes the guides. Keep existing page URLs stable.
* Conceptual explanations belong in ``docs/*.rst``. Keep the README focused on
  installation, a first successful download, and links to the website.

The same Sphinx configuration builds locally, in CI, and on Read the Docs.
Pull requests build the site with warnings treated as errors; the CI artifact
contains the HTML for review. CI also checks for a nonempty root ``index.html``,
which Read the Docs requires before publishing. Open ``docs/_build/html/index.html``
to preview the site locally. Read the Docs is configured to fail on warnings
as well. Automatic publication requires the repository's Read the Docs webhook
and build settings to be enabled in that service.

Website builds copy notebooks as downloadable files without executing them.
The user guide is written separately in reStructuredText, with its own progression
through discovery, downloads, and analysis.
Before saving newly executed outputs, identify their source and retrieval date
in the notebook; never present offline fixture outputs as real observations.
Offline execution checks notebook code without changing the committed notebooks.
For new products or station selections, extend ``tests/noaa_fixtures.py`` when
needed. Run live checks explicitly when verifying upstream availability.

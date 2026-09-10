Development notes
=================

From the repository root, with the development environment activated:

.. code-block:: bash

   pytest -q
   pytest -q -m integration
   sphinx-build -E -W --keep-going -b html . docs/_build/html
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
  first Markdown heading and an introduction. Add each tutorial to the table of
  contents in the root ``index.rst`` and link it from ``docs/examples.rst``.
  The website renders and executes notebooks;
  pytest also executes every notebook against offline fixtures.
* The website homepage belongs in the repository-root ``index.rst``;
  ``docs/user_guide.rst`` indexes the notebook pages, installation, and reference.
* Walkthrough explanations belong alongside executable cells in
  ``examples/*.ipynb``. Do not create separate RST versions of notebook topics.
  RST is reserved for navigation, installation, reference, and development notes.
  Keep the README focused on installation and links to the website.

The same Sphinx configuration builds locally, in CI, and on Read the Docs.
Pull requests build the site with warnings treated as errors; the CI artifact
contains the HTML for review. CI also checks for a nonempty root ``index.html``,
which Read the Docs requires before publishing. Open ``docs/_build/html/index.html``
to preview the site locally. Read the Docs is configured to fail on warnings
as well. Automatic publication requires the repository's Read the Docs webhook
and build settings to be enabled in that service.

Read the Docs automatically builds and publishes the documentation on pushes
when its GitHub integration is enabled. No local notebook execution or manual
build is needed. MyST-NB executes every tutorial against live NOAA services,
even when the source notebook already contains outputs, and saves the executed
notebooks under ``_executed/`` in the HTML build alongside rendered outputs.
It does not update notebooks in Git.
Execution uses temporary working directories, so tutorial exports do not modify
the source tree. Each cell has a 300-second timeout; execution errors fail the
build rather than publish incomplete results. NOAA outages can therefore require
rebuilding after the service recovers.

The website user guide links directly to the rendered tutorials. Record execution
or retrieval time in a code cell so timestamps update with each build. Never
present offline fixture outputs as real observations. Offline execution checks
notebook code without changing the committed notebooks. For new products or
station selections, extend ``tests/noaa_fixtures.py`` when needed.

The Read the Docs project must have its GitHub webhook enabled and the desired
branch active with automatic builds enabled. These are service settings, not
settings that ``.readthedocs.yaml`` can enable. GitHub Actions also builds tutorials
on pushes to main and pull requests, retaining the HTML as a review artifact.
For an optional local preview, use the clean build command above; ``-E`` ensures
all sources are processed again. Notebook pages also refresh automatically on
incremental builds.

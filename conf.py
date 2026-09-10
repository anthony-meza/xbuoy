import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

sys.path.insert(0, str(Path(__file__).resolve().parent / "docs" / "_ext"))

from xndbc import __version__

release = __version__
project = "xndbc"
author = "Anthony Meza"

extensions = ["sphinx.ext.autodoc", "sphinx.ext.napoleon",
              "sphinx.ext.viewcode", "reference_tables", "notebook_gallery"]
master_doc = "docs/index"
exclude_patterns = ["docs/_build", ".git", ".pytest_cache", "**/__pycache__", "**/.ipynb_checkpoints", "build"]
html_theme = "sphinx_rtd_theme"

autodoc_member_order = "bysource"

napoleon_google_docstring = True
napoleon_numpy_docstring = False

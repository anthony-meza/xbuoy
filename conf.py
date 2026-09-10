import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

sys.path.insert(0, str(Path(__file__).resolve().parent / "docs" / "_ext"))

from xndbc import __version__

release = __version__
project = "xndbc"
author = "Anthony Meza"

extensions = ["sphinx.ext.autodoc", "sphinx.ext.napoleon",
              "sphinx.ext.viewcode", "sphinx_design", "reference_tables", "myst_nb", "notebook_outputs"]
# Notebook pages are rendered directly alongside the reStructuredText guides.
source_suffix = {".rst": "restructuredtext", ".ipynb": "myst-nb"}
nb_execution_mode = "force"
nb_execution_in_temp = True
nb_execution_timeout = 300
nb_execution_allow_errors = False
nb_execution_raise_on_error = True
nb_kernel_rgx_aliases = {".*": "python3"}

root_doc = "index"
exclude_patterns = ["*.md", "**/*.md", "docs/_build", "_build", "_readthedocs", ".git", ".pytest_cache", "**/__pycache__", "**/.ipynb_checkpoints", "build"]
html_theme = "pydata_sphinx_theme"
html_title = "xndbc"
html_static_path = ["docs/_static"]
html_css_files = ["custom.css"]
html_theme_options = {
    "github_url": "https://github.com/anthony-meza/xndbc",
    "navbar_end": ["theme-switcher", "navbar-icon-links"],
    "navbar_persistent": ["search-button"],
    "show_nav_level": 2,
    "secondary_sidebar_items": ["page-toc"],
}
templates_path = ["docs/_templates"]
html_sidebars = {"**": ["site-nav.html"]}
html_copy_source = False
html_show_sourcelink = False

autodoc_member_order = "bysource"

napoleon_google_docstring = True
napoleon_numpy_docstring = False

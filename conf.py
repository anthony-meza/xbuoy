import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

sys.path.insert(0, str(Path(__file__).resolve().parent / "docs" / "_ext"))

from xndbc import __version__

release = __version__
project = "xndbc"
author = "Anthony Meza"

extensions = ["sphinx.ext.autodoc", "sphinx.ext.napoleon",
              "sphinx.ext.viewcode", "sphinx_design", "reference_tables", "notebook_gallery"]
root_doc = "index"
exclude_patterns = ["docs/_build", "_build", "_readthedocs", ".git", ".pytest_cache", "**/__pycache__", "**/.ipynb_checkpoints", "build"]
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
html_sidebars = {"index": [], "**": ["sidebar-nav-bs"]}

autodoc_member_order = "bysource"

napoleon_google_docstring = True
napoleon_numpy_docstring = False

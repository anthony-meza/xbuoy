"""Refresh rendered notebook pages on every documentation build."""

from pathlib import Path


def refresh_notebooks(app, env, added, changed, removed):
    # Force parsing even when an incremental build reuses its Sphinx environment.
    return [
        name for name in env.found_docs
        if Path(env.doc2path(name)).suffix == ".ipynb"
    ]


def setup(app):
    app.connect("env-get-outdated", refresh_notebooks)
    return {"version": "1", "parallel_read_safe": True, "parallel_write_safe": True}

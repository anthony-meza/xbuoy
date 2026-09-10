"""Refresh notebook pages and retain executed notebooks in published HTML builds."""

from pathlib import Path
import shutil


def refresh_notebooks(app, env, added, changed, removed):
    # Force parsing even when an incremental build reuses its Sphinx environment.
    return [
        name for name in env.found_docs
        if Path(env.doc2path(name)).suffix == ".ipynb"
    ]


def save_executed_notebooks(app, exception):
    if exception is not None or app.builder.format != "html":
        return
    source = Path(app.env.mystnb_config.output_folder)
    destination = Path(app.outdir) / "_executed"
    if destination.exists():
        shutil.rmtree(destination)
    for name in sorted(app.env.found_docs):
        if Path(app.env.doc2path(name)).suffix != ".ipynb":
            continue
        relative = Path(name + ".ipynb")
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / relative, target)


def setup(app):
    app.connect("env-get-outdated", refresh_notebooks)
    app.connect("build-finished", save_executed_notebooks)
    return {"version": "1", "parallel_read_safe": True, "parallel_write_safe": True}

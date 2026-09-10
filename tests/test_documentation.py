"""Check notebook publication and refresh behavior with a small real Sphinx build."""

import json
import os
from pathlib import Path
import subprocess
import sys

import nbformat
import pytest

pytest.importorskip("myst_nb")
pytest.importorskip("sphinx")

ROOT = Path(__file__).resolve().parents[1]


def build_project(tmp_path, code):
    source = tmp_path / "source"
    source.mkdir()
    (source / "conf.py").write_text(
        f"import sys\nsys.path.insert(0, {str(ROOT / 'docs' / '_ext')!r})\n"
        "extensions = ['myst_nb', 'notebook_outputs']\n"
        "nb_execution_mode = 'force'\n"
        "nb_execution_in_temp = True\n"
        "nb_execution_raise_on_error = True\n"
        "nb_execution_timeout = 30\n"
    )
    (source / "index.rst").write_text("Tutorials\n=========\n\n.. toctree::\n\n   example\n")
    notebook = nbformat.v4.new_notebook(
        cells=[nbformat.v4.new_markdown_cell("# Example"), nbformat.v4.new_code_cell(code)],
        metadata={"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"}},
    )
    notebook.cells[1].execution_count = 99
    notebook.cells[1].outputs = [nbformat.v4.new_output("stream", name="stdout", text="STALE OUTPUT")]
    nbformat.write(notebook, source / "example.ipynb")
    kernel = tmp_path / "jupyter" / "kernels" / "python3"
    kernel.mkdir(parents=True)
    (kernel / "kernel.json").write_text(json.dumps({
        "argv": [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"],
        "display_name": "Python 3", "language": "python",
    }))
    env = {**os.environ, "JUPYTER_PATH": str(tmp_path / "jupyter")}
    output = tmp_path / "build" / "html"

    def build():
        return subprocess.run(
            [sys.executable, "-m", "sphinx", "-T", "-W", "-b", "html", str(source), str(output)],
            capture_output=True, text=True, env=env, timeout=90,
        )

    return source, output, build


def test_notebooks_refresh_and_publish_without_changing_source(tmp_path):
    counter = tmp_path / "counter"
    source, output, build = build_project(tmp_path, f"""
from pathlib import Path
counter = Path({str(counter)!r})
count = int(counter.read_text()) + 1 if counter.exists() else 1
counter.write_text(str(count))
Path('tutorial-export.txt').write_text('temporary output')
print(f'Fresh execution {{count}}')
""")
    original = (source / "example.ipynb").read_bytes()
    for expected in (1, 2):
        result = build()
        assert result.returncode == 0, result.stdout + result.stderr
        assert not (output / "_executed").exists()
        html = (output / "example.html").read_text()
        assert f"Fresh execution {expected}" in html
        assert "STALE OUTPUT" not in html
        assert (source / "example.ipynb").read_bytes() == original
        assert not (source / "tutorial-export.txt").exists()


def test_execution_error_fails_build(tmp_path):
    _, output, build = build_project(tmp_path, "raise RuntimeError('execution failed deliberately')")
    result = build()
    assert result.returncode != 0
    assert "execution failed deliberately" in result.stdout + result.stderr
    assert not (output / "_executed").exists()


def test_site_examples_navigation_and_no_downloads(tmp_path):
    pytest.importorskip("pydata_sphinx_theme")
    pytest.importorskip("sphinx_design")
    from bs4 import BeautifulSoup

    output = tmp_path / "html"
    result = subprocess.run(
        [sys.executable, "-m", "sphinx", "-E", "-W", "-b", "html",
         "-D", "nb_execution_mode=off", str(ROOT), str(output)],
        capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    notebooks = [
        "getting_started", "finding_stations", "historical_analysis",
        "realtime_observations", "wind_speed_direction", "current_profiles",
        "wave_spectra",
    ]
    home = BeautifulSoup((output / "index.html").read_text(), "html.parser")
    header = home.select_one("#pst-header")
    assert header is not None
    for doc in ("user_guide", "api", "notes"):
        assert header.select_one(f'a[href="docs/{doc}.html"]')
    assert not header.select(
        'a[href="docs/examples.html"], a[href^="examples/"]'
    )
    sidebar = home.select_one(".bd-sidebar-primary")
    assert sidebar is not None
    assert sidebar.select_one('a[href="docs/examples.html"]')
    for name in notebooks:
        assert sidebar.select_one(f'a[href="examples/{name}.html"]')
        page = BeautifulSoup((output / "examples" / f"{name}.html").read_text(), "html.parser")
        assert page.select_one(".cell_input")
        assert page.select_one(".cell_output")
        assert page.select_one(".prev-next-area a")
    api = BeautifulSoup((output / "docs/api.html").read_text(), "html.parser")
    assert api.select_one("#supported-products table")
    assert api.select_one("#variable-metadata table")
    for retired in ("downloads", "data_status", "datasets", "wind", "reference"):
        assert not (output / "docs" / f"{retired}.html").exists()
    assert not (output / "_executed").exists()
    assert not any(path.is_file() for path in (output / "_sources").rglob("*"))
    assert not list(output.rglob("*.ipynb"))
    for html in output.rglob("*.html"):
        page = BeautifulSoup(html.read_text(), "html.parser")
        assert not page.select('a[download], a.reference.download, a[href*="_executed/"], a[href*="_sources/"]')

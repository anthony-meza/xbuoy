"""
Notebook execution tests.
"""

from pathlib import Path

import nbformat
import pytest
from nbclient import NotebookClient


pytestmark = pytest.mark.integration


@pytest.mark.parametrize("notebook_path", sorted(Path("examples").glob("*.ipynb")))
def test_example_notebook_runs(notebook_path):
    """Execute example notebooks end-to-end."""
    with notebook_path.open() as f:
        notebook = nbformat.read(f, as_version=4)

    client = NotebookClient(
        notebook,
        timeout=900,
        kernel_name="python3",
        resources={"metadata": {"path": str(notebook_path.parent)}},
    )
    client.execute()

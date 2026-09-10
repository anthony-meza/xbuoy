"""Execute the actual notebook code with small synthetic NOAA responses."""

import sys
from pathlib import Path

import nbformat
import pytest
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    "path", sorted((ROOT / "examples").glob("*.ipynb")), ids=lambda p: p.stem
)
def test_notebook(path, tmp_path):
    notebook = nbformat.read(path, as_version=4)
    fixture_code = (
        "import sys\n"
        f"sys.path[:0] = {[str(ROOT / 'src'), str(ROOT / 'tests')]!r}\n"
        "from noaa_fixtures import configure_notebook\n"
        "get_ipython().run_line_magic('matplotlib', 'inline')\n"
        "configure_notebook()\n"
    )
    notebook.cells.insert(0, nbformat.v4.new_code_cell(fixture_code))
    if path.stem == "wind_speed_direction":
        notebook.cells.append(nbformat.v4.new_code_cell("""
# The fixture crosses north (350 and 10 degrees) and includes a missing day.
north = float(summary.mean_direction.isel(time=0))
assert min(abs(north), abs(north - 360)) < 1e-10
assert float(summary.mean_speed.isel(time=0)) == 6.0
assert int(summary.direction_samples.isel(time=0)) == 2
assert np.isnan(summary.mean_direction.isel(time=1))
assert np.isnan(vector.speed.isel(time=2))
# Positive east-origin wind moves west; these samples have net southward motion.
np.testing.assert_allclose(float(vector.u.isel(time=0)), -0.17364817766693033)
np.testing.assert_allclose(float(vector.v.isel(time=0)), -5.908846518073248)
assert float(vector.speed.isel(time=0)) < float(vector.paired_scalar_speed.isel(time=0))
"""))
    client = NotebookClient(
        notebook,
        timeout=120,
        kernel_name="python3",
        resources={"metadata": {"path": str(tmp_path)}},
    )
    # Use the test interpreter, not an unrelated globally installed kernel.
    manager = client.create_kernel_manager()
    manager.kernel_spec.argv = [
        sys.executable,
        "-m",
        "ipykernel_launcher",
        "-f",
        "{connection_file}",
    ]
    client.km = manager
    client.execute()

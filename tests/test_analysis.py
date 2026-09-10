from pathlib import Path

import numpy as np
import pytest
import xarray as xr

import xndbc
from xndbc._parsing import parse_observation_table, table_to_dataset

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.mark.parametrize(
    "filename, mode, dimensions",
    [
        ("stdmet.txt", "stdmet", {"time": 3}),
        ("adcp.txt", "adcp", {"time": 2, "depth_bin": 2}),
        ("spectral.txt", "swden", {"time": 2, "frequency": 2}),
        ("realtime_spectral.txt", "swden", {"time": 2, "frequency": 3}),
    ],
)
def test_representative_formats(filename, mode, dimensions):
    ds = table_to_dataset(
        parse_observation_table((FIXTURES / filename).read_text(), mode), mode
    )
    assert dict(ds.sizes) == dimensions
    if filename == "stdmet.txt":
        assert ds.WDIR.values.tolist() == [350, 10, 99]
        assert ds.MWD.isel(time=0).item() == 99
        assert np.isnan(ds.WSPD.isel(time=-1))
    elif mode == "adcp":
        assert ds.DIR.isel(time=0, depth_bin=0).item() == 99
        assert ds.SPD.isel(time=0, depth_bin=0).item() == 99
        assert np.isnan(ds.SPD.isel(time=1, depth_bin=1))
        assert ds.SPD.attrs["units"] == "cm s-1"
        assert ds.DEP.isel(time=0).values.tolist() == [1.5, 2.5]
        assert np.isnan(ds.DEP.isel(time=1, depth_bin=1))
    else:
        assert np.isnan(ds.SWDEN.isel(time=0, frequency=0))
        assert ds.SWDEN.isel(time=0, frequency=1).item() == 99
        assert ds.frequency.attrs["units"] == "Hz"
        if filename == "spectral.txt":
            assert str(ds.time.values[0]).startswith("1996-01-01")
        else:
            assert ds.frequency.values.tolist() == [0.03, 0.04, 0.05]


def test_text_wave_summary_and_header_units():
    body = "#YY MM DD hh mm WVHT SwD STEEPNESS OTHER\n#yr mo dy hr mn m - - kg\n2020 01 01 00 00 1 SE VERY_STEEP 99\n"
    ds = table_to_dataset(parse_observation_table(body, "spec"), "spec")
    assert ds.SWD.item() == "SE"
    assert ds.STEEPNESS.item() == "VERY_STEEP"
    assert ds.OTHER.item() == 99
    assert ds.OTHER.attrs["units"] == "kg"


@pytest.mark.parametrize(
    "body, mode",
    [
        ("", "stdmet"),
        ("<html>Error</html>", "stdmet"),
        ("#YY MM DD hh mm WTMP\n2020 01 01 00 00\n", "stdmet"),
        ("#YY MM DD hh WTMP\n2020 01 01 00 12\n2020 01 01 01", "stdmet"),
        ("#YY MM DD hh mm\n2020 01 01 00 00 0.1 2 (0.03) junk", "swden"),
        ("#YY MM DD hh mm DEP01 DIR01 SPD01\n2020 01 01 00 00 1 2", "adcp"),
    ],
)
def test_malformed_files_raise(body, mode):
    with pytest.raises(ValueError):
        parse_observation_table(body, mode)


def test_adcp_reconstructed_headers_and_units():
    body = (
        "#YY MM DD hh mm DEP DIR SPD\n"
        "#yr mo dy hr mn m degree cm/s m degree cm/s\n"
        "2020 01 01 00 00 1 99 99 2 350 10\n"
    )
    frame = parse_observation_table(body, "adcp")
    assert list(frame.columns[-6:]) == [
        "DEP01",
        "DIR01",
        "SPD01",
        "DEP02",
        "DIR02",
        "SPD02",
    ]
    assert frame.attrs["units"]["SPD02"] == "cm/s"
    mismatched = body.replace("cm/s m degree cm/s", "cm/s")
    assert "units" not in parse_observation_table(mismatched, "adcp").attrs


@pytest.fixture(params=[False, True], ids=["standard", "flox"])
def coverage_engine(request):
    if request.param:
        import flox  # noqa: F401 -- require the acceleration installed by xarray[complete]
    with xr.set_options(use_flox=request.param):
        yield


def test_coverage_counts_empty_bins_and_preserves_dimensions(coverage_engine):
    ds = xr.Dataset(
        {"WTMP": (("station_id", "time"), [[1, 2], [np.nan, 2]])},
        coords={
            "station_id": ["a", "b"],
            "time": np.array(["2020-01-01", "2020-01-03"], dtype="datetime64[ns]"),
        },
    )
    coverage = ds.ndbc.coverage("D")
    np.testing.assert_allclose(coverage.WTMP, [200 / 3, 100 / 3])
    assert coverage.attrs["time_bins"] == 3
    assert coverage.WTMP.attrs["units"] == "%"
    wider = ds.ndbc.coverage("D", start="2020-01-01", end="2020-01-04")
    np.testing.assert_allclose(wider.WTMP, [50, 25])
    assert ds.ndbc.coverage("D", start="2019-01-01", end="2019-01-04").WTMP.max() == 0
    assert ds.expand_dims(frequency=[0.1, 0.2]).ndbc.coverage("D").WTMP.dims == (
        "frequency",
        "station_id",
    )


def test_coverage_partial_bins_duplicates_and_empty_time(coverage_engine):
    ds = xr.Dataset(
        {"WTMP": ("time", [1, 2, 3])},
        coords={
            "time": np.array(
                ["2020-01-01T12:00", "2020-01-01T12:00", "2020-02-10T12:00"],
                dtype="datetime64[ns]",
            )
        },
    )
    assert ds.ndbc.coverage("ME").WTMP.item() == 100
    empty = ds.isel(time=slice(0, 0))
    assert (
        empty.ndbc.coverage("D", start="2020-01-01", end="2020-01-03").WTMP.item() == 0
    )
    with pytest.raises(ValueError):
        empty.ndbc.coverage("D")
    with pytest.raises(ValueError):
        ds.ndbc.coverage("0h")
    with pytest.raises(ValueError):
        ds.ndbc.coverage("D", start="2021", end="2020")


def test_coverage_missing_samples_and_zero_values(coverage_engine):
    ds = xr.Dataset(
        {"WTMP": ("time", [np.nan, 0.0, np.nan])},
        coords={"time": np.array(
            ["2020-01-01T00:00", "2020-01-01T12:00", "2020-01-03T00:00"],
            dtype="datetime64[ns]",
        )},
    )
    # Zero is a real measurement; both absent days and all-missing days are empty.
    np.testing.assert_allclose(ds.ndbc.coverage("D").WTMP, 100 / 3)
    assert ds.where(ds.WTMP != 0).ndbc.coverage("D").WTMP.item() == 0


def test_map_layouts_without_coastline_download(monkeypatch):
    import matplotlib

    matplotlib.use("Agg")
    import cartopy.mpl.geoaxes
    import matplotlib.pyplot as plt

    monkeypatch.setattr(cartopy.mpl.geoaxes.GeoAxes, "coastlines", lambda *a, **k: None)
    monkeypatch.setattr(
        cartopy.mpl.geoaxes.GeoAxes, "add_feature", lambda *a, **k: None
    )
    ds = xr.Dataset(
        {"WTMP": ("station_id", [12.0, np.nan])},
        coords={
            "station_id": ["a", "b"],
            "latitude": ("station_id", [30.0, 31.0]),
            "longitude": ("station_id", [175.0, -175.0]),
        },
    )
    for subset in (ds, ds.sel(station_id="a"), ds.isel(station_id=slice(0, 0))):
        fig, ax = subset.ndbc.plot_map("WTMP")
        from io import BytesIO

        output = BytesIO()
        fig.savefig(output, format="png", bbox_inches="tight")
        output.seek(0)
        # Regression: incompatible Cartopy/Matplotlib rendered only the colorbar.
        assert plt.imread(output, format="png").shape[1] > 200
        plt.close(fig)
    fig, ax = ds.ndbc.plot_map()
    assert np.ptp(ax.get_xlim()) < 30
    plt.close(fig)
    with pytest.raises(ValueError, match="one value per station"):
        ds.expand_dims(time=[0]).ndbc.plot_map("WTMP")
    missing = ds.assign_coords(latitude=("station_id", [np.nan, np.nan]))
    with pytest.warns(UserWarning, match="Omitted 2"):
        fig, ax = missing.ndbc.plot_map()
    plt.close(fig)

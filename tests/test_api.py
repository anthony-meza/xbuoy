"""Offline public workflow and failure regression tests."""

import json

import numpy as np
import pytest
import xarray as xr

import xndbc
from xndbc import _catalog, _http, core
from xndbc import _stations as stations
from noaa_fixtures import read_fixture


@pytest.fixture
def offline(monkeypatch):
    _catalog._station_catalog.cache_clear()
    _catalog.historical_file_index.cache_clear()
    monkeypatch.setattr(_http, "read_noaa_text", read_fixture)
    yield
    _catalog._station_catalog.cache_clear()
    _catalog.historical_file_index.cache_clear()


def test_search_and_dateline(offline):
    assert set(
        xndbc.stations(
            bounds={"north": 40, "south": 20, "west": 170, "east": -170}
        ).station_id.values
    ) == {
        "46001",
        "46002",
    }
    assert xndbc.stations("absent").sizes["station_id"] == 0
    assert xndbc.stations("44013").notes.item() == "Boston harbor"


def test_archive_availability_for_known_unknown_and_missing_stations(offline):
    selected = xr.Dataset(coords={"station_id": ["44013", "archive", "absent"]})
    available = selected.ndbc.availability(years=[2020, 2022])
    assert available.available.dtype == bool
    assert available.available.values.tolist() == [[True, False], [True, False], [False, False]]
    assert (available.url.sel(year=2022) == "").all()
    assert available.latitude.sel(station_id="44013").item() == xndbc.stations("44013").latitude.item()
    assert np.isnan(available.latitude.sel(station_id=["archive", "absent"])).all()
    # Geographic filtering cannot locate archive-only stations without metadata.
    assert "archive" not in stations.availability(
        bounds={"north": 50, "south": 0, "west": -80, "east": -60}
    ).station_id


def test_discovery_cache_refresh_and_mutation(offline, monkeypatch):
    counter = []

    def read(url):
        if url.endswith("station_table.txt"):
            counter.append(url)
        return read_fixture(url)

    monkeypatch.setattr(_http, "read_noaa_text", read)
    first = xndbc.stations()
    first.latitude[:] = 0
    assert xndbc.stations("44013").latitude.item() != 0
    assert len(counter) == 1
    xndbc.stations(refresh=True)
    assert len(counter) == 2
    a = stations.availability()
    a.available[:] = False
    assert stations.availability().available.any()
    calls = []

    def updated_archive(url):
        if url.endswith("/"):
            calls.append(url)
            return '<a href="newh2020.txt.gz">new</a>'
        return read_fixture(url)

    monkeypatch.setattr(_http, "read_noaa_text", updated_archive)
    assert "new" not in stations.availability().station_id
    assert "new" in stations.availability(refresh=True).station_id
    assert len(calls) == 1


def test_partial_and_all_unavailable(offline):
    with pytest.warns(UserWarning, match="1 of 2"):
        data = xndbc.historical(["44013", "absent"], years=2020, progress=False)
    assert data.sizes["station_id"] == 1
    assert data.ndbc.report().status.values.tolist() == ["success", "unavailable"]
    with pytest.raises(xndbc.RetrievalError) as failure:
        xndbc.historical("absent", years=2020, progress=False)
    assert failure.value.report.status.item() == "unavailable"
    with pytest.raises(xndbc.RetrievalError):
        xndbc.historical(["44013", "absent"], years=2020, errors="raise", progress=False)


def test_download_failures_are_visible(offline, monkeypatch):
    def broken(url, mode):
        raise TimeoutError("NOAA timed out")

    monkeypatch.setattr(core, "_download", broken)
    with pytest.raises(xndbc.RetrievalError, match="timed out") as failure:
        xndbc.realtime("44013", progress=False)
    assert failure.value.report.status.item() == "failed"
    assert np.isnan(failure.value.report.year.item())
    assert "44013.txt" in failure.value.report.url.item()


def test_metadata_outage_preserves_observations(offline, monkeypatch):
    def broken(*args, **kwargs):
        raise TimeoutError("metadata offline")

    monkeypatch.setattr(core, "get_stations", broken)
    with pytest.warns(UserWarning, match="metadata offline"):
        data = xndbc.historical("44013", years=2020, progress=False)
    assert data.sizes["time"] == 3
    assert np.isnan(data.latitude.item())
    monkeypatch.setattr(stations, "get_stations", broken)
    with pytest.warns(UserWarning):
        assert stations.availability().available.any()
    with pytest.raises(RuntimeError, match="geographic"):
        stations.availability(
            bounds={"north": 50, "south": 0, "west": -80, "east": -60}
        )


@pytest.mark.parametrize(
    "kwargs, error",
    [
        ({"years": True}, TypeError),
        ({"max_workers": 0}, ValueError),
        ({"errors": "ignore"}, ValueError),
        ({"progress": "yes"}, TypeError),
        ({"mode": "spec"}, ValueError),
    ],
)
def test_validation_precedes_network(monkeypatch, kwargs, error):
    monkeypatch.setattr(
        core, "historical_file_index", lambda *a: pytest.fail("network attempted")
    )
    args = {"stations": "44013", "years": 2020, **kwargs}
    with pytest.raises(error):
        xndbc.historical(**args)


@pytest.mark.parametrize(
    "bounds",
    [
        {"north": 20, "south": 0, "west": 0},
        *[
            {"north": 20, "south": 0, "west": 0, "east": 1, **override}
            for override in [
                {"south": 30},
                {"north": 91},
                {"east": np.nan},
                {"east": True},
            ]
        ],
    ],
)
def test_invalid_bounds(bounds):
    with pytest.raises(ValueError, match="bounds|Longitudes"):
        stations._validate_bounds(bounds)


@pytest.mark.parametrize("discover", [xndbc.stations, stations.availability])
def test_bounds_validation_precedes_network(discover, monkeypatch):
    def no_network(*args, **kwargs):
        pytest.fail("network attempted before bounds validation")

    monkeypatch.setattr(stations, "get_stations", no_network)
    monkeypatch.setattr(stations, "historical_file_index", no_network)
    with pytest.raises(ValueError, match="bounds|Longitudes"):
        discover(bounds={})


def test_bounds_key_order_and_inclusive_edges(offline):
    station = xndbc.stations("44013")
    bounds = {
        "north": station.latitude.item(),
        "south": station.latitude.item(),
        "west": station.longitude.item(),
        "east": station.longitude.item(),
    }
    original = bounds.copy()
    result = xndbc.stations(bounds=bounds)
    assert result.station_id.values.tolist() == ["44013"]
    xr.testing.assert_identical(
        result, xndbc.stations(bounds=dict(reversed(bounds.items())))
    )
    assert bounds == original
    assert xndbc.stations(["44013", "41043"], bounds=bounds).station_id.item() == "44013"


def test_realtime_urls_and_netcdf_roundtrip(offline, tmp_path):
    data = xndbc.realtime(["bzbm3", "VAKF1"], progress=False)
    assert data.station_id.values.tolist() == ["bzbm3", "vakf1"]
    assert {url.rsplit("/", 1)[-1] for url in data.ndbc.report().url.values} == {
        "BZBM3.txt",
        "VAKF1.txt",
    }
    path = tmp_path / "data.nc"
    data.to_netcdf(path, engine="scipy")
    with xr.open_dataset(path, engine="scipy") as restored:
        xr.testing.assert_equal(data.ndbc.report(), restored.ndbc.report())
        assert restored.WTMP.attrs["units"] == "degC"
    assert json.loads(data.attrs["ndbc_report"])[0]["year"] is None


def test_modes_do_not_require_network():
    modes = xndbc.list_modes()
    assert not modes.historical.sel(mode="spec")
    assert not modes.realtime.sel(mode="adcp2")


def test_historical_download_preserves_order_metadata_and_original_values(
    offline, monkeypatch
):
    def read(url):
        if url.endswith("/"):
            return read_fixture(url) + '<a href="41043h2021.txt.gz">file</a>'
        if url.endswith(".gz"):
            # Different files overlap at the same timestamps and disagree on temperature.
            body = read_fixture(url).replace("2021", "2020")
            return body.replace("15 12 10", "15 42 10") if "2021" in url else body
        return read_fixture(url)

    monkeypatch.setattr(_http, "read_noaa_text", read)
    # A deterministic valid completion order; results must still follow request order.
    monkeypatch.setattr(core, "as_completed", lambda futures: reversed(list(futures)))
    ids = ["44013", "41043"]
    data = xndbc.historical(ids, years=[2020, 2021], progress=False)
    assert data.station_id.values.tolist() == ["44013", "41043"]
    assert data.sizes["time"] == 3
    assert data.WTMP.isel(time=0).values.tolist() == [12, 12]
    assert data.WDIR.sel(station_id="44013").values.tolist() == [350, 10, 99]
    assert data.WTMP.attrs["units"] == "degC"
    assert data.time.attrs["timezone"] == "UTC"
    assert data.name.sel(station_id="44013").item() == "Boston buoy"
    assert (data.ndbc.report().status == "success").all()
    assert data.ndbc.report().year.values.tolist() == [2020, 2021, 2020, 2021]


def test_archive_duplicates_and_empty_index(offline, monkeypatch):
    def index_text(url):
        if url.endswith("/"):
            return (
                '<a href="ABCh2020.txt.gz">first</a><a href="abch2020.txt.gz">last</a>'
            )
        return read_fixture(url)

    monkeypatch.setattr(_http, "read_noaa_text", index_text)
    archive = stations.availability()
    assert archive.station_id.item() == "abc"
    assert archive.url.item().endswith("/abch2020.txt.gz")
    monkeypatch.setattr(
        _http,
        "read_noaa_text",
        lambda url: "" if url.endswith("/") else read_fixture(url),
    )
    empty = stations.availability(refresh=True)
    assert dict(empty.sizes) == {"station_id": 0, "year": 0}
    assert empty.available.dtype == bool
    assert empty.station_id.dtype.kind == "U"
    assert empty.year.dtype.kind == "i"
    assert empty.url.dtype.kind == "U"


@pytest.mark.parametrize(
    "selection, expected",
    [
        (" BZBM3 ", ["bzbm3"]),
        (["44013", "41043", "44013"], ["44013", "41043"]),
        (xr.DataArray(["44013", "41043"]), ["44013", "41043"]),
        (xr.DataArray("44013"), ["44013"]),
        (xr.Dataset(coords={"station_id": ["44013", "41043"]}), ["44013", "41043"]),
        (xr.Dataset(coords={"station_id": "44013"}), ["44013"]),
    ],
    ids=["string", "list", "array", "scalar_array", "dataset", "scalar_dataset"],
)
def test_station_input_normalization(selection, expected):
    assert stations._normalize_station_ids(selection) == expected


@pytest.mark.parametrize("feed", ["historical", "realtime"])
def test_regional_download_matches_selection(offline, feed):
    bounds = {"north": 43, "south": 42, "west": -71, "east": -70}
    selected = xndbc.stations(bounds=bounds)
    kwargs = {"years": xr.DataArray(2020)} if feed == "historical" else {}
    direct = getattr(xndbc, feed)(bounds=bounds, progress=False, **kwargs)
    explicit = getattr(xndbc, feed)(selected, progress=False, **kwargs)
    xr.testing.assert_equal(direct, explicit)


@pytest.mark.parametrize(
    "selection, error",
    [
        (xr.Dataset({"station_id": ("row", ["44013"])}), ValueError),
        (xr.Dataset(coords={"station_id": ("row", [])}), ValueError),
        (xr.Dataset(coords={"station_id": (("row", "col"), [["44013"]])}), ValueError),
        (xr.Dataset(coords={"station_id": [44013]}), TypeError),
    ],
    ids=["missing_coordinate", "empty", "multidimensional", "nonstring"],
)
def test_invalid_station_input_normalization(selection, error):
    with pytest.raises(error):
        stations._normalize_station_ids(selection)


def test_station_selector_resolution(monkeypatch):
    bounds = {"north": 0, "south": -1, "west": 0, "east": 1}
    monkeypatch.setattr(
        core, "discover_stations", lambda **kwargs: pytest.fail("discovery attempted")
    )
    with pytest.raises(ValueError, match="either stations or bounds"):
        core._resolve_stations(None, None)
    with pytest.raises(ValueError, match="either stations or bounds"):
        core._resolve_stations("44013", bounds)
    monkeypatch.setattr(
        core, "discover_stations",
        lambda **kwargs: xr.Dataset(coords={"station_id": ("station_id", [])}),
    )
    with pytest.raises(ValueError, match="one or more"):
        core._resolve_stations(None, bounds)


def test_removed_query_and_old_exports():
    with pytest.raises(TypeError, match="query"):
        xndbc.stations(query="Boston")
    assert not hasattr(xndbc, "fetch_historical")
    assert not hasattr(xndbc, "fetch_realtime")

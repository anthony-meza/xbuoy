"""Small, explicitly requested checks against live NOAA services."""

import pytest

import xndbc

pytestmark = pytest.mark.integration


def test_live_discovery():
    stations = xndbc.stations(
        bounds={"north": 45, "south": 25, "west": -80, "east": -65}
    )
    assert stations.sizes["station_id"] > 0
    assert ((stations.latitude >= 25) & (stations.latitude <= 45)).all()
    available = xndbc.stations("44013").ndbc.availability(years=2020)
    assert available.available.item()


def test_live_historical_and_realtime():
    historical = xndbc.historical("44013", years=2020, progress=False)
    assert historical.sizes["time"] > 366
    assert historical.WTMP.attrs["units"] == "degC"
    realtime = xndbc.realtime("44013", progress=False)
    assert realtime.sizes["time"] > 0
    assert realtime.ndbc.report().status.item() == "success"


@pytest.mark.parametrize(
    "mode, station, year, dimension",
    [("adcp", "41051", 2013, "depth_bin"), ("swden", "41018", 1996, "frequency")],
)
def test_live_advanced_modes(mode, station, year, dimension):
    data = xndbc.historical(station, years=year, mode=mode, progress=False)
    assert data.sizes[dimension] > 1


def test_live_realtime_spectra():
    data = xndbc.realtime("44013", mode="swden", progress=False)
    assert data.sizes["frequency"] > 1

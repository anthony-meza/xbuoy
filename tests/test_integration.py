"""
Tests for xbuoy package.

Tests cover the main user-facing API as well as individual module functionality.
"""

import pytest
import xarray as xr
import pandas as pd
import numpy as np

import xbuoy
from xbuoy import core, station_metadata, data_processing, geographic_filters


class TestCoreAPI:
    """Test the high-level user-facing API."""

    def test_list_stations(self):
        """Test listing all buoy stations."""
        stations = xbuoy.list_stations()

        assert isinstance(stations, xr.Dataset)
        assert "latitude" in stations.data_vars
        assert "longitude" in stations.data_vars
        assert "min_year" in stations.data_vars
        assert "max_year" in stations.data_vars
        assert len(stations.station_id) > 0

    def test_list_stations_pandas(self):
        """Test listing stations as pandas DataFrame."""
        stations = xbuoy.list_stations(data_format="pandas")

        assert isinstance(stations, pd.DataFrame)
        assert "latitude" in stations.columns
        assert "longitude" in stations.columns

    def test_list_stations_with_region(self):
        """Test listing stations filtered by region."""
        # Test Caribbean region
        region = {
            'lon_min': -85,
            'lon_max': -60,
            'lat_min': 10,
            'lat_max': 25
        }
        stations = xbuoy.list_stations(region=region)

        assert isinstance(stations, xr.Dataset)
        # All stations should be within the specified region
        assert (stations.latitude >= 10).all()
        assert (stations.latitude <= 25).all()
        assert (stations.longitude >= -85).all()
        assert (stations.longitude <= -60).all()

    def test_filter_by_region(self):
        """Test filtering a dataset by geographic region."""
        stations = xbuoy.list_stations()

        # Filter to US East Coast
        filtered = xbuoy.filter_by_region(
            stations,
            lon_min=-80,
            lon_max=-65,
            lat_min=25,
            lat_max=45
        )

        assert isinstance(filtered, xr.Dataset)
        assert len(filtered.station_id) <= len(stations.station_id)
        # Check bounds
        assert (filtered.latitude >= 25).all()
        assert (filtered.latitude <= 45).all()


class TestStationMetadata:
    """Test station metadata functions."""

    def test_get_buoy_metadata(self):
        """Test fetching detailed buoy metadata."""
        metadata = station_metadata.get_buoy_metadata()

        assert isinstance(metadata, pd.DataFrame)
        assert len(metadata) > 0
        assert "min_year" in metadata.columns
        assert "max_year" in metadata.columns

    def test_get_buoy_stations(self):
        """Test getting simplified station information."""
        stations = station_metadata.get_buoy_stations(data_format="xarray")

        assert isinstance(stations, xr.Dataset)
        assert "latitude" in stations.data_vars
        assert "longitude" in stations.data_vars

    def test_get_historical_bounds(self):
        """Test getting historical bounds for a station."""
        bounds = station_metadata.get_historical_bounds("tplm2")

        assert isinstance(bounds, dict)
        assert "tplm2" in bounds
        # Bounds should be a tuple of (min_year, max_year) or (nan, nan)
        assert len(bounds["tplm2"]) == 2


class TestGeographicFilters:
    """Test geographic filtering functions."""

    def test_box_filter_global(self):
        """Test box filter with global bounds (no filtering)."""
        stations = xbuoy.list_stations()
        filtered = geographic_filters.box_filter_buoys(stations)

        # Should return all stations
        assert len(filtered.station_id) == len(stations.station_id)

    def test_box_filter_custom_region(self):
        """Test box filter with custom region."""
        stations = xbuoy.list_stations()

        # Filter to a small region
        filtered = geographic_filters.box_filter_buoys(
            stations,
            lon1=-75,
            lon2=-70,
            lat1=35,
            lat2=40
        )

        assert len(filtered.station_id) <= len(stations.station_id)
        # All stations should be within bounds
        assert (filtered.latitude >= 35).all()
        assert (filtered.latitude <= 40).all()


class TestDataProcessing:
    """Test data processing functions."""

    def test_add_variable_coverage(self):
        """Test computing data coverage for a variable."""
        # Create a simple test dataset
        ds = xr.Dataset({
            "WTMP": (["station_id", "time"], np.random.rand(3, 10)),
            "station_id": ["A", "B", "C"],
            "time": pd.date_range("2020-01-01", periods=10)
        })

        # Add some NaN values
        ds["WTMP"].values[0, 0:5] = np.nan  # 50% coverage for station A

        result = data_processing.add_variable_coverage(ds, varname="WTMP")

        assert "WTMP_coverage" in result.data_vars
        assert result["WTMP_coverage"].sel(station_id="A").values == 50.0
        assert result["WTMP_coverage"].sel(station_id="B").values == 100.0

    def test_compute_data_coverage(self):
        """Test the compute_data_coverage alias function."""
        # Create a simple test dataset
        ds = xr.Dataset({
            "WSPD": (["station_id", "time"], np.random.rand(2, 10)),
            "station_id": ["A", "B"],
            "time": pd.date_range("2020-01-01", periods=10)
        })

        result = data_processing.compute_data_coverage(ds, variable="WSPD")

        assert "WSPD_coverage" in result.data_vars
        assert (result["WSPD_coverage"] == 100.0).all()

    def test_add_latitude_longitude(self):
        """Test adding lat/lon coordinates from reference dataset."""
        # Create test datasets
        data = xr.Dataset({
            "WTMP": (["station_id", "time"], np.random.rand(2, 5)),
            "station_id": ["A", "B"],
            "time": pd.date_range("2020-01-01", periods=5)
        })

        reference = xr.Dataset({
            "latitude": (["station_id"], [40.0, 42.0]),
            "longitude": (["station_id"], [-70.0, -72.0]),
            "station_id": ["A", "B"]
        })

        result = data_processing.add_latitude_longitude(data, reference)

        assert "latitude" in result.data_vars
        assert "longitude" in result.data_vars
        assert result["latitude"].sel(station_id="A").values == 40.0
        assert result["longitude"].sel(station_id="B").values == -72.0


class TestPackageImports:
    """Test that main package imports work correctly."""

    def test_version_available(self):
        """Test that package version is accessible."""
        assert hasattr(xbuoy, "__version__")
        assert isinstance(xbuoy.__version__, str)

    def test_core_functions_available(self):
        """Test that core API functions are available at package level."""
        assert hasattr(xbuoy, "list_stations")
        assert hasattr(xbuoy, "fetch_data")
        assert hasattr(xbuoy, "filter_by_region")
        assert hasattr(xbuoy, "plot_stations")

    def test_advanced_functions_available(self):
        """Test that advanced functions are still available."""
        assert hasattr(xbuoy, "get_buoy_metadata")
        assert hasattr(xbuoy, "get_buoy_stations")
        assert hasattr(xbuoy, "box_filter_buoys")
        assert hasattr(xbuoy, "compute_data_coverage")

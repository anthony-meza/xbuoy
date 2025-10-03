"""
Basic tests for xbuoy package that don't require network access.
"""

import pytest
import xarray as xr
import pandas as pd
import numpy as np

import xbuoy
from xbuoy import data_processing, geographic_filters


class TestPackageStructure:
    """Test that the package is properly structured."""

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


class TestDataProcessing:
    """Test data processing functions without network access."""

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
        """Test the compute_data_coverage function."""
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


class TestGeographicFilters:
    """Test geographic filtering functions."""

    def test_box_filter_global(self):
        """Test box filter with global bounds (no filtering)."""
        # Create a simple test dataset
        ds = xr.Dataset({
            "latitude": (["station_id"], [40.0, 42.0, 38.0]),
            "longitude": (["station_id"], [-70.0, -72.0, -68.0]),
            "station_id": ["A", "B", "C"]
        })

        filtered = geographic_filters.box_filter_buoys(ds)

        # Should return all stations
        assert len(filtered.station_id) == 3

    def test_box_filter_custom_region(self):
        """Test box filter with custom region."""
        # Create a test dataset with known coordinates
        ds = xr.Dataset({
            "latitude": (["station_id"], [40.0, 42.0, 30.0]),
            "longitude": (["station_id"], [-70.0, -72.0, -60.0]),
            "station_id": ["A", "B", "C"]
        })

        # Filter to only include stations A and B
        filtered = geographic_filters.box_filter_buoys(
            ds,
            lon1=-75,
            lon2=-65,
            lat1=35,
            lat2=45
        )

        assert len(filtered.station_id) == 2
        # Station C should be filtered out
        assert "C" not in filtered.station_id.values

    def test_filter_by_region_wrapper(self):
        """Test the user-facing filter_by_region function."""
        ds = xr.Dataset({
            "latitude": (["station_id"], [40.0, 25.0]),
            "longitude": (["station_id"], [-70.0, -80.0]),
            "station_id": ["A", "B"]
        })

        filtered = xbuoy.filter_by_region(
            ds,
            lon_min=-75,
            lon_max=-65,
            lat_min=35,
            lat_max=45
        )

        # Only station A should remain
        assert len(filtered.station_id) == 1
        assert filtered.station_id.values[0] == "A"

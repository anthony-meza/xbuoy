"""
xbuoy - A Python package for accessing and analyzing NOAA NDBC buoy data.

This package provides tools to fetch, process, and visualize oceanographic data
from NOAA's National Data Buoy Center (NDBC).
"""

# Read version from installed package
from importlib.metadata import version
__version__ = version("xbuoy")

# ===== HIGH-LEVEL USER API (recommended) =====
from .core import (
    list_stations,
    fetch_data,
    filter_by_region,
)

from .plotting import (
    plot_stations,
)

# ===== ADVANCED/BACKEND FUNCTIONS =====
# Only needed for advanced customization
from .station_metadata import (
    get_buoy_metadata,
    get_buoy_stations,
    get_historical_bounds,
    fetch_station_historical_bounds,
)

from .data_retrieval import (
    extract_historical_year,
    get_station_records,
)

from .data_processing import (
    add_latitude_longitude,
    add_variable_coverage,
    compute_data_coverage,
)

from .geographic_filters import (
    box_filter_buoys,
)

# Main user-facing API
__all__ = [
    # === CORE USER API (Start here!) ===
    "list_stations",       # Get station metadata
    "fetch_data",          # Download buoy data
    "filter_by_region",    # Filter to geographic region
    "plot_stations",       # Plot station locations on map

    # === Advanced functions ===
    # Metadata
    "get_buoy_metadata",
    "get_buoy_stations",
    "get_historical_bounds",
    "fetch_station_historical_bounds",
    # Data retrieval
    "extract_historical_year",
    "get_station_records",
    # Data processing
    "add_latitude_longitude",
    "add_variable_coverage",
    "compute_data_coverage",
    # Geographic filters
    "box_filter_buoys",
]

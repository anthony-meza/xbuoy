# Read version from installed package
from importlib.metadata import version
__version__ = version("xbuoy")

from .core import (
    list_stations,
    fetch_data,
    filter_by_region,
)

from .plotting import (
    plot_stations,
)

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

__all__ = [
    "list_stations",       # Get station metadata
    "fetch_data",          # Download buoy data
    "filter_by_region",    # Filter to geographic region
    "plot_stations",       # Plot station locations on map
    "get_buoy_metadata",
    "get_buoy_stations",
    "get_historical_bounds",
    "fetch_station_historical_bounds",
    "extract_historical_year",
    "get_station_records",
    "add_latitude_longitude",
    "add_variable_coverage",
    "compute_data_coverage",
    "box_filter_buoys",
]

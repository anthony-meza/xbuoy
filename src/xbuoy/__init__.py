from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("xbuoy")
except PackageNotFoundError:
    __version__ = "0.1.0"

from .core import (
    list_stations,
    list_available,
    fetch_data,
    filter_by_region,
)

try:
    from .plotting import (
        plot_stations,
    )
except ImportError:
    def plot_stations(*args, **kwargs):
        raise ImportError(
            "plot_stations requires optional plotting dependencies such as "
            "matplotlib and cartopy."
        )

from .station_metadata import (
    get_buoy_metadata,
    get_buoy_stations,
    get_historical_bounds,
    fetch_station_historical_bounds,
)

from .data_retrieval import (
    extract_historical_year,
    extract_realtime,
    historical_index,
    historical_mode_index,
    historical_modes,
    get_station_records,
    read_ndbc_raw,
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
    "list_available",      # List historical file availability
    "fetch_data",          # Download buoy data
    "filter_by_region",    # Filter to geographic region
    "plot_stations",       # Plot station locations on map
    "get_buoy_metadata",
    "get_buoy_stations",
    "get_historical_bounds",
    "fetch_station_historical_bounds",
    "extract_historical_year",
    "extract_realtime",
    "historical_index",
    "historical_mode_index",
    "historical_modes",
    "get_station_records",
    "read_ndbc_raw",
    "add_latitude_longitude",
    "add_variable_coverage",
    "compute_data_coverage",
    "box_filter_buoys",
]

"""Internal NOAA text parsers; callers provide text, not URLs."""

from .observations import parse_observation_table, table_to_dataset
from .stations import parse_station_table

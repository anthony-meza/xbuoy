"""Discover NOAA buoys and load original-resolution observations into xarray."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("xndbc")
except PackageNotFoundError:
    __version__ = "0.2.0"

from . import accessor as _accessor  # noqa: F401 -- registers the xarray accessor
from . import stations
from .core import RetrievalError, fetch_historical, fetch_realtime
from ._products import list_modes

__all__ = [
    "stations",
    "list_modes",
    "fetch_historical",
    "fetch_realtime",
    "RetrievalError",
]

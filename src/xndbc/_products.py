"""Describe the NOAA data products that xndbc understands."""

from dataclasses import dataclass
from typing import Literal

import xarray as xr


@dataclass(frozen=True)
class NDBCProduct:
    """Describe a NOAA product's location and observation layout.

    historical indicates archive support; realtime_extension=None means no
    realtime feed. layout selects column handling, not a separate parser class.
    """

    description: str
    historical: bool
    realtime_extension: str | None
    layout: Literal["table", "spectrum", "adcp"] = "table"


MODES = {
    "stdmet": NDBCProduct(
        description="Standard meteorological observations",
        historical=True,
        realtime_extension="txt",
    ),
    "cwind": NDBCProduct(
        description="Continuous wind observations",
        historical=True,
        realtime_extension="cwind",
    ),
    "supl": NDBCProduct(
        description="Supplemental meteorological observations",
        historical=True,
        realtime_extension="supl",
    ),
    "ocean": NDBCProduct(
        description="Oceanographic observations",
        historical=True,
        realtime_extension="ocean",
    ),
    "spec": NDBCProduct(
        description="Wave summary and steepness",
        historical=False,
        realtime_extension="spec",
    ),
    "adcp": NDBCProduct(
        description="Acoustic Doppler current profiles",
        historical=True,
        realtime_extension="adcp",
        layout="adcp",
    ),
    "adcp2": NDBCProduct(
        description="Additional acoustic Doppler current profiles",
        historical=True,
        realtime_extension=None,
        layout="adcp",
    ),
    "swden": NDBCProduct(
        description="Wave spectral density",
        historical=True,
        realtime_extension="data_spec",
        layout="spectrum",
    ),
    "swdir": NDBCProduct(
        description="Mean wave direction by frequency",
        historical=True,
        realtime_extension="swdir",
        layout="spectrum",
    ),
    "swdir2": NDBCProduct(
        description="Principal wave direction by frequency",
        historical=True,
        realtime_extension="swdir2",
        layout="spectrum",
    ),
    "swr1": NDBCProduct(
        description="First directional Fourier magnitude",
        historical=True,
        realtime_extension="swr1",
        layout="spectrum",
    ),
    "swr2": NDBCProduct(
        description="Second directional Fourier magnitude",
        historical=True,
        realtime_extension="swr2",
        layout="spectrum",
    ),
}


def list_modes() -> xr.Dataset:
    """Describe supported products along ``mode``, without accessing NOAA.

    ``historical`` and ``realtime`` describe product support, not availability
    at any particular station. Use :func:`xndbc.stations.availability` for archive files.
    """
    names = list(MODES)
    products = list(MODES.values())
    return xr.Dataset(
        {
            "description": ("mode", [product.description for product in products]),
            "historical": ("mode", [product.historical for product in products]),
            "realtime": (
                "mode",
                [product.realtime_extension is not None for product in products],
            ),
        },
        coords={"mode": names},
    )


def validate_mode(mode, feed="historical"):
    if not isinstance(mode, str):
        raise TypeError("mode must be a string; inspect xndbc.list_modes()")
    mode = mode.strip().lower()
    choices = [
        name
        for name, product in MODES.items()
        if (
            product.historical
            if feed == "historical"
            else product.realtime_extension is not None
        )
    ]
    if mode not in choices:
        raise ValueError(
            f"Unsupported {feed} mode {mode!r}. Choose from {', '.join(choices)}"
        )
    return mode

"""Describe the NOAA data products that xndbc understands."""

from dataclasses import dataclass
from typing import Literal

import xarray as xr


@dataclass(frozen=True)
class NDBCProduct:
    """Describe a product's feed locations and parser layout.

    Attributes:
        description: Human-readable product description.
        historical: Whether an archive index is supported.
        realtime_extension: NOAA realtime suffix, or None without realtime support.
        layout: Parser layout: table, spectrum, or adcp.
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
    """Describe supported products without accessing NOAA.

    Returns:
        An xarray Dataset indexed by mode, with description and boolean historical
        and realtime support flags. Support does not guarantee station-level files;
        inspect a station dataset's ndbc.availability() for archive file presence.
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
    """Normalize a product code and require support for the requested feed.

    Raises:
        TypeError: If mode is not a string.
        ValueError: If the product does not support the requested feed.
    """
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

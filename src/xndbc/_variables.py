"""Variable descriptions from https://www.ndbc.noaa.gov/faq/measdes.shtml.

Never apply numeric missing-value codes across unrelated variables: 99 degrees
is a valid direction. Unknown columns retain numeric values and header units.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class VariableMetadata:
    """Describe one measurement's units and numeric missing marker.

    Attributes:
        long_name: Human-readable measurement description.
        units: Units attached to the xarray variable.
        missing_value: Numeric sentinel to replace with NaN, or None to preserve
            all numeric values. Text missing markers are handled by the parser.
    """

    long_name: str
    units: str
    missing_value: float | None


VARIABLES = {
    "WD": VariableMetadata(
        long_name="Wind direction", units="degree", missing_value=999
    ),
    "WDIR": VariableMetadata(
        long_name="Wind direction", units="degree", missing_value=999
    ),
    "WSPD": VariableMetadata(long_name="Wind speed", units="m s-1", missing_value=99),
    "GST": VariableMetadata(
        long_name="Wind gust speed", units="m s-1", missing_value=99
    ),
    "WVHT": VariableMetadata(
        long_name="Significant wave height", units="m", missing_value=99
    ),
    "DPD": VariableMetadata(
        long_name="Dominant wave period", units="s", missing_value=99
    ),
    "APD": VariableMetadata(
        long_name="Average wave period", units="s", missing_value=99
    ),
    "MWD": VariableMetadata(
        long_name="Mean wave direction", units="degree", missing_value=999
    ),
    "PRES": VariableMetadata(
        long_name="Air pressure at sea level", units="hPa", missing_value=9999
    ),
    "BAR": VariableMetadata(
        long_name="Air pressure at sea level", units="hPa", missing_value=9999
    ),
    "ATMP": VariableMetadata(
        long_name="Air temperature", units="degC", missing_value=999
    ),
    "WTMP": VariableMetadata(
        long_name="Water temperature", units="degC", missing_value=999
    ),
    "DEWP": VariableMetadata(
        long_name="Dew point temperature", units="degC", missing_value=999
    ),
    "VIS": VariableMetadata(long_name="Visibility", units="nmi", missing_value=99),
    "PTDY": VariableMetadata(
        long_name="Three-hour pressure tendency", units="hPa", missing_value=99
    ),
    "TIDE": VariableMetadata(
        long_name="Water level relative to mean lower low water",
        units="ft",
        missing_value=99,
    ),
    "SWH": VariableMetadata(long_name="Swell height", units="m", missing_value=99),
    "SWP": VariableMetadata(long_name="Swell period", units="s", missing_value=99),
    "WWH": VariableMetadata(long_name="Wind wave height", units="m", missing_value=99),
    "WWP": VariableMetadata(long_name="Wind wave period", units="s", missing_value=99),
    "SWDEN": VariableMetadata(
        long_name="Wave spectral density", units="m2 Hz-1", missing_value=999
    ),
    "SWDIR": VariableMetadata(
        long_name="Mean wave direction", units="degree", missing_value=999
    ),
    "SWDIR2": VariableMetadata(
        long_name="Principal wave direction", units="degree", missing_value=999
    ),
    "SWR1": VariableMetadata(
        long_name="First directional Fourier magnitude", units="1", missing_value=999
    ),
    "SWR2": VariableMetadata(
        long_name="Second directional Fourier magnitude", units="1", missing_value=999
    ),
    "SEP_FREQ": VariableMetadata(
        long_name="Swell and wind wave separation frequency",
        units="Hz",
        missing_value=9.999,
    ),
    "DEP": VariableMetadata(
        long_name="Current measurement depth", units="m", missing_value=None
    ),
    "DIR": VariableMetadata(
        long_name="Current direction", units="degree", missing_value=None
    ),
    "SPD": VariableMetadata(
        long_name="Current speed", units="cm s-1", missing_value=None
    ),
}


def annotate(dataset, header_units=None):
    """Attach measurement and coordinate metadata in place.

    Args:
        dataset: Parsed observations with a time coordinate.
        header_units: Optional mapping of NOAA column names to source units.

    Returns:
        The same dataset. Known definitions take precedence; unknown variables
        retain supplied header units when available.
    """
    for name, variable in dataset.data_vars.items():
        if name in VARIABLES:
            definition = VARIABLES[name]
            variable.attrs.update(
                long_name=definition.long_name, units=definition.units
            )
        elif header_units and name in header_units and header_units[name] != "-":
            variable.attrs["units"] = header_units[name]
    if "frequency" in dataset.coords:
        dataset.frequency.attrs.update(long_name="Wave frequency", units="Hz")
    if "depth_bin" in dataset.coords:
        dataset.depth_bin.attrs["long_name"] = (
            "Current meter bin (see DEP for depth in metres)"
        )
    dataset.time.attrs.update(standard_name="time", long_name="Time", timezone="UTC")
    return dataset

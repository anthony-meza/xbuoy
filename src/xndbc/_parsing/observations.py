"""Parse NOAA observation text and convert it to labeled xarray datasets."""

import re
from io import StringIO

import numpy as np
import pandas as pd
import xarray as xr

from .._products import MODES
from .._variables import VARIABLES, annotate

ADCP_COLUMNS = ("DEP", "DIR", "SPD")
TIME_COLUMN_NAMES = {
    "YY": "year",
    "YYYY": "year",
    "MM": "month",
    "DD": "day",
    "hh": "hour",
    "mm": "minute",
}
# NDBC began in 1970: 70–99 refer to the 1900s and 00–69 to the 2000s.
TWO_DIGIT_YEAR_CUTOFF = 70
FREQUENCY_COLUMN = re.compile(r"(?:\d+(?:\.\d*)?|\.\d+)")
# Realtime spectra repeat "measurement (frequency)" after each timestamp.
SPECTRAL_PAIR = re.compile(r"(\S+)\s+\(([\d.]+)\)")
SPECTRAL_VALUES = re.compile(r"(?:\S+\s+\([\d.]+\)\s*)+")


def parse_observation_table(body: str, mode: str = "stdmet") -> pd.DataFrame:
    """Read a NOAA table, preserving text fields and variable-specific missing values."""
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    headers = [line.lstrip("#").split() for line in lines if line.startswith("#")]
    rows = [line for line in lines if not line.startswith("#")]
    if not rows:
        raise ValueError("The NOAA file contains no observations")
    if not headers:
        headers = [rows.pop(0).split()]
    column_names = headers[0]
    if not rows or column_names[0] not in {"YY", "YYYY"}:
        raise ValueError("Unrecognized NOAA observation header")

    product = MODES[mode]
    if product.layout == "spectrum" and "(" in rows[0]:
        frame = _parse_realtime_spectrum(rows, column_names, mode)
    else:
        frame, column_names = _parse_regular_table(rows, column_names, product.layout)

    # 99 can be a valid direction: never replace sentinels across the entire table.
    for column in frame:
        if column in TIME_COLUMN_NAMES:
            continue
        variable_name = str(column).upper()
        if product.layout == "spectrum" and FREQUENCY_COLUMN.fullmatch(variable_name):
            variable_name = mode.upper()
        metadata = VARIABLES.get(variable_name)
        if metadata and metadata.missing_value is not None:
            frame[column] = frame[column].replace(metadata.missing_value, np.nan)

    # Ignore unmatched units rows rather than assigning units to the wrong columns.
    if len(headers) > 1 and len(headers[1]) == len(column_names):
        frame.attrs["units"] = dict(
            zip((name.upper() for name in column_names), headers[1], strict=True)
        )
    return frame


def _parse_realtime_spectrum(rows, column_names, mode):
    """Align repeated value/frequency pairs; swden also includes separation frequency."""
    time_count = sum(name in TIME_COLUMN_NAMES for name in column_names)
    prefix_names = column_names[:time_count]
    if mode == "swden":
        prefix_names = [*prefix_names, "SEP_FREQ"]
    prefix_count = len(prefix_names)
    observations = []
    for row in rows:
        parts = row.split(maxsplit=prefix_count)
        if len(parts) != prefix_count + 1 or not SPECTRAL_VALUES.fullmatch(parts[-1]):
            raise ValueError("Malformed paired-frequency spectrum")
        observation = dict(zip(prefix_names, parts[:-1], strict=True))
        observation.update(
            (str(float(frequency)), value)
            for value, frequency in SPECTRAL_PAIR.findall(parts[-1])
        )
        observations.append(observation)
    frame = pd.DataFrame(observations)
    return frame.mask(frame.isin(["MM", "N/A"])).apply(pd.to_numeric, errors="raise")


def _parse_regular_table(rows, column_names, layout):
    """Read fixed columns or ADCP depth groups, returning the effective header too."""
    widths = [len(row.split()) for row in rows]
    is_adcp = layout == "adcp"
    width = max(widths) if is_adcp else widths[0]
    time_names = [name for name in column_names if name in TIME_COLUMN_NAMES]
    if len(column_names) != width:
        if not is_adcp:
            raise ValueError(
                f"NOAA header has {len(column_names)} columns, observations have {width}"
            )
        bin_count, remainder = divmod(width - len(time_names), len(ADCP_COLUMNS))
        if remainder or bin_count < 1:
            raise ValueError("Malformed ADCP depth bins")
        column_names = time_names + [
            f"{name}{depth_bin:02d}"
            for depth_bin in range(1, bin_count + 1)
            for name in ADCP_COLUMNS
        ]
    if is_adcp:
        # Rows may omit trailing bins, but each present depth/direction/speed group is whole.
        if any((width - len(time_names)) % len(ADCP_COLUMNS) for width in widths):
            raise ValueError("Incomplete ADCP depth bin")
    elif any(width != len(column_names) for width in widths):
        raise ValueError("Inconsistent NOAA observation row widths")
    frame = pd.read_csv(
        StringIO("\n".join(rows)),
        sep=r"\s+",
        names=column_names,
        na_values=["MM", "N/A"],
        keep_default_na=False,
    )
    return frame, column_names


def _index_by_time(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.rename(columns=TIME_COLUMN_NAMES)
    frame = frame.assign(
        minute=frame.get("minute", 0),
        hour=frame.get("hour", 0),
    )
    years = pd.to_numeric(frame["year"], errors="raise")
    # NDBC began in 1970; two-digit archive years below 70 are in the 2000s.
    frame["year"] = np.where(
        years < TWO_DIGIT_YEAR_CUTOFF,
        2000 + years,
        np.where(years < 100, 1900 + years, years),
    )
    frame["time"] = pd.to_datetime(frame[["year", "month", "day", "hour", "minute"]])
    return frame.drop(columns=["year", "month", "day", "hour", "minute"]).set_index(
        "time"
    )


def table_to_dataset(frame: pd.DataFrame, mode: str) -> xr.Dataset:
    """Return original-resolution observations with labeled dimensions."""
    header_units = frame.attrs.get("units", {})
    frame = _index_by_time(frame)
    if MODES[mode].layout == "adcp":
        bins = sorted(
            int(str(col)[3:]) for col in frame if re.fullmatch(r"DEP\d+", str(col))
        )
        if not bins:
            raise ValueError("ADCP file has no recognizable depth bins")
        variables = {}
        for name in ADCP_COLUMNS:
            columns = [f"{name}{i:02d}" for i in bins]
            variables[name] = (
                ("time", "depth_bin"),
                frame.reindex(columns=columns).apply(pd.to_numeric).to_numpy(),
            )
        dataset = xr.Dataset(variables, coords={"time": frame.index, "depth_bin": bins})
    elif MODES[mode].layout == "spectrum":
        frequencies = pd.to_numeric(pd.Index(frame.columns), errors="coerce")
        names = frame.columns[frequencies.notna()]
        if names.empty:
            raise ValueError("Spectrum has no recognizable frequency columns")
        dataset = xr.Dataset(
            {
                mode.upper(): (
                    ("time", "frequency"),
                    frame[names].apply(pd.to_numeric).to_numpy(),
                )
            },
            coords={
                "time": frame.index,
                "frequency": frequencies[frequencies.notna()].astype(float),
            },
        ).sortby("frequency")
        if "SEP_FREQ" in frame:
            dataset["SEP_FREQ"] = ("time", frame.SEP_FREQ.to_numpy())
    else:
        dataset = frame.to_xarray()
    dataset = dataset.rename({name: str(name).upper() for name in dataset.data_vars})
    return annotate(
        dataset.sortby("time").drop_duplicates("time", keep="first"), header_units
    )

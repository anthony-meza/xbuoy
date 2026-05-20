"""
Data retrieval functions for NDBC buoy observations.

This module provides functions to fetch historical and realtime observational
data from NOAA NDBC buoys, including temperature, wave, wind, and other
oceanographic measurements.
"""

import pandas as pd
import numpy as np
import xarray as xr
import concurrent.futures
import re
from functools import lru_cache
from io import StringIO
from typing import List, Optional
from urllib.request import urlopen
from tqdm import tqdm

NDBC_HISTORICAL_ROOT_URL = "https://www.ndbc.noaa.gov/data/historical"
NDBC_REALTIME_URL = "https://www.ndbc.noaa.gov/data/realtime2"
NDBC_REALTIME_EXTENSIONS = {
    "stdmet": "txt",
    "adcp": "adcp",
    "cwind": "cwind",
    "ocean": "ocean",
    "spec": "spec",
    "supl": "supl",
    "swden": "swden",
    "swdir": "swdir",
    "swdir2": "swdir2",
    "swr1": "swr1",
    "swr2": "swr2",
}
NDBC_NA_VALUES = {
    "adcp": None,
    "adcp2": None,
    "spec": ["N/A"],
    "stdmet": ["MM", 99.0, 999, 9999, 9999.0],
    "cwind": [99.0, 999, 9999, 9999.0, "MM"],
    "supl": [99.0, 999, 999.0, 9999, 9999.0, "MM"],
    "swden": [99.0, 999, 999.0, 9999, 9999.0, "MM"],
    "swdir": [99.0, 999, 999.0, 9999, 9999.0, "MM"],
    "swdir2": [99.0, 999, 999.0, 9999, 9999.0, "MM"],
    "swr1": [99.0, 999, 999.0, 9999, 9999.0, "MM"],
    "swr2": [99.0, 999, 999.0, 9999, 9999.0, "MM"],
}
SAMPLE_RATE_ALIASES = {
    "H": "h",
    "M": "ME",
}


@lru_cache(maxsize=1)
def historical_modes() -> list[str]:
    """List historical NDBC data modes from the historical directory index."""
    body = _read_url_text(f"{NDBC_HISTORICAL_ROOT_URL}/")
    modes = re.findall(r'href="([^"/]+)/"', body)
    return sorted(mode for mode in modes if mode != "..")


def parse_historical_filename(filename: str, mode: str) -> Optional[dict]:
    """Parse station and year from an NDBC historical filename."""
    suffix = ".txt.gz"
    if not filename.endswith(suffix):
        return None
    stem = filename[: -len(suffix)]
    if len(stem) < 6 or not stem[-4:].isdigit() or not stem[-5].isalpha():
        return None

    return {
        "station_id": stem[:-5].lower(),
        "mode": mode,
        "year": int(stem[-4:]),
        "filename": filename,
    }


@lru_cache(maxsize=None)
def historical_mode_index(mode: str) -> pd.DataFrame:
    """Index historical files available for one NDBC data mode."""
    mode = mode.lower()
    url = f"{NDBC_HISTORICAL_ROOT_URL}/{mode}/"
    body = _read_url_text(url)
    filenames = re.findall(r'href="([^"]+\.txt\.gz)"', body)
    rows = []
    for filename in filenames:
        parsed = parse_historical_filename(filename, mode)
        if parsed is not None:
            parsed["url"] = f"{url}{filename}"
            rows.append(parsed)
    return pd.DataFrame(rows)


def historical_index(modes: Optional[list[str]] = None) -> pd.DataFrame:
    """Index historical files available across NDBC data modes."""
    if modes is None:
        modes = historical_modes()
    elif isinstance(modes, str):
        modes = [modes]
    indexes = [historical_mode_index(mode).copy() for mode in modes]
    indexes = [index for index in indexes if not index.empty]
    if not indexes:
        return pd.DataFrame(columns=["station_id", "mode", "year", "filename", "url"])
    return pd.concat(indexes, ignore_index=True)


def _availability_dataset(available: pd.DataFrame) -> xr.Dataset:
    """Convert an availability dataframe to the public xarray representation."""
    if available.empty:
        available = pd.DataFrame(
            columns=["station_id", "mode", "year", "filename", "url"]
        )
    available = available.reset_index(drop=True)
    available.index.name = "file"
    return available.to_xarray()


def list_available(mode: Optional[str] = "stdmet") -> xr.Dataset:
    """
    List available NDBC historical files.

    Parameters
    ----------
    mode : str, optional
        Historical data mode to list. Use None to list all historical modes.

    Returns
    -------
    xr.Dataset
        Variables include station_id, mode, year, filename, and url.
    """
    modes = None if mode is None else [mode.lower()]
    return _availability_dataset(historical_index(modes=modes))


def historical_url(station_id: str, year: int, mode: str = "stdmet") -> str:
    """Build an NDBC historical data file URL."""
    mode = mode.lower()
    available = historical_index(modes=[mode])
    matches = available[
        (available["station_id"] == str(station_id).lower())
        & (available["year"] == int(year))
    ]
    if matches.empty:
        raise ValueError(f"No historical {mode} file found for station {station_id}, year {year}")
    return matches.iloc[0]["url"]


def historical_stdmet_url(station_id: str, year: int) -> str:
    """Build the NDBC historical standard meteorological file URL."""
    return historical_url(station_id, year, mode="stdmet")


def realtime_url(station_id: str, mode: str = "stdmet") -> str:
    """Build an NDBC realtime data file URL."""
    mode = mode.lower()
    if mode not in NDBC_REALTIME_EXTENSIONS:
        raise ValueError(f"Unsupported realtime mode: {mode}")
    extension = NDBC_REALTIME_EXTENSIONS[mode]
    return f"{NDBC_REALTIME_URL}/{station_id.upper()}.{extension}"


def realtime_stdmet_url(station_id: str) -> str:
    """Build the NDBC realtime standard meteorological file URL."""
    return realtime_url(station_id, mode="stdmet")


def read_ndbc_raw(url: str) -> pd.DataFrame:
    """Read an NDBC data file as a raw numeric table."""
    return pd.read_csv(
        url,
        sep=r"\s+",
        comment="#",
        header=None,
        compression="infer",
    )


def _read_url_text(url: str) -> str:
    with urlopen(url, timeout=30) as response:
        raw = response.read()
    if url.endswith(".gz"):
        import gzip
        return gzip.decompress(raw).decode("utf-8", errors="ignore")
    return raw.decode("utf-8", errors="ignore")


def _read_ndbc_table_from_text(body: str, mode: str = "stdmet") -> pd.DataFrame:
    """Read an NDBC whitespace-delimited observation table from response text."""
    mode = mode.lower()
    header = []
    data = []
    for line in body.splitlines():
        if line.startswith("#"):
            header.append(line)
        elif line.strip():
            data.append(line)

    if not data:
        return pd.DataFrame()

    names = None
    if header:
        names = [name for name in header[0].strip("#").split() if name]
    elif any(char.isalpha() for char in data[0]):
        names = data[0].split()
        data = data[1:]

    # Some NDBC files have stale or abbreviated headers. If the parsed header
    # cannot describe the data row, let pandas assign integer column names.
    row_width = len(data[0].split())
    if names is not None and len(names) != row_width:
        names = None

    return pd.read_csv(
        StringIO("\n".join(data)),
        sep=r"\s+",
        header=None,
        names=names,
        na_values=NDBC_NA_VALUES.get(mode, ["MM"]),
    )


def _read_ndbc_table(url: str, mode: str = "stdmet") -> pd.DataFrame:
    """Read an NDBC whitespace-delimited observation table from a URL."""
    return _read_ndbc_table_from_text(_read_url_text(url), mode=mode)


def _timestamped_dataframe(sdf: pd.DataFrame) -> pd.DataFrame:
    """Normalize NDBC date columns and return a time-indexed dataframe."""
    replace_names = {
        "YY": "year",
        "#YY": "year",
        "YYYY": "year",
        "#YYYY": "year",
        "MM": "month",
        "DD": "day",
        "hh": "hour",
        "mm": "minute",
    }

    sdf["mm"] = 0 if "mm" not in sdf.columns else sdf["mm"]
    sdf["hh"] = 1 if "hh" not in sdf.columns else sdf["hh"]
    sdf = sdf.rename(columns=replace_names)
    sdf["year"] = pd.to_numeric(sdf["year"], errors="coerce")
    sdf["year"] = np.where(sdf["year"] < 100, 1900 + sdf["year"], sdf["year"])

    dt_cols = ["year", "month", "day", "hour", "minute"]
    sdf["time"] = pd.to_datetime(sdf[dt_cols])
    return sdf.drop(columns=dt_cols).set_index("time").sort_index()


def _adcp_dataset(sdf: pd.DataFrame) -> xr.Dataset:
    """Reshape ADCP DEP/DIR/SPD columns onto a depth_bin dimension."""
    groups = {"DEP": {}, "DIR": {}, "SPD": {}}
    for column in sdf.columns:
        match = re.match(r"^(DEP|DIR|SPD)(\d+)$", str(column))
        if match is not None:
            variable, bin_number = match.groups()
            groups[variable][int(bin_number)] = column

    depth_bins = sorted({bin_number for columns in groups.values() for bin_number in columns})
    if not depth_bins:
        return sdf.to_xarray()

    data_vars = {}
    for variable, columns in groups.items():
        if not columns:
            continue
        values = np.full((len(sdf.index), len(depth_bins)), np.nan)
        for j, bin_number in enumerate(depth_bins):
            if bin_number in columns:
                values[:, j] = pd.to_numeric(sdf[columns[bin_number]], errors="coerce")
        data_vars[variable] = (("time", "depth_bin"), values)

    return xr.Dataset(
        data_vars=data_vars,
        coords={
            "time": sdf.index,
            "depth_bin": depth_bins,
        },
    )


def _spectral_dataset(sdf: pd.DataFrame, mode: str) -> xr.Dataset:
    """Reshape spectral wave columns onto a frequency dimension."""
    frequency_columns = []
    for column in sdf.columns:
        try:
            frequency_columns.append((float(str(column)), column))
        except ValueError:
            continue

    if not frequency_columns:
        return sdf.to_xarray()

    frequency_columns = sorted(frequency_columns)
    frequencies = [frequency for frequency, _ in frequency_columns]
    columns = [column for _, column in frequency_columns]
    values = sdf[columns].apply(pd.to_numeric, errors="coerce").to_numpy()

    return xr.Dataset(
        data_vars={
            mode: (("time", "frequency"), values),
        },
        coords={
            "time": sdf.index,
            "frequency": frequencies,
        },
    )


def _observation_dataset(sdf: pd.DataFrame, mode: str, sample_rate: str) -> xr.Dataset:
    """Convert an NDBC observation table to a mode-aware xarray dataset."""
    mode = mode.lower()
    sample_rate = SAMPLE_RATE_ALIASES.get(sample_rate, sample_rate)
    sdf = _timestamped_dataframe(sdf)

    if mode in {"adcp", "adcp2"}:
        ds = _adcp_dataset(sdf)
    elif mode in {"swden", "swdir", "swdir2", "swr1", "swr2"}:
        ds = _spectral_dataset(sdf, mode)
    else:
        ds = sdf.to_xarray()

    return ds.sortby("time").resample(time=sample_rate).mean("time")


def extract_historical_year(
    yr: int,
    station_id: str = 'tplm2',
    sample_rate: str = "D",
    display_error: bool = False,
    mode: str = "stdmet"
) -> Optional[xr.Dataset]:
    """
    Extract and process historical data for a specific year and station.

    Parameters
    ----------
    yr : int
        Year to extract data for.
    station_id : str, optional
        ID of the station (default is 'tplm2').
    sample_rate : str, optional
        Resampling rate for pandas resample (default is daily "D").
        Examples: "D" (daily), "W" (weekly), "M" (monthly).
    display_error : bool, optional
        Whether to print error messages (default is False).
    mode : str, optional
        NDBC historical data mode to fetch (default is "stdmet").

    Returns
    -------
    xr.Dataset or None
        Processed data resampled to the specified sample rate.
        Returns None if data extraction fails.
    """
    try:
        mode = mode.lower()
        sdf = _read_ndbc_table(historical_url(station_id, yr, mode=mode), mode=mode)

        # If "WTMP" (water temperature) is not in the columns, return None
        if mode == "stdmet" and ("WTMP" not in sdf.columns) and display_error:
            print(f"WTMP not found for station {station_id}, year {yr}")

        return _observation_dataset(sdf, mode, sample_rate)

    except Exception as e:
        if display_error:
            print(f"Error extracting data for station {station_id}, year {yr}: {e}")
        return None


def extract_realtime(
    station_id: str = "tplm2",
    sample_rate: str = "H",
    display_error: bool = False,
    mode: str = "stdmet"
) -> Optional[xr.Dataset]:
    """
    Extract and process recent realtime data for a station.

    Parameters
    ----------
    station_id : str, optional
        ID of the station (default is 'tplm2').
    sample_rate : str, optional
        Resampling rate for pandas resample (default is hourly "H").
    display_error : bool, optional
        Whether to print error messages (default is False).
    mode : str, optional
        NDBC realtime data mode to fetch (default is "stdmet").

    Returns
    -------
    xr.Dataset or None
        Processed realtime data resampled to the specified sample rate.
    """
    try:
        mode = mode.lower()
        sdf = _read_ndbc_table(realtime_url(station_id, mode=mode), mode=mode)
        return _observation_dataset(sdf, mode, sample_rate)
    except Exception as e:
        if display_error:
            print(f"Error extracting realtime data for station {station_id}: {e}")
        return None


def get_station_records(
    station_list: List[str],
    years: Optional[List[int]] = None,
    sample_rate: str = "D",
    debugging: bool = False,
    data_type: str = "historical",
    mode: str | List[str] = "stdmet",
    max_workers: int = 6,
) -> xr.Dataset:
    """
    Retrieve and process historical records for multiple stations and years.

    This function fetches data in parallel for efficiency and combines all
    station records into a single xarray Dataset.

    Parameters
    ----------
    station_list : list of str
        List of station IDs to fetch data for.
    years : list of int, optional
        List of years to extract data for. Required for historical data.
    sample_rate : str, optional
        Resampling rate (default is daily "D").
    debugging : bool, optional
        If True, processes data sequentially for easier debugging (default is False).
    data_type : {"historical", "realtime"}, optional
        Which NDBC feed to retrieve.
    mode : str or list of str, optional
        Which NDBC data mode(s) to retrieve (default is "stdmet").
    max_workers : int, optional
        Maximum number of concurrent file reads per station.

    Returns
    -------
    xr.Dataset
        Merged dataset containing historical records for all stations and years.
        Includes a 'station_id' dimension.
    """
    data_type = data_type.lower()
    if isinstance(mode, list):
        datasets = [
            get_station_records(
                station_list=station_list,
                years=years,
                sample_rate=sample_rate,
                debugging=debugging,
                data_type=data_type,
                mode=single_mode,
                max_workers=max_workers,
            )
            for single_mode in mode
        ]
        datasets = [ds for ds in datasets if ds.data_vars]
        if not datasets:
            return xr.Dataset()
        return xr.merge(datasets, compat="override", join="outer")

    mode = mode.lower()
    if data_type not in {"historical", "realtime"}:
        raise ValueError("data_type must be 'historical' or 'realtime'")
    if data_type == "historical" and years is None:
        raise ValueError("years is required when data_type='historical'")

    xxsdf = []

    for station_id in tqdm(station_list, desc="Fetching stations", unit="station"):
        if data_type == "realtime":
            results = [extract_realtime(station_id=station_id, sample_rate=sample_rate, mode=mode)]
        else:
            particular_historical_record = lambda yr: extract_historical_year(
                yr, station_id=station_id, sample_rate=sample_rate, mode=mode
            )

            if debugging:
                results = [particular_historical_record(yr) for yr in years]
            else:
                with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                    results = list(executor.map(particular_historical_record, years))

        results = [r for r in results if r is not None]

        if len(results) == 1:
            xsdf = results[0].sortby("time")
            xsdf = xsdf.drop_duplicates("time")
            xsdf = xsdf.assign_coords(station_id=station_id).expand_dims("station_id")
            xxsdf.append(xsdf)
        elif len(results) > 1:
            xsdf = xr.concat(results, dim="time").sortby("time")
            xsdf = xsdf.drop_duplicates("time")  # sometimes the records overlap
            xsdf = xsdf.assign_coords(station_id=station_id).expand_dims("station_id")
            xxsdf.append(xsdf)

    if not xxsdf:
        return xr.Dataset()

    return xr.merge(xxsdf, compat="no_conflicts", join="outer")

"""Read station IDs, descriptions, and coordinates from NOAA station tables."""

import re
from html import unescape

import numpy as np
import xarray as xr

LOCATION = re.compile(r"([\d.]+)\s*([NS])\s+([\d.]+)\s*([EW])")


def _plain_text(value):
    """Remove HTML tags and decode entities in a station metadata field."""
    return " ".join(unescape(re.sub(r"<[^>]+>", " ", value)).split())


def parse_station_table(body: str) -> xr.Dataset:
    """Parse NOAA station metadata and geographic coordinates.

    Args:
        body: Pipe-delimited NOAA station catalog text.

    Returns:
        An xarray Dataset indexed by station_id, with location coordinates in
        degrees and descriptive text fields. Missing or unrecognized locations
        remain NaN; HTML markup is removed from descriptive fields.

    Raises:
        ValueError: If no station records can be parsed.
    """
    rows = {}
    for line in body.splitlines():
        if line.startswith("#") or "|" not in line:
            continue
        fields = line.split("|", 9)
        if len(fields) != 10:
            continue
        # NOAA supplies ten fields; the unused deployment fields are not exported.
        station, owner, kind, _, name, _, location, _, _, notes = fields
        station = station.strip().lower()
        if not re.fullmatch(r"[a-z0-9]+", station):
            continue
        match = LOCATION.search(location)
        latitude = longitude = np.nan
        if match:
            lat, ns, lon, ew = match.groups()
            latitude = float(lat) * (1 if ns == "N" else -1)
            longitude = float(lon) * (1 if ew == "E" else -1)
        rows[station] = (
            _plain_text(name),
            _plain_text(owner),
            _plain_text(kind),
            _plain_text(notes),
            latitude,
            longitude,
        )
    if not rows:
        raise ValueError("NOAA station table contains no recognizable station records")
    ids = sorted(rows)
    names = ["name", "owner", "station_type", "notes", "latitude", "longitude"]
    dataset = xr.Dataset(
        {
            name: ("station_id", [rows[s][i] for s in ids])
            for i, name in enumerate(names)
        },
        coords={"station_id": ids},
    )
    dataset.latitude.attrs.update(long_name="Station latitude", units="degrees_north")
    dataset.longitude.attrs.update(long_name="Station longitude", units="degrees_east")
    return dataset.set_coords(["latitude", "longitude"])

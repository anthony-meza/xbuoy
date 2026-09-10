"""Download NOAA text, including gzip-compressed archive files."""

import gzip
from urllib.request import urlopen

# Bound each NOAA request so an unresponsive server cannot stall retrieval forever.
REQUEST_TIMEOUT_SECONDS = 30


def read_noaa_text(url: str) -> str:
    """Download and decode a NOAA UTF-8 file; archive .gz files are decompressed."""
    with urlopen(url, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        raw = response.read()
    if url.endswith(".gz"):
        raw = gzip.decompress(raw)
    return raw.decode("utf-8")

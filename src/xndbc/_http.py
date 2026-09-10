"""Download NOAA text, including gzip-compressed archive files."""

import gzip
from urllib.request import urlopen

# Bound each NOAA request so an unresponsive server cannot stall retrieval forever.
REQUEST_TIMEOUT_SECONDS = 30


def read_noaa_text(url: str) -> str:
    """Download NOAA text with a bounded request timeout.

    Args:
        url: NOAA file URL. A .gz suffix requests gzip decompression after retrieval.

    Returns:
        UTF-8 decoded text. Each call downloads the file without an observation cache.

    Raises:
        OSError: If the network request or gzip decompression fails.
        UnicodeDecodeError: If the response is not valid UTF-8.
    """
    with urlopen(url, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        raw = response.read()
    if url.endswith(".gz"):
        raw = gzip.decompress(raw)
    return raw.decode("utf-8")

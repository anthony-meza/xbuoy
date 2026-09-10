"""Small NOAA responses shared by API tests and notebook kernels."""

import re
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"


def read_fixture(url):
    """Route NOAA URLs to local text so the real parsers still run."""
    if url.endswith("station_table.txt"):
        return (FIXTURES / "stations.txt").read_text()
    if url.endswith("/"):
        if "/adcp/" in url:
            names = ["41051a2013.txt.gz"]
        elif "/swden/" in url:
            names = ["41018w1996.txt.gz"]
        else:
            names = [
                "44013h2020.txt.gz",
                "44013h2021.txt.gz",
                "41043h2020.txt.gz",
                "archiveh2020.txt.gz",
                "46254h1998.txt.gz",
                "46254h1999.txt.gz",
            ]
        return "".join(f'<a href="{name}">{name}</a>' for name in names)
    filename = "stdmet.txt"
    if "/adcp/" in url or url.endswith(".adcp"):
        filename = "adcp.txt"
    elif "/swden/" in url or url.endswith(".data_spec"):
        filename = "spectral.txt"
    body = (FIXTURES / filename).read_text()
    year = re.search(r"[a-z](\d{4})\.txt\.gz$", url)
    if year and filename != "spectral.txt":
        body = body.replace("2020", year.group(1))
    if "realtime2/46254" in url:
        lines = body.splitlines()
        wind_column = lines[0].split().index("WSPD")
        for index, line in enumerate(lines):
            if not line.startswith("#"):
                values = line.split()
                values[wind_column] = "MM"
                lines[index] = " ".join(values)
        body = "\n".join(lines)
    return body


def configure_notebook():
    """Use the same offline downloads and suppress coastline downloads in a kernel."""
    from xndbc import _catalog, _http
    import cartopy.mpl.geoaxes

    _catalog._station_catalog.cache_clear()
    _catalog.historical_file_index.cache_clear()
    _http.read_noaa_text = read_fixture
    cartopy.mpl.geoaxes.GeoAxes.coastlines = lambda *args, **kwargs: None
    cartopy.mpl.geoaxes.GeoAxes.add_feature = lambda *args, **kwargs: None

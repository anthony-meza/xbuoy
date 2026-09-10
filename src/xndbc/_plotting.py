"""Station maps. Imports stay lazy to avoid loading plotting libraries until needed."""

import warnings

import numpy as np


def plot_station_map(dataset, variable=None, *, ax=None, labels="auto"):
    """Render station points without spatial interpolation.

    Args:
        dataset: Station or observation dataset with station_id and location coordinates.
        variable: Optional measurement containing one value per station.
        ax: Cartopy axes or None to create new axes.
        labels: Boolean or "auto" to label at most ten stations.

    Returns:
        A Matplotlib (figure, axes) pair. Missing values are gray; missing locations
        are omitted with a warning. Cartopy may download coastline resources.

    Raises:
        ValueError: If labels, coordinates, or measurement dimensions are invalid.
    """
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature
    import matplotlib.pyplot as plt

    if labels != "auto" and not isinstance(labels, bool):
        raise ValueError("labels must be True, False, or 'auto'")
    if "station_id" not in dataset.coords:
        raise ValueError("A station map requires a station_id coordinate")
    if "station_id" not in dataset.dims:
        dataset = dataset.expand_dims("station_id")
        for name in ("latitude", "longitude"):
            if name in dataset.coords and dataset[name].ndim == 0:
                dataset = dataset.assign_coords(
                    {name: ("station_id", [dataset[name].item()], dataset[name].attrs)}
                )
    for name in ("latitude", "longitude"):
        if name not in dataset.coords or dataset[name].dims != ("station_id",):
            raise ValueError(
                f"A station map requires {name} coordinates along station_id"
            )
    if variable is not None:
        if variable not in dataset:
            raise ValueError(
                f"Unknown variable {variable!r}; choose from {list(dataset.data_vars)}"
            )
        if dataset[variable].dims != ("station_id",):
            raise ValueError(
                "Map coloring needs one value per station. Select a time/depth/frequency or explicitly reduce those dimensions first."
            )
        if not np.issubdtype(dataset[variable].dtype, np.number):
            raise TypeError("Map coloring requires numeric values")
    located = np.isfinite(dataset.latitude.values) & np.isfinite(
        dataset.longitude.values
    )
    if (~located).any():
        warnings.warn(
            f"Omitted {int((~located).sum())} stations without locations",
            UserWarning,
            stacklevel=3,
        )
    dataset = dataset.isel(station_id=located)
    lon, lat = dataset.longitude.values, dataset.latitude.values
    center, extent = _map_extent(lon, lat)
    transform = ccrs.PlateCarree()
    if ax is None:
        fig, ax = plt.subplots(
            figsize=(9, 5),
            subplot_kw={"projection": ccrs.PlateCarree(central_longitude=center)},
        )
    else:
        if not hasattr(ax, "projection"):
            raise TypeError("ax must be a Cartopy GeoAxes")
        fig = ax.figure
    ax.add_feature(cfeature.LAND, facecolor="0.92")
    ax.coastlines(linewidth=0.6, color="0.45")
    grid = ax.gridlines(
        draw_labels=True, alpha=0.25, formatter_kwargs={"auto_hide": False}
    )
    grid.top_labels = grid.right_labels = False
    if not lon.size:
        ax.set_global()
        ax.text(
            0.5,
            0.5,
            "No stations with known locations",
            ha="center",
            transform=ax.transAxes,
        )
        return fig, ax
    if extent is None:
        ax.set_global()
    else:
        ax.set_extent(extent, crs=ccrs.PlateCarree(central_longitude=center))
    style = dict(
        s=38, edgecolors="white", linewidths=0.5, transform=transform, zorder=3
    )
    if variable is None:
        ax.scatter(lon, lat, color="tab:blue", **style)
    else:
        values = dataset[variable].values
        valid = np.isfinite(values)
        if valid.any():
            points = ax.scatter(
                lon[valid], lat[valid], c=values[valid], cmap="viridis", **style
            )
            attrs = dataset[variable].attrs
            label = attrs.get("long_name", variable)
            if attrs.get("units"):
                label += f" [{attrs['units']}]"
            fig.colorbar(points, ax=ax, label=label, shrink=0.8)
        if (~valid).any():
            ax.scatter(
                lon[~valid],
                lat[~valid],
                color="0.6",
                marker="x",
                label="No data",
                transform=transform,
                zorder=3,
            )
            ax.legend()
    # More than ten automatic labels tends to obscure nearby station markers.
    if labels is True or (labels == "auto" and lon.size <= 10):
        for station, x, y in zip(dataset.station_id.values, lon, lat):
            ax.annotate(
                str(station).upper(),
                (x, y),
                xycoords=transform._as_mpl_transform(ax),
                xytext=(4, 4),
                textcoords="offset points",
                fontsize=8,
            )
    return fig, ax


def _map_extent(lon, lat):
    """Find a compact map window, keeping nearby dateline stations together."""
    # Find the smallest longitude arc; nearby dateline stations stay nearby.
    center = 0.0
    if lon.size:
        ordered = np.sort(lon % 360)
        gaps = np.diff(np.r_[ordered, ordered[0] + 360])
        start = ordered[(int(gaps.argmax()) + 1) % len(ordered)]
        unwrapped = start + (lon - start) % 360
        center = float((unwrapped.min() + unwrapped.max()) / 2)
        center = (center + 180) % 360 - 180
    if not lon.size:
        return center, None
    offsets = (lon - center + 180) % 360 - 180
    # Pad by 8%, with at least one degree for single stations and small groups.
    padding = max(1.0, float(np.ptp(offsets)) * 0.08)
    latitude_padding = max(1.0, float(np.ptp(lat)) * 0.08)
    # Avoid projection singularities at the poles and the map seam.
    south = max(-89.9, float(lat.min()) - latitude_padding)
    north = min(89.9, float(lat.max()) + latitude_padding)
    # Nearly global station groups are clearer on a full-world map.
    if np.ptp(offsets) + 2 * padding >= 350:
        return center, None
    return center, [
        max(-179.9, float(offsets.min()) - padding),
        min(179.9, float(offsets.max()) + padding),
        south,
        north,
    ]

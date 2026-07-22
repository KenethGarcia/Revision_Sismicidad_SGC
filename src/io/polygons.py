# Author: Garcia-Cifuentes, K. <ORCID:0009-0001-2607-6359>

# --------------------------------------------------------------------------------------------------------
# This file contains functions to I/O polygons inside the package
# --------------------------------------------------------------------------------------------------------
from __future__ import annotations

import json
import shapely
import warnings
import numpy as np
from pathlib import Path
from shapely.geometry import Polygon
from shapely.geometry.base import BaseGeometry
from shapely.geometry import shape as shapely_shape


def load_polygons(
    polygon_entries: list[dict],
    base_dir: Path
):
    """
    Load, validate, and spatially prepare every polygon declared in the
    TOML [[polygons]] array.

    Parameters
    ----------
    polygon_entries : list[dict]
        Parsed contents of raw["polygons"] from the TOML file.
    base_dir : Path
        Directory of the TOML file, used to resolve relative polygon paths.

    Returns
    -------
    dict[str, shapely.geometry.Polygon]
        Mapping of polygon name → prepared Shapely Polygon.
        Polygons marked skip=true are excluded silently (with a warning).

    Raises
    ------
    ValueError        – duplicate polygon name detected.
    FileNotFoundError – a declared polygon path does not exist.
    ValueError        – an invalid polygon type is specified.
    """
    if not polygon_entries:
        warnings.warn(
            "No [[polygons]] entries found in the configuration. "
            "Spatial checks will not be available.",
            stacklevel=3,
        )
        return {}

    polygon_cache: dict[str, BaseGeometry] = {}
    seen_names: set[str] = set()

    for entry in polygon_entries:
        p_name = entry.get("name")
        p_path = entry.get("path")
        skip = entry.get("skip", False)
        p_type = entry.get("polygon_type")

        # ── Required key guards ────────────────────────────────────
        if not p_name:
            warnings.warn(
                "A [[polygons]] entry is missing the 'name' key and will be skipped.",
                stacklevel=3,
            )
            continue
        if not p_path:
            warnings.warn(
                f"Polygon {p_name!r} is missing the 'path' key and will be skipped.",
                stacklevel=3,
            )
            continue

        # ── Duplicate name guard ───────────────────────────────────
        if p_name in seen_names:
            raise ValueError(
                f"Duplicate polygon name {p_name!r} found in [[polygons]]. "
                "Each entry must have a unique 'name'."
            )
        seen_names.add(p_name)

        # ── Skip flag ──────────────────────────────────────────────
        if skip:
            warnings.warn(
                f"Polygon {p_name!r} is marked skip=true and will not be loaded.",
                stacklevel=3,
            )
            continue

        # ── Resolve path ───────────────────────────────────────────
        p_path = Path(p_path)
        if not p_path.is_absolute():
            p_path = (base_dir / p_path).resolve()

        if not p_path.exists():
            raise FileNotFoundError(
                f"Polygon file for {p_name!r} was not found: {p_path}\n"
                "Check the 'path' value in the [[polygons]] entry."
            )

        # ── Determine polygon type ─────────────────────────────────
        # Priority:
        # 1. Explicit polygon_type in the entry (case-insensitive)
        if p_type is not None:
            p_type_norm = str(p_type).upper()
        # 2. Inference from file extension (.txt/.csv -> BNA, .geojson/.json -> GeoJSON)
        else:
            suffix = p_path.suffix.lower()
            if suffix in {".txt", ".csv"}:
                p_type_norm = "BNA"
            elif suffix in {".geojson", ".json"}:
                p_type_norm = "GEOJSON"
        # 3. Fallback to BNA with a warning
            else:
                p_type_norm = "BNA"
                warnings.warn(
                    f"Polygon {p_name!r} has no 'polygon_type' and uses an "
                    f"unrecognized extension {suffix!r}. "
                    "Defaulting to BNA interpretation.",
                    stacklevel=3,
        )

        # ── Load polygon ───────────────────────────────────────────
        if p_type_norm == "BNA":
            polygon = _load_bna_polygon(p_path)
        elif p_type_norm == "GEOJSON":
            polygon = _load_geojson_polygon(p_path)
        else:
            raise ValueError(
                f"Unsupported polygon_type {p_type!r} for polygon {p_name!r}. "
                "Supported types are 'BNA' and 'GeoJSON'."
            )

        # Prepare (build spatial index once) and cache
        shapely.prepare(polygon)
        polygon_cache[p_name] = polygon

    return polygon_cache


def _load_bna_polygon(
        p_path: Path
) -> shapely.geometry.Polygon:
    """
    Load a polygon from a BNA-like text file with 'lon,lat' per line
    (header in the first line, optional comments starting with '#').

    Parameters
    ----------
    p_path : Path
        Path to BNA-like text file.

    Returns
    -------
    shapely.geometry.Polygon
        Prepared Shapely Polygon.
    """
    coords = np.loadtxt(
        str(p_path),
        delimiter=",",
        skiprows=1,
        comments="#",  # skip any line starting with # anywhere in the file
    )
    # Expect coords as [ [lon, lat], ... ]
    return Polygon(coords)


def _load_geojson_polygon(
        p_path: Path
) -> BaseGeometry:
    """
    Load a polygon (or multipolygon) from a GeoJSON file.

    Accepts:
    - A FeatureCollection with multiple features.
    - A single Feature.
    - A bare Geometry object.

    Parameters
    ----------
    p_path : Path
        Path to BNA-like text file.

    Returns
    -------
    shapely.geometry.Polygon
        Prepared Shapely Polygon.
    """
    text = p_path.read_text(encoding="utf-8")
    data = json.loads(text)

    # FeatureCollection
    if data.get("type") == "FeatureCollection":
        # union all polygon-like geometries into a single geometry
        geoms = [
            shapely_shape(feat["geometry"])
            for feat in data.get("features", [])
            if feat.get("geometry")
        ]
        if not geoms:
            raise ValueError(f"GeoJSON file {p_path} has no geometries.")
        geom = shapely.union_all(geoms)
    # Single Feature
    elif data.get("type") == "Feature" and "geometry" in data:
        geom = shapely_shape(data["geometry"])
    # Bare geometry
    else:
        geom = shapely_shape(data)

    return geom
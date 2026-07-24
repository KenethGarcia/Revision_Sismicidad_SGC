# Author: Garcia-Cifuentes, K. <ORCID:0009-0001-2607-6359>

# --------------------------------------------------------------------------------------------------------
# This file contains functions to test polygons.py I/O file
# --------------------------------------------------------------------------------------------------------
import json
import pytest
import shapely
import numpy as np
from pathlib import Path
from shapely.geometry import Polygon
from shapely.geometry.base import BaseGeometry

from src.io.polygons import (
    load_polygons,
    _load_bna_polygon,
    _load_geojson_polygon,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "src" / "data" / "polygons" / "SGC" / "RSNC"
BNA_FILE = DATA_DIR / "ptogaitan.txt"
GEOJSON_FILE = DATA_DIR / "ptogaitan.geojson"
@pytest.mark.skipif(not BNA_FILE.exists(), reason="ptogaitan.txt not found")
@pytest.mark.skipif(not GEOJSON_FILE.exists(), reason="ptogaitan.geojson not found")


def test_load_bna_polygon():
    """
    A single function to test the _load_bna_polygon function.
    It checks if the function correctly loads a BNA polygon file and returns a Shapely Polygon object.
    """
    poly = _load_bna_polygon(BNA_FILE)
    assert isinstance(poly, Polygon)
    assert poly.is_valid
    assert len(poly.exterior.coords) == 5  # At least 4 vertices + closing point

    # Check if first coordinate matches the file
    lon0, lat0 = poly.exterior.coords[0]
    assert isinstance(lon0, float)
    assert isinstance(lat0, float)


def test_load_geojson_polygon():
    """
    A single function to test the _load_geojson_polygon function.
    """
    poly = _load_geojson_polygon(GEOJSON_FILE)
    assert isinstance(poly, Polygon)
    assert poly.is_valid
    assert len(poly.exterior.coords) == 5

    lon0, lat0 = poly.exterior.coords[0]
    assert isinstance(lon0, float)
    assert isinstance(lat0, float)


def test_load_polygons_mixed_types():
    """
        Ensure load_polygons can load one BNA and one GeoJSON polygon
        from a mixed [[polygons]] configuration using real files.
    """
    base_dir = REPO_ROOT

    polygon_entries = [
        {
            "name": "zona_bna",
            "path": str(BNA_FILE.relative_to(base_dir)), # path relative to base_dir
            "polygon_type": "BNA",
            "description": "Puerto Gaitan Zone - BNA Format",
        },
        {
            "name": "zona_geo",
            "path": str(GEOJSON_FILE.relative_to(base_dir)),
            "polygon_type": "GeoJSON",
            "description": "Puerto Gaitan Zone - GeoJSON Format",
        },
    ]

    # Test case 1: Mixed files, but setting the polygon_type explicitly
    cache = load_polygons(polygon_entries, base_dir)
    assert set(cache.keys()) == {"zona_bna", "zona_geo"}
    z_bna = cache["zona_bna"]
    z_geo = cache["zona_geo"]
    assert isinstance(z_bna, BaseGeometry)
    assert isinstance(z_bna, Polygon)
    assert isinstance(z_geo, BaseGeometry)
    assert isinstance(z_geo, Polygon)
    # Prepared geometries
    assert shapely.is_prepared(z_bna)
    assert shapely.is_prepared(z_geo)
    # The polygons must be the same, since both polygons are equal but in different formats
    assert z_bna.equals(z_geo)


    # Test case 2: Mixed files, but without setting polygon_type
    # Drop the polygon_type key from previous polygon_entries
    polygon_entries[0].pop("polygon_type", None)
    polygon_entries[1].pop("polygon_type", None)
    cache2 = load_polygons(polygon_entries, base_dir)
    assert set(cache2.keys()) == {"zona_bna", "zona_geo"}
    z_bna = cache2["zona_bna"]
    z_geo = cache2["zona_geo"]
    assert isinstance(z_bna, BaseGeometry)
    assert isinstance(z_bna, Polygon)
    assert isinstance(z_geo, BaseGeometry)
    assert isinstance(z_geo, Polygon)
    assert shapely.is_prepared(z_bna)
    assert shapely.is_prepared(z_geo)
    assert z_bna.equals(z_geo)


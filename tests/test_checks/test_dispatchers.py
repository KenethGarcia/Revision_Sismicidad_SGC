# Author: Garcia-Cifuentes, K. <ORCID:0009-0001-2607-6359>

# --------------------------------------------------------------------------------------------------------
# This file contains dispatchers for handling seismic quality checks.
# --------------------------------------------------------------------------------------------------------
import numpy as np
import pandas as pd
import pytest
from shapely.geometry import Polygon

from src.checks.dispatchers import (
    dispatch_numeric,
    dispatch_non_numeric,
    dispatch_column_column,
    dispatch_polygon,
    dispatch_temporal,
    CONDITION_DISPATCHERS
)

def test_dispatch_numeric():
    """
    Test the dispatch_numeric function with a sample DataFrame and condition.
    """
    # Test case 1: Simple comparison using greater than
    subset = pd.DataFrame({"val": [0.0, 1.0, 2.0]})
    cond = {
        "column": "val",
        "mode": "gt",
        "threshold": 1.0,
    }
    mask = dispatch_numeric(subset, cond)
    assert mask.dtype == bool
    # values > 1.0 -> only the last element
    assert np.array_equal(mask, np.array([False, False, True]))

    # Test case 2: Greater equal
    cond["mode"] = "ge"
    mask = dispatch_numeric(subset, cond)
    assert mask.dtype == bool
    assert np.array_equal(mask, np.array([False, True, True]))

    # Test case 3: less than
    cond["mode"] = "lt"
    mask = dispatch_numeric(subset, cond)
    assert mask.dtype == bool
    assert np.array_equal(mask, np.array([True, False, False]))

    # Test case 4: less equal
    cond["mode"] = "le"
    mask = dispatch_numeric(subset, cond)
    assert mask.dtype == bool
    assert np.array_equal(mask, np.array([True, True, False]))

    # Test case 5: equal
    cond["mode"] = "eq"
    mask = dispatch_numeric(subset, cond)
    assert mask.dtype == bool
    assert np.array_equal(mask, np.array([False, True, False]))

    # Test case 6: not equal
    cond["mode"] = "ne"
    mask = dispatch_numeric(subset, cond)
    mask2 = dispatch_numeric(subset, cond)
    assert mask.dtype == bool
    assert np.array_equal(mask, np.array([True, False, True]))

    # Test case 7: between
    subset = pd.DataFrame({"val": [-1.0, 0.0, 1.0, 2.0]})
    cond = {
        "column": "val",
        "mode": "between",
        "lower": 0.0,
        "upper": 1.0,
    }
    mask = dispatch_numeric(subset, cond)
    assert np.array_equal(mask, np.array([False, True, True, False]))

    # Test case 8: outside
    cond["mode"] = "outside"
    mask = dispatch_numeric(subset, cond)
    assert mask.dtype == bool
    assert np.array_equal(mask, np.array([True, False, False, True]))

    # Test case 9: absolute value greater than
    cond["mode"] = "abs_gt"
    cond["threshold"] = 1.0
    mask = dispatch_numeric(subset, cond)
    assert mask.dtype == bool
    assert np.array_equal(mask, np.array([False, False, False, True]))

    # Test case 10: absolute value greater equal
    cond["mode"] = "abs_ge"
    mask = dispatch_numeric(subset, cond)
    assert mask.dtype == bool
    assert np.array_equal(mask, np.array([True, False, True, True]))


def test_dispatch_non_numeric():
    """
    Test the dispatch_non_numeric function with a sample DataFrame and condition.
    """
    subset = pd.DataFrame({"label": ["A", "B", "C"]})

    # Test case 1: in condition
    cond = {
        "column": "label",
        "mode": "in",
        "values": ["A", "C"],
    }
    mask = dispatch_non_numeric(subset, cond)
    assert mask.dtype == bool
    assert np.array_equal(mask, np.array([True, False, True]))

    # Test case 2: not in condition
    cond["mode"] = "not_in"
    mask = dispatch_non_numeric(subset, cond)
    assert mask.dtype == bool
    assert np.array_equal(mask, np.array([False, True, False]))

    # Test case 3: is null condition
    subset = pd.DataFrame({"label": ["A", None, "C"]})
    cond = {
        "column": "label",
        "mode": "is_null",
    }
    mask = dispatch_non_numeric(subset, cond)
    assert mask.dtype == bool
    assert np.array_equal(mask, np.array([False, True, False]))

    # Test case 4: is not null condition
    cond["mode"] = "not_null"
    mask = dispatch_non_numeric(subset, cond)
    assert mask.dtype == bool
    assert np.array_equal(mask, np.array([True, False, True]))

    # Test case 5: in condition with single value in values arg
    subset = pd.DataFrame({"label": ["DESTACADO", "OTHER"]})
    cond = {
        "column": "label",
        "mode": "in",
        "values": "DESTACADO",  # single string should be normalized to list
    }
    mask = dispatch_non_numeric(subset, cond)
    assert np.array_equal(mask, np.array([True, False]))

    # Test case 6: in condition with byte-strings
    subset = pd.DataFrame({"label": [b"DESTACADO", "OTHER"]})
    mask = dispatch_non_numeric(subset, cond)
    assert mask.dtype == bool
    assert np.array_equal(mask, np.array([True, False]))

    # Test case 7: in condition with single value in valur arg
    cond = {
        "column": "label",
        "mode": "in",
        "value": "DESTACADO",  # single string should be normalized to list
    }
    mask = dispatch_non_numeric(subset, cond)
    assert mask.dtype == bool
    assert np.array_equal(mask, np.array([True, False]))

    # Test case 8: not in condition with multiple values in value arg
    subset = pd.DataFrame({"label": ["A", "B", "C"]})
    cond = {
        "column": "label",
        "mode": "not_in",
        "value": ["A", "C"],  # list under 'value' must be handled
    }
    mask = dispatch_non_numeric(subset, cond)
    assert np.array_equal(mask, np.array([False, True, False]))


def test_dispatch_temporal():
    """
    Test the dispatch_temporal function with a sample DataFrame and condition.
    """
    # Test case 1: greater equal
    subset = pd.DataFrame(
        {"t": ["2024-01-01 00:00:00", "2024-01-02 00:00:00", "2024-01-03 00:00:00"]}
    )
    cond = {
        "column": "t",
        "mode": "ge",
        "value": "2024-01-02 00:00:00",
    }
    mask = dispatch_temporal(subset, cond)
    assert mask.dtype == bool
    assert np.array_equal(mask, np.array([False, True, True]))

    # Test case 2: greater than
    cond["mode"] = "gt"
    mask = dispatch_temporal(subset, cond)
    assert mask.dtype == bool
    assert np.array_equal(mask, np.array([False, False, True]))

    # Test case 3: less equal
    cond["mode"] = "le"
    mask = dispatch_temporal(subset, cond)
    assert mask.dtype == bool
    assert np.array_equal(mask, np.array([True, True, False]))

    # Test case 4: less than
    cond["mode"] = "lt"
    mask = dispatch_temporal(subset, cond)
    assert mask.dtype == bool
    assert np.array_equal(mask, np.array([True, False, False]))

    # Test case 5: equal (changing format)
    cond["mode"] = "eq"
    cond["value"] = "2024-01-02T00:00:00"
    mask = dispatch_temporal(subset, cond)
    assert mask.dtype == bool
    assert np.array_equal(mask, np.array([False, True, False]))

    # Test case 6: not equal
    cond["mode"] = "ne"
    mask = dispatch_temporal(subset, cond)
    assert mask.dtype == bool
    assert np.array_equal(mask, np.array([True, False, True]))

    # Test case 7: Different valid time formats on left column
    right_formats = [
        "2024-01-01",
        "2024-01-01 00:00:00",
        "2024-01-01T00:00:00",
        "2024-01-01 00:00:00.000",
        "2024/01/01",
        "20240101",
        "2024-01-01 00:00:00+00:00",
        "2024-01-01T00:00:00Z",
    ]
    subset = pd.DataFrame(
        {"t": right_formats
         })
    cond["mode"] = "eq"
    cond["value"] = "2024-01-01 00:00:00"
    mask = dispatch_temporal(subset, cond)
    assert mask.dtype == bool
    assert mask.all()  # All should be True since all formats represent the same time

    # Test case 8: Different valid time formats on right column
    # Loop over subset and change dynamically the cond["value"] to match each row,
    # and check that the comparison always is true
    for value in right_formats:
        cond["value"] = value
        mask = dispatch_temporal(subset, cond)
        assert mask.dtype == bool
        assert mask.all()


def test_dispatch_polygon():
    """
    Test the dispatch_polygon function with a sample DataFrame and condition.
    """
    # Test case 1: Inside
    square = Polygon([(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)])
    polygons = {"zone1": square}
    subset = pd.DataFrame({"lon": [0.5, 1.5], "lat": [0.5, 0.5]})

    cond = {
        "lat_col": "lat",
        "lon_col": "lon",
        "mode": "inside",
        "polygon": "zone1",  # bare string
    }
    mask = dispatch_polygon(subset, cond, polygons)
    assert np.array_equal(mask, np.array([True, False]))

    # Test case 2: Outside with multiple polygons/points
    poly2 = Polygon([(1.0, 0.0), (2.0, 0.0), (2.0, 1.0), (1.0, 1.0)])
    polygons = {"zone1": square, "zone2": poly2}

    subset = pd.DataFrame(
        {"lon": [0.5, 1.5, 2.5], "lat": [0.5, 0.5, 0.5],}
    )

    cond = {
        "lat_col": "lat",
        "lon_col": "lon",
        "mode": "outside",
        "polygon": ["zone1", "zone2"],  # list of names
    }

    mask = dispatch_polygon(subset, cond, polygons)
    # first point inside zone1, second inside zone2, third outside both
    assert np.array_equal(mask, np.array([False, False, True]))

    # Test case 3: KeyError raises when missing polygon
    subset = pd.DataFrame({"lon": [0.5], "lat": [0.5]})
    cond = {
        "lat_col": "lat",
        "lon_col": "lon",
        "mode": "inside",
        "polygon": ["zone1", "zoneX"],  # zoneX missing
    }
    with pytest.raises(KeyError):
        dispatch_polygon(subset, cond, polygons)

    # Test case 4: ValueError raises when empty polygon list
    cond = {
        "lat_col": "lat",
        "lon_col": "lon",
        "mode": "inside",
        "polygon": [],  # empty
    }

    with pytest.raises(ValueError):
        dispatch_polygon(subset, cond, polygons)

    # Test case 5: TypeError raises when polygon is not a shapely Polygon or a list of shapely Polygons
    cond = {
        "lat_col": "lat",
        "lon_col": "lon",
        "mode": "inside",
        "polygon": 123,  # not str or list
    }
    with pytest.raises(TypeError):
        dispatch_polygon(subset, cond, polygons)


def test_dispatch_column_column():
    """
    Test the dispatch_column_column function with a sample DataFrame and condition.
    """
    # Test case 1: Loop over each possible case
    subset = pd.DataFrame({"a": [1.0, 3.0, 5.0], "b": [1.0, 1.0, 1.0]})
    cond = {
        "left_col": "a",
        "right_col": "b",
        "mode": "gt"
    }
    options = ("gt", "ge", "lt", "le", "eq", "ne")
    solutions = (  # a <mode> b
        [False, True, True],  # gt
        [True, True, True],  # ge
        [False, False, False],  # lt
        [True, False, False],  # le
        [True, False, False],  # eq
        [False, True, True]   # ne
    )
    for i in range(len(options)):
        cond["mode"] = options[i]
        mask = dispatch_column_column(subset, cond)
        assert mask.dtype == bool
        assert np.array_equal(mask, np.array(solutions[i]))

    # Test case 2: Testing offset and factor
    cond = {
        "left_col": "a",
        "right_col": "b",
        "mode": "gt",
        "factor": 2.0,
        "offset": 0.0,
    }
    mask = dispatch_column_column(subset, cond)
    # compare a > 2 * b: [1 > 2, 3 > 2, 5 > 2]
    assert np.array_equal(mask, np.array([False, True, True]))


def test_condition_dispatchers():
    """
    Test the condition_dispatchers function with examples
    """
    # Test case 1: Check that all expected keys are present
    expected_keys = {
        "numeric",
        "category",
        "column_column",
        "polygon",
        "temporal",
    }
    assert set(CONDITION_DISPATCHERS.keys()) == expected_keys

    # Test case 2: Check that each dispatcher is callable
    for key, dispatcher in CONDITION_DISPATCHERS.items():
        assert callable(dispatcher)

    # Test case 3: Check if the functions are correctly correlated
    assert CONDITION_DISPATCHERS["numeric"] is dispatch_numeric
    assert CONDITION_DISPATCHERS["category"] is dispatch_non_numeric
    assert CONDITION_DISPATCHERS["column_column"] is dispatch_column_column
    assert CONDITION_DISPATCHERS["polygon"] is dispatch_polygon
    assert CONDITION_DISPATCHERS["temporal"] is dispatch_temporal
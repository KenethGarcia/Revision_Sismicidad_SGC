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
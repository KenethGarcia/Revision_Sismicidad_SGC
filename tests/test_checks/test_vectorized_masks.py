# Author: Garcia-Cifuentes, K. <ORCID:0009-0001-2607-6359>

# --------------------------------------------------------------------------------------------------------
# This file contains tests for the vectorized_masks.py functions.
# --------------------------------------------------------------------------------------------------------
import pytest
import numpy as np
import pandas as pd
from shapely.geometry import Polygon
from src.checks.vectorized_masks import (
    numeric_mask,
    column_column_mask,
    non_numeric_mask,
    polygon_mask,
    temporal_mask,
    combine_masks
)

def test_numeric_mask():
    """
    Test the numeric_mask function with various modes and thresholds.
    """
    df = pd.DataFrame({'x': [0.0, 1.0, 2.0, -2.0]})

    # Test greater than comparison
    gt_mask = numeric_mask(df, "x", mode="gt", threshold=1.0)
    assert gt_mask.dtype == bool
    assert np.array_equal(gt_mask, np.array([False, False, True, False]))

    # Test greater equal comparison
    ge_mask = numeric_mask(df, "x", mode="ge", threshold=1.0)
    assert np.array_equal(ge_mask, np.array([False, True, True, False]))

    # Test less than comparison
    lt_mask = numeric_mask(df, "x", mode="lt", threshold=0.0)
    assert np.array_equal(lt_mask, np.array([False, False, False, True]))

    # Test less equal comparison
    le_mask = numeric_mask(df, "x", mode="le", threshold=0.0)
    assert np.array_equal(le_mask, np.array([True, False, False, True]))

    # Test equal comparison
    eq_mask = numeric_mask(df, "x", mode="eq", threshold=1.0)
    assert np.array_equal(eq_mask, np.array([False, True, False, False]))

    # Test not equal comparison
    ne_mask = numeric_mask(df, "x", mode="ne", threshold=1.0)
    assert np.array_equal(ne_mask, np.array([True, False, True, True]))
    df = pd.DataFrame({"x": [-3.0, -1.0, 0.0, 1.0, 3.0]})

    # Test between comparison
    between_mask = numeric_mask(df, "x", mode="between", lower=-1.0, upper=1.0)
    assert np.array_equal(between_mask, np.array([False, True, True, True, False]))

    # Test outside comparison
    outside_mask = numeric_mask(df, "x", mode="outside", lower=-1.0, upper=1.0)
    assert np.array_equal(outside_mask, np.array([True, False, False, False, True]))

    # Test absolute greater than comparison
    abs_gt_mask = numeric_mask(df, "x", mode="abs_gt", threshold=2.0)
    assert np.array_equal(abs_gt_mask, np.array([True, False, False, False, True]))

    # Test absolute greater equal comparison
    abs_ge_mask = numeric_mask(df, "x", mode="abs_ge", threshold=3.0)
    assert np.array_equal(abs_ge_mask, np.array([True, False, False, False, True]))

    # Test unsupported mode
    with pytest.raises(ValueError):
        numeric_mask(df, "x", mode="unsupported_mode", threshold=1.0)


def test_column_column_mask():
    """
    Test the column_column_mask function with various modes and thresholds.
    """
    df = pd.DataFrame({"a": [1.0, 2.0, 3.0], "b": [0.5, 2.0, 5.0]})

    # Test a > b
    gt_mask = column_column_mask(df, "a", mode="gt", right_col="b")
    assert np.array_equal(gt_mask, np.array([True, False, False]))

    # Test a >= b
    ge_mask = column_column_mask(df, "a", mode="ge", right_col="b")
    assert np.array_equal(ge_mask, np.array([True, True, False]))

    # Test a < b
    lt_mask = column_column_mask(df, "a", mode="lt", right_col="b")
    assert np.array_equal(lt_mask, np.array([False, False, True]))

    # Test a <= b
    le_mask = column_column_mask(df, "a", mode="le", right_col="b")
    assert np.array_equal(le_mask, np.array([False, True, True]))

    # Test a == b
    eq_mask = column_column_mask(df, "a", mode="eq", right_col="b")
    assert np.array_equal(eq_mask, np.array([False, True, False]))

    # Test a != b
    ne_mask = column_column_mask(df, "a", mode="ne", right_col="b")
    assert np.array_equal(ne_mask, np.array([True, False, True]))

    # Test factor (a > 2b)
    gt_2b_mask = column_column_mask(df, "a", mode="gt", right_col="b", factor=2.0)
    assert np.array_equal(gt_2b_mask, np.array([False, False, False]))

    # Test offset (a > b + 0.1)
    gt_b_plus_1 = column_column_mask(df, "a", mode="lt", right_col="b", offset=0.1)
    assert np.array_equal(gt_b_plus_1, np.array([False, True, True]))

    # Test unsupported mode
    with pytest.raises(KeyError):
        column_column_mask(df, "a", mode="unsupported_mode", right_col="b")


def test_non_numeric_mask():
    df = pd.DataFrame({"label": ["A", None, "B", pd.NA]})

    # Test null values
    is_null = non_numeric_mask(df, "label", mode="is_null")
    assert np.array_equal(is_null, np.array([False, True, False, True]))

    not_null = non_numeric_mask(df, "label", mode="not_null")
    assert np.array_equal(not_null, ~is_null)

    # Test in/not in normal and byte-strings
    df = pd.DataFrame(
        {"label": ["DESTACADO", b"DESTACADO", bytearray(b"OTHER"), "OTHER"]}
    )
    values = ["DESTACADO"]

    in_mask = non_numeric_mask(df, "label", mode="in", values=values)
    assert np.array_equal(in_mask, np.array([True, True, False, False]))

    not_in_mask = non_numeric_mask(df, "label", mode="not_in", values=values)
    assert np.array_equal(not_in_mask, np.array([False, False, True, True]))

    with pytest.raises(ValueError):
        non_numeric_mask(df, "label", mode="unsupported_mode")


if __name__ == "__main__":
    pytest.main()
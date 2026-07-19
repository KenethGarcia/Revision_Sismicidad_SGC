# Author: Garcia-Cifuentes, K. <ORCID:0009-0001-2607-6359>

# --------------------------------------------------------------------------------------------------------
# This file contains dispatchers for handling seismic quality checks.
# --------------------------------------------------------------------------------------------------------
from __future__ import annotations
from typing import Dict
from shapely.geometry import Polygon
import numpy as np
import pandas as pd

from .vectorized_masks import (
    numeric_mask,
    column_column_mask,
    non_numeric_mask,
    polygon_mask,
    temporal_mask,
    combine_masks
)


def dispatch_numeric(
        subset: pd.DataFrame,
        cond: dict,
        polygons: dict | None = None
) -> np.ndarray:
    """
    Dispatcher for numeric ruletype.

    Expects cond to contain:
    - 'column' (str)
    - 'mode'   (str)
    - optional 'threshold' (float)
    - optional 'lower', 'upper' (float)

    Example TOML:
    checks.conditions
      ruletype = "numeric"
      column   = "qualitystandardError"
      mode     = "gt"
      threshold = 1.5
    """
    return numeric_mask(
        events=subset,
        column=cond['column'],
        mode=cond['mode'],
        threshold=cond.get('threshold'),
        lower=cond.get('lower'),
        upper=cond.get('upper')
    )


def dispatch_non_numeric(
        subset: pd.DataFrame,
        cond: dict,
        polygons: dict | None = None
) -> np.ndarray:
    """
    Dispatcher for non-numeric (categoric) ruletype.

    Expects cond to contain:
    - 'column' (str)
    - 'mode'   (str): 'is_null', 'not_null', 'in', 'not_in'
    - optional 'values' or 'value'

    Example TOML:
    checks.conditions
      rule_type = "category"
      column = "event_type"
      mode = "not_in"
      values = ["earthquake", "outside of network interest"]

    TOML flexibility:
    - values = "DESTACADO"
    - values = ["DESTACADO", "OTHER"]
    - value  = "DESTACADO"  (single)
    """
    values = cond.get('values')
    if isinstance(values, str):
        values = [values]
    elif values is None and "value" in cond:
        raw_value = cond["value"]
        values = raw_value if isinstance(raw_value, list) else [raw_value]

    return non_numeric_mask(
        events=subset,
        column=cond["column"],
        mode=cond["mode"],
        values=values,
    )


def dispatch_temporal(
        subset: pd.DataFrame,
        cond: dict,
        polygons: dict | None = None
) -> np.ndarray:
    """
    Dispatcher for temporal ruletype.

    Expects cond to contain:
    - 'column' (str)
    - 'mode'   (str): gt, ge, lt, le, eq, ne
    - 'value'  (str): any pandas.Timestamp-friendly string

    Example TOML:
    checks.conditions
      rule_type = "temporal"
      column = "time_value"
      mode = "ge"
      value = "2026-03-17T00:00:00Z"
    """
    return temporal_mask(
        events=subset,
        column=cond['column'],
        mode=cond['mode'],
        value=cond['value']
    )


def dispatch_polygon(
        subset: pd.DataFrame,
        cond: dict,
        polygons: Dict[str, Polygon],
) -> np.ndarray:
    """
    Dispatcher for polygon ruletype.

    Expects cond to contain:
    - 'lat_col'   (str)
    - 'lon_col'   (str)
    - 'mode'     (str): 'inside' or 'outside'
    - 'polygon'  (str | list[str]): one or more polygon names
      that must exist in the polygon cache.

    Semantics:
    - mode == 'inside':
        Event is flagged if it is inside ANY of the listed polygons
    - mode == 'outside':
        Event is flagged if it is outside ALL the listed polygons

    Example TOML:
    checks.conditions
      rule_type = "polygon"
      lat_col = "latitude_value"
      lon_col = "longitude_value"
      mode = "inside"
      polygon = "local_area"

    Raises
    ------
    KeyError
        If any of the listed polygon names are not found in the polygon cache.
    ValueError
        If the 'polygon' list is empty.
    TypeError
        If the 'polygon' value is neither a string nor a list of strings.
    """
    polygon_names = cond["polygon"]

    # Normalize: allow both a bare string (legacy) and a list
    if isinstance(polygon_names, str):
        polygon_names = [polygon_names]
    elif not isinstance(polygon_names, list):
        raise TypeError(
            f"'polygon' must be a string or a list of strings, "
            f"got {type(polygon_names).__name__}"
        )

    if not polygon_names:
        raise ValueError("'polygon' list must contain at least one polygon name")

    missing = [p for p in polygon_names if p not in polygons]
    if missing:
        raise KeyError(
            f"Polygon(s) {missing} referenced in a condition were not found "
            f"in the loaded polygon cache. Available: {list(polygons.keys())}"
        )

    mode = cond["mode"]

    per_polygon_masks = [
        polygon_mask(
            events=subset,
            lon_col=cond["lon_col"],
            lat_col=cond["lat_col"],
            polygon=polygons[name],
            mode=mode,
        )
        for name in polygon_names
    ]

    # Single-polygon shortcut — skip combine_masks entirely
    if len(per_polygon_masks) == 1:
        return per_polygon_masks[0]

    # mode == "inside"  -> event flagged if inside ANY of the listed polygons  (OR)
    # mode == "outside" -> event flagged if outside ALL the listed polygons (AND)
    union_logic = "or" if mode == "inside" else "and"
    return combine_masks(per_polygon_masks, logic=union_logic)


def dispatch_column_column(subset: pd.DataFrame, cond: dict, polygons: dict | None = None) -> np.ndarray:
    """
    Dispatcher for column-column ruletype.

    Expects cond to contain:
    - 'left_col'  (str)
    - 'right_col' (str)
    - 'mode'     (str): gt, ge, lt, le, eq, ne
    - optional 'factor' (float, default=1.0)
    - optional 'offset' (float, default=0.0)

    Follows the formula:
        subset[left_col] (op) factor * subset[right_col] + offset

    Example TOML:
    checks.conditions
      rule_type = "column_column"
      left_col = "column_a"
      right_col = "column_b"
      mode = "gt"
      factor = 1.0
      offset = 0.0
    """
    return column_column_mask(
        events=subset,
        left_col=cond["left_col"],
        mode=cond["mode"],
        right_col=cond["right_col"],
        factor=cond.get("factor", 1.0),
        offset=cond.get("offset", 0.0),
    )


CONDITION_DISPATCHERS = {
    "numeric": dispatch_numeric,
    "category": dispatch_non_numeric,
    "temporal": dispatch_temporal,
    "polygon": dispatch_polygon,
    "column_column": dispatch_column_column,
}
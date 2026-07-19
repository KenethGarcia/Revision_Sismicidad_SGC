# Author: Garcia-Cifuentes, K. <ORCID:0009-0001-2607-6359>

# --------------------------------------------------------------------------------------------------------
# This file contains functions to create vectorized masks for different types based on usual requirements.
# --------------------------------------------------------------------------------------------------------
import shapely
import numpy as np
import pandas as pd
from shapely.geometry import Polygon
from shapely.geometry.base import BaseGeometry


def numeric_mask(
    events: pd.DataFrame,
    column: str,
    mode: str,
    threshold : float | None= None,
    lower: float | None = None,
    upper: float | None = None,
    dtype = np.float64
) -> np.ndarray:
    """
    Vectorized numeric comparator for seismic quality checks.

    Parameters
    ----------
    events : pd.DataFrame
        Input seismic dataframe.
    column : str
        Column to evaluate.
    mode : str
        Comparison mode:
            'gt'       -> values > threshold
            'ge'       -> values >= threshold
            'lt'       -> values < threshold
            'le'       -> values <= threshold
            'eq'       -> values == threshold
            'ne'       -> values != threshold
            'between'  -> lower <= values <= upper
            'outside'  -> values < lower or values > upper
            'abs_gt'   -> abs(values) > threshold
            'abs_ge'   -> abs(values) >= threshold
    threshold : float, optional
        Threshold for one-sided and equality comparisons.
    lower, upper : float, optional
        Bounds for range comparisons.
    dtype : numpy dtype
        Target dtype for NumPy conversion.

    Returns
    -------
    np.ndarray
        Boolean mask of flagged rows.

    Raises
    -------
    ValueError
        If an unsupported mode is provided.
    """
    values = events[column].to_numpy(dtype=dtype, copy=False)

    if mode == 'gt':
        return values > threshold
    elif mode == 'ge':
        return values >= threshold
    elif mode == 'lt':
        return values < threshold
    elif mode == 'le':
        return values <= threshold
    elif mode == 'eq':
        return values == threshold
    elif mode == 'ne':
        return values != threshold
    elif mode == 'between':
        return (values >= lower) & (values <= upper)
    elif mode == 'outside':
        return (values < lower) | (values > upper)
    elif mode == 'abs_gt':
        return np.abs(values) > threshold
    elif mode == 'abs_ge':
        return np.abs(values) >= threshold
    else:
        raise ValueError(f"Unsupported mode: {mode!r}")


def column_column_mask(
    events: pd.DataFrame,
    left_col: str,
    mode: str,
    right_col: str,
    offset: float = 0.0,
    factor: float = 1.0,
    dtype=np.float64,
) -> np.ndarray:
    """
    Vectorized column to column comparator for seismic quality checks.
    It follows the formulae: events[left_col] <<mode>> factor * events[right_col] + offset

    Parameters
    ----------
    events : pd.DataFrame
        Input seismic dataframe.
    left_col : str
        Left column to compare.
    mode : str
        Comparison mode:
            'gt'       -> values > threshold
            'ge'       -> values >= threshold
            'lt'       -> values < threshold
            'le'       -> values <= threshold
            'eq'       -> values == threshold
            'ne'       -> values != threshold
    right_col : str
        Right column to compare.
    offset : float, optional
        Offset of the equation, if required. Defaults to zero.
    factor : float, optional
        Multiplier for the right column, if required. Defaults to zero.
    dtype : numpy dtype
        Target dtype for NumPy conversion.

    Returns
    -------
    np.ndarray
        Boolean mask of flagged rows.
    """
    left = events[left_col].to_numpy(dtype=dtype, copy=False)
    right = events[right_col].to_numpy(dtype=dtype, copy=False) * factor + offset
    ops = {
        "gt": np.greater,
        "ge": np.greater_equal,
        "lt": np.less,
        "le": np.less_equal,
        "eq": np.equal,
        "ne": np.not_equal,
    }
    return ops[mode](left, right)


def _normalize_text_series(
        s: pd.Series
) -> pd.Series:
    """
    Coerce bytes/bytearray entries to str (UTF-8 decoded). Used for a TOML string literal like 'DESTACADO' matches
    regardless of whether the source driver returned str or bytes for that row.

    Parameters
    ----------
    s : pd.Series
        Input series to normalize.

    Returns
    ----------
    pd.Series
        Normalized series.
    """
    def _to_str(v):
        if isinstance(v, (bytes, bytearray)):
            return v.decode("utf-8", errors="replace")
        return v
    return s.map(_to_str)


def non_numeric_mask(
    events: pd.DataFrame,
    column: str,
    mode: str,
    values: list[str] | None = None,
) -> np.ndarray:
    """
    Vectorized non-numeric comparator for seismic quality checks.

    Parameters
    ----------
    events : pd.DataFrame
        Input seismic dataframe.
    column : str
        Column to evaluate.
    mode : str
        Comparison mode:
            'is_null'       -> values that are null/NaN
            'not_null'      -> values that are not null/NaN
            'in'            -> values that are in the provided list
            'not_in'        -> values that are not in the provided list
    values : list[str], optional
        List of values for 'in' or 'not_in' modes.

    Returns
    -------
    np.ndarray
        Boolean mask of flagged rows.

    Raises
    -------
    ValueError
        If an unsupported mode is provided.
    """
    s = _normalize_text_series(events[column])
    if mode == "is_null":
        return s.isna().to_numpy()
    elif mode == "not_null":
        return s.notna().to_numpy()
    elif mode == "in":
        return s.isin(values).to_numpy()
    elif mode == "not_in":
        return (~s.isin(values)).to_numpy()
    else:
        raise ValueError(f"Unsupported category mode: {mode!r}")


def polygon_mask(
    events: pd.DataFrame,
    lon_col: str,
    lat_col: str,
    polygon: Polygon | BaseGeometry,
    mode : str = "inside"
) -> np.ndarray:
    """
    Vectorized polygon comparator for seismic quality checks.

    Parameters
    ----------
    events : pd.DataFrame
        Input seismic dataframe.
    lon_col : str
        Longitude column to evaluate.
    lat_col : str
        Latitude column to evaluate.
    polygon : shapely.geometry.Polygon or shapely.geometry.base.BaseGeometry
        Shapely polygon to compare.
    mode : str
        Comparison mode:
            'inside'       -> values inside polygon
            'outside'      -> values outside polygon

    Returns
    -------
    np.ndarray
        Boolean mask of flagged rows.

    Raises
    -------
    ValueError
        If an unsupported mode is provided.
    """
    if mode not in ['inside', 'outside']:
        raise ValueError(f"Unsupported polygon mode: {mode}. Accepted modes: 'inside' and 'outside'")
    if not shapely.is_prepared(polygon):
        shapely.prepare(polygon)
    inside = shapely.contains_xy(
        polygon,
        events[lon_col].to_numpy(),
        events[lat_col].to_numpy()
    )
    return inside if mode == "inside" else ~inside


def temporal_mask(
    events: pd.DataFrame,
    column: str,
    mode: str,
    value: str,
) -> np.ndarray:
    """
    Vectorized temporal comparator for seismic quality checks.

    Parameters
    ----------
    events : pd.DataFrame
        Input seismic dataframe.
    column : str
        Column to evaluate.
    mode : str
        Comparison mode:
            'gt'       -> values > Timestamp
            'ge'       -> values >= Timestamp
            'lt'       -> values < Timestamp
            'le'       -> values <= Timestamp
            'eq'       -> values == Timestamp
            'ne'       -> values != Timestamp
    value : str
        Reference timestamp used for the comparison. Any string accepted by
        :class:`pandas.Timestamp` can be supplied, for example
        '2024-01-01T00:00:00Z' or '2024-01-01 00:00:00'.

    Returns
    -------
    numpy.ndarray
        Boolean mask with one entry per row in events. True indicates
        that the row satisfies the requested temporal condition.
    """
    left = pd.to_datetime(events[column], format="mixed", utc=True, errors="raise")
    right = pd.to_datetime(value, format="mixed", utc=True, errors="raise")

    ops = {
        "gt": np.greater,
        "ge": np.greater_equal,
        "lt": np.less,
        "le": np.less_equal,
        "eq": np.equal,
        "ne": np.not_equal,
    }
    return ops[mode](left.to_numpy(dtype="datetime64[ns]"), right.to_datetime64())


def combine_masks(
        masks: list[np.ndarray],
        logic: str
) -> np.ndarray:
    """
    Combine multiple boolean masks using a logical operator.

    Parameters
    ----------
    masks : list[np.ndarray]
        List of boolean masks to combine. All masks must have the same shape.
    logic : str
        Combination logic to apply:
            'and' -> logical AND across all masks
            'or'  -> logical OR across all masks
            'xor' -> logical XOR between exactly 2 masks

    Returns
    -------
    np.ndarray
        Boolean mask with one entry per element in the input masks.

    Raises
    ------
    ValueError
        If no masks are provided, if 'xor' is used with anything other than exactly 2 masks,
        or if an unsupported logic value is supplied.
    """
    if not masks:
        raise ValueError("No masks provided")
    if logic == "and":
        return np.logical_and.reduce(masks)
    elif logic == "or":
        return np.logical_or.reduce(masks)
    elif logic == "xor":
        if len(masks) != 2:
            raise ValueError("XOR logic requires exactly 2 masks")
        return np.logical_xor(masks[0], masks[1])
    else:
        raise ValueError(f"Unsupported logic: {logic!r}")
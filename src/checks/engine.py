# Author: Garcia-Cifuentes, K. <ORCID:0009-0001-2607-6359>
#
# --------------------------------------------------------------------------------------------------------
# This file contains functions to run engines directly from TOML checks and duplicates to code
# --------------------------------------------------------------------------------------------------------
from __future__ import annotations

import warnings
import numpy as np
import pandas as pd
from typing import Any

from src.checks.dispatchers import CONDITION_DISPATCHERS, combine_masks
from src.checks.duplicates import check_duplicates


def evaluate_node(
    subset: pd.DataFrame,
    node: dict,
    polygon_cache: dict[str, Any]
) -> np.ndarray:
    """
    Recursively evaluate a checks/groups node and return a boolean mask
    aligned to `subset`'s row order.

    A node is either:
      - A pure leaf list holder: has "conditions" (list of condition dicts)
        and/or "groups" (list of nested nodes).
      - If it has exactly ONE child total, "logic" is optional and ignored
        (there is nothing to combine).
      - If it has TWO OR MORE children total, "logic" is required.
      - Optionally negated via node.get("negate", False), regardless of
        child count.

    Parameters
    ----------
    subset : pd.DataFrame
        The subset of events to evaluate against the current node.
    node : dict
        The current checks/groups node to evaluate.
    polygon_cache : dict[str, shapely.geometry.Polygon]
        Dictionary mapping polygon names to Shapely Polygon objects. Usually returned by `load_config` under the 'polygons' key.

    Returns
    -----------
    pd.Index of the flagged events in the original DataFrame.

    Raises
    -----------
    ValueError
        If there are unsupported rule_type or if the node has no conditions or groups to evaluate.
    """
    child_masks: list[np.ndarray] = []

    # Direct leaf conditions
    for cond in node.get("conditions", []):
        ruletype = cond.get("rule_type")
        if ruletype not in CONDITION_DISPATCHERS:
            raise ValueError(
                f"Unsupported rule_type {ruletype!r} in condition {cond}. "
                f"Valid types: {list(CONDITION_DISPATCHERS.keys())}."
            )
        dispatcher = CONDITION_DISPATCHERS[ruletype]
        child_masks.append(dispatcher(subset, cond, polygon_cache))

    # Nested groups
    for group in node.get("groups", []):
        child_masks.append(evaluate_node(subset, group, polygon_cache))

    if not child_masks:
        raise ValueError(
            f"Node {node.get('name', node.get('description', 'unnamed'))!r} "
            "has no conditions or groups to evaluate."
        )

    # Single-child shortcut
    if len(child_masks) == 1:
        combined = child_masks[0]
        if "logic" in node:
            warnings.warn(
                f"Node {node.get('name', node.get('description', 'unnamed'))!r} "
                f"has a single condition but declares logic={node['logic']!r}. "
                "The logic key is ignored when there is only one child.",
                stacklevel=2,
            )
    else:
        if "logic" not in node:
            raise ValueError(
                f"Node {node.get('name', node.get('description', 'unnamed'))!r} "
                f"has {len(child_masks)} children but no 'logic' key. "
                "logic is required when combining 2 or more children."
            )
        combined = combine_masks(child_masks, logic=node["logic"])

    if node.get("negate", False):
        combined = ~combined

    return combined


def run_duplicates(
    events: pd.DataFrame,
    duplicates_cfg: list[dict],
) -> pd.DataFrame:
    """
    Execute every [[duplicates]] entry and return merged duplicate rows with Observations column.

    Parameters
    ---------------
    events : pd.DataFrame
        Input seismic Dataframe.
    duplicates_cfg : list[dict]
        List of [[duplicates]] entries from the TOML configuration.
    """
    if not duplicates_cfg:
        return events.iloc[0:0].copy()

    obsmap: dict[Any, list[str]] = {}

    for dup in duplicates_cfg:
        name = dup.get("name", "<unnamed>")
        subset = dup.get("subset")  # e.g. ["Origin.time_value", "lat", "lon", "publicID"]
        method = dup.get("method", "adjacent")
        timewindow = dup.get("time_window", 4)
        distthreshold = dup.get("dist_threshold", 100.0)

        dup_rows = check_duplicates(
            events=events,
            subset=subset,
            method=method,
            time_window=timewindow,
            dist_threshold=distthreshold,
        )
        if dup_rows.empty:
            continue

        for idx, obs in zip(dup_rows.index, dup_rows["Observations"]):
            obsmap.setdefault(idx, []).append(f"{name}: {obs}")

    if not obsmap:
        return events.iloc[0:0].copy()

    flagged_positions = sorted(obsmap.keys())
    flagged = events.loc[flagged_positions].copy()
    flagged["Observations"] = ["; ".join(obsmap[i]) for i in flagged_positions]

    return flagged


def run_single_check(
    events: pd.DataFrame,
    check: dict,
    polygon_cache: dict[str, Any],
    event_type_col: str = "event_type"
) -> pd.Index:
    """
    Run a single check on the seismic events DataFrame

    Parameters
    ----------
    events : pd.DataFrame
        Input seismic events DataFrame.
    check : dict
        Dictionary containing the check configuration. Usually returned by `load_config` under the 'checks' key.
    polygon_cache : dict[str, shapely.geometry.Polygon]
        Dictionary mapping polygon names to Shapely Polygon objects. Usually returned by `load_config` under the 'polygons' key.
    event_type_col : str
        Name of the column in `events` that contains the event type. Defaults to "event_type".

    Returns
    -----------
    pd.Index
        Index of the flagged events in the original DataFrame.
    """
    # Filter by event_type at root node
    allowed_types = check.get("event_type")
    if allowed_types:
        if isinstance(allowed_types, str):
            allowed_types = [allowed_types]
        events = events[events[event_type_col].isin(allowed_types)]

    # If there are no events after filtering, return empty index
    if events.empty:
        return pd.Index([])

    mask = evaluate_node(events, check, polygon_cache)
    flagged = np.where(mask)[0]

    return events.index[flagged]


def run_checks(
    events: pd.DataFrame,
    checks: list[dict],
    polygon_cache: dict[str, Any],
    event_type_col: str = "event_type",
) -> pd.DataFrame:
    """
    Execute every [[checks]] entry declared in config["checks"] and return
    the flagged rows with an 'Observations' column listing which checks fired.

    Parameters
    ----------
    events : pd.DataFrame
        Full seismic event dataframe.
    checks: list[dict]
        List of [[checks]] entries from the TOML configuration.
    polygon_cache: dict[str, Any]
        Dictionary mapping polygon names to Shapely Polygon objects.
    event_type_col : str
        Column holding the event type string, used for root-level filtering.

    Returns
    -------
    pd.DataFrame
        Flagged rows with an added 'Observations' column.
    """
    if not checks:
        warnings.warn("No [[checks]] entries found in configuration.", stacklevel=2)
        return events.iloc[0:0].copy()

    # Map from index -> list of observation strings
    observations: dict[Any, list[str]] = {}

    for check in checks:
        name = check.get("name", "<unnamed>")
        try:
            flagged_idx = run_single_check(events, check, polygon_cache, event_type_col=event_type_col)
        except Exception as exc:
            warnings.warn(f"Check {name!r} raised an error and was skipped: {exc}", stacklevel=2)
            continue
        else:
            if flagged_idx.empty:
                continue
            for idx in flagged_idx:
                observations.setdefault(idx, []).append(name)

    if not observations:
        return events.iloc[0:0].copy()

    # Build flagged rows with Observations column
    flagged_positions = sorted(observations.keys())
    flagged = events.loc[flagged_positions].copy()
    flagged["Observations"] = ["; ".join(observations[i]) for i in flagged_positions]

    return flagged
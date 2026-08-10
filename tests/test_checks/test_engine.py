# Author: Garcia-Cifuentes, K. <ORCID:0009-0001-2607-6359>
#
# --------------------------------------------------------------------------------------------------------
# This file contains tests for engine.py
# --------------------------------------------------------------------------------------------------------
import pytest
import numpy as np
import pandas as pd
from typing import Any, Dict
from src.checks import engine
from src.checks.vectorized_masks import combine_masks

# Helpers for CONDITION_DISPATCHERS / combine_masks / check_duplicates

@pytest.fixture(autouse=True)
def patch_dispatchers(monkeypatch):
    """
    Patch CONDITION_DISPATCHERS and combine_masks in engine module to use simple, predictable behavior for tests.
    """
    # Simple dispatchers: each returns a mask based on a column and a rule_type
    def fake_numeric_dispatch(
            subset: pd.DataFrame,
            cond: Dict[str, Any],
            polygon_cache: Dict[str, Any]
    ) -> np.ndarray:
        """Fake numeric dispatcher: returns True where column > threshold (default 0.0)."""
        col = cond["column"]
        mode = cond.get("mode", "gt")
        thr = cond.get("threshold", 0.0)
        values = subset[col].to_numpy(dtype=float)
        if mode == "gt":
            return values > thr
        elif mode == "ge":
            return values >= thr
        elif mode == "lt":
            return values < thr
        elif mode == "le":
            return values <= thr
        else:
            raise ValueError(f"Unsupported mode {mode!r} in fake_numeric_dispatch")

    def fake_category_dispatch(
            subset: pd.DataFrame,
            cond: Dict[str, Any],
            polygon_cache: Dict[str, Any]
    ) -> np.ndarray:
        """Fake category dispatcher: returns True where column is in cond['values'] list."""
        col = cond["column"]
        values = cond.get("values", [])
        s = subset[col].astype(str)
        return s.isin(values).to_numpy()

    # Build fake CONDITION_DISPATCHERS mapping
    fake_condition_dispatchers = {
        "numeric": fake_numeric_dispatch,
        "category": fake_category_dispatch,
    }

    monkeypatch.setattr(engine, "CONDITION_DISPATCHERS", fake_condition_dispatchers)
    monkeypatch.setattr(engine, "combine_masks", combine_masks)


@pytest.fixture
def dummy_events() -> pd.DataFrame:
    """Small events DataFrame used in multiple tests."""
    return pd.DataFrame(
        {
            "event_type": ["earthquake", "explosion", "earthquake", "earthquake"],
            "quality_standardError": [0.2, 0.5, 0.8, 0.1],
            "comment": ["OK", "DESTACADO", "DESTACADO", "OK"],
        }
    )


@pytest.fixture
def dummy_polygon_cache() -> Dict[str, Any]:
    """For now, polygon_cache is unused by fake dispatchers."""
    return {}


# Tests for evaluate_node
def test_evaluate_node_single_condition_no_logic(dummy_events, dummy_polygon_cache):
    """
    evaluate_node with a single numeric condition and no logic should return the mask directly.
    """
    node = {
        "conditions": [
            {"rule_type": "numeric", "column": "quality_standardError", "mode": "gt", "threshold": 0.3}
        ]
    }
    mask = engine.evaluate_node(dummy_events, node, dummy_polygon_cache)
    # quality_standardError > 0.3 => rows 1 and 2
    assert mask.tolist() == [False, True, True, False]


def test_evaluate_node_multiple_conditions_with_and_logic(dummy_events, dummy_polygon_cache):
    """
    evaluate_node with two conditions and logic='and' should combine masks via logical AND.
    """
    node = {
        "logic": "and",
        "conditions": [
            {"rule_type": "numeric", "column": "quality_standardError", "mode": "gt", "threshold": 0.3},
            {"rule_type": "category", "column": "comment", "values": ["DESTACADO"]},
        ],
    }

    mask = engine.evaluate_node(dummy_events, node, dummy_polygon_cache)
    # numeric > 0.3 => rows 1, 2; comment == DESTACADO => rows 1, 2; AND => rows 1, 2
    assert mask.tolist() == [False, True, True, False]


def test_evaluate_node_nested_groups_or_logic(dummy_events, dummy_polygon_cache):
    """
    evaluate_node with a group node combining child masks using OR logic.
    """
    node = {
        "logic": "or",
        "conditions": [
            {"rule_type": "numeric", "column": "quality_standardError", "mode": "gt", "threshold": 0.7},
        ],
        "groups": [
            {
                "conditions": [
                    {"rule_type": "category", "column": "comment", "values": ["DESTACADO"]},
                ]
            }
        ],
    }

    mask = engine.evaluate_node(dummy_events, node, dummy_polygon_cache)
    # numeric > 0.7 => row 2; comment DESTACADO => rows 1, 2; OR => rows 1, 2
    assert mask.tolist() == [False, True, True, False]


def test_evaluate_node_negate(dummy_events, dummy_polygon_cache):
    """
    evaluate_node should apply negation when node['negate'] is True.
    """
    node = {
        "conditions": [
            {"rule_type": "numeric", "column": "quality_standardError", "mode": "gt", "threshold": 0.3},
        ],
        "negate": True,
    }

    mask = engine.evaluate_node(dummy_events, node, dummy_polygon_cache)
    # Base mask [False, True, True, False] => negated [True, False, False, True]
    assert mask.tolist() == [True, False, False, True]


def test_evaluate_node_unsupported_rule_type_raises(dummy_events, dummy_polygon_cache):
    """
    evaluate_node must raise ValueError when encountering an unknown rule_type.
    """
    node = {
        "conditions": [
            {"rule_type": "unknown_type", "column": "quality_standardError"},
        ]
    }

    with pytest.raises(ValueError) as excinfo:
        engine.evaluate_node(dummy_events, node, dummy_polygon_cache)

    assert "Unsupported rule_type" in str(excinfo.value)


def test_evaluate_node_no_children_raises(dummy_events, dummy_polygon_cache):
    """
    evaluate_node must raise ValueError when node has no conditions or groups.
    """
    node = {}

    with pytest.raises(ValueError) as excinfo:
        engine.evaluate_node(dummy_events, node, dummy_polygon_cache)

    assert "has no conditions or groups to evaluate" in str(excinfo.value)


def test_evaluate_node_missing_logic_with_multiple_children_raises(dummy_events, dummy_polygon_cache):
    """
    evaluate_node must raise ValueError when there are multiple child masks and no 'logic' key.
    """
    node = {
        "conditions": [
            {"rule_type": "numeric", "column": "quality_standardError", "mode": "gt", "threshold": 0.3},
            {"rule_type": "category", "column": "comment", "values": ["DESTACADO"]},
        ]
    }

    with pytest.raises(ValueError) as excinfo:
        engine.evaluate_node(dummy_events, node, dummy_polygon_cache)

    assert "has 2 children but no 'logic' key" in str(excinfo.value)


# Tests for run_single_check
def test_run_single_check_filters_by_event_type(dummy_events, dummy_polygon_cache):
    """
    run_single_check must filter events by event_type before evaluating the node.
    """
    check_cfg = {
        "name": "High RMS earthquakes only",
        "event_type": "earthquake",
        "conditions": [
            {"rule_type": "numeric", "column": "quality_standardError", "mode": "gt", "threshold": 0.3},
        ],
    }

    flagged_idx = engine.run_single_check(dummy_events, check_cfg, dummy_polygon_cache, event_type_col="event_type")

    # After filtering to earthquakes (rows 0, 2, 3), quality_standardError > 0.3 => row 2 only
    assert list(flagged_idx) == [2]


def test_run_single_check_no_events_after_filter_returns_empty(dummy_events, dummy_polygon_cache):
    """
    If filtering by event_type leaves no events, run_single_check must return an empty Index.
    """
    check_cfg = {
        "name": "Explosion only",
        "event_type": "explosion",
        "conditions": [
            {"rule_type": "numeric", "column": "quality_standardError", "mode": "gt", "threshold": 1.0},
        ],
    }

    flagged_idx = engine.run_single_check(dummy_events, check_cfg, dummy_polygon_cache, event_type_col="event_type")
    assert isinstance(flagged_idx, pd.Index)
    assert len(flagged_idx) == 0


# Tests for run_checks
def test_run_checks_no_checks_warns_and_returns_empty(dummy_events, dummy_polygon_cache, capsys):
    """
    When checks list is empty, run_checks should warn and return an empty DataFrame.
    """
    result = engine.run_checks(dummy_events, checks=[], polygon_cache=dummy_polygon_cache, event_type_col="event_type")
    assert isinstance(result, pd.DataFrame)
    assert result.empty


def test_run_checks_single_check_builds_observations(dummy_events, dummy_polygon_cache):
    """
    run_checks with a single check must return flagged rows with an 'Observations' column listing the check name.
    """
    checks_cfg = [
        {
            "name": "High RMS",
            "conditions": [
                {"rule_type": "numeric", "column": "quality_standardError", "mode": "gt", "threshold": 0.3},
            ],
        }
    ]

    result = engine.run_checks(dummy_events, checks=checks_cfg, polygon_cache=dummy_polygon_cache, event_type_col="event_type")

    # Rows 1 and 2 should be flagged
    assert len(result) == 2
    assert list(result["quality_standardError"]) == [0.5, 0.8]
    assert "Observations" in result.columns
    obs = result["Observations"].tolist()
    # Each observation must include the check name
    assert obs == ["High RMS", "High RMS"]


def test_run_checks_multiple_checks_merge_observations(dummy_events, dummy_polygon_cache):
    """
    run_checks with multiple checks must merge check names for events flagged by more than one rule.
    """
    checks_cfg = [
        {
            "name": "High RMS",
            "conditions": [
                {"rule_type": "numeric", "column": "quality_standardError", "mode": "gt", "threshold": 0.3},
            ],
        },
        {
            "name": "DESTACADO comment",
            "conditions": [
                {"rule_type": "category", "column": "comment", "values": ["DESTACADO"]},
            ],
        },
    ]

    result = engine.run_checks(dummy_events, checks=checks_cfg, polygon_cache=dummy_polygon_cache,
                               event_type_col="event_type")

    # Two rows should be flagged
    assert len(result) == 2

    # These rows correspond to rows 1 and 2 of dummy_events (quality_standardError 0.5 and 0.8)
    assert list(result["quality_standardError"]) == [0.5, 0.8]
    assert list(result["comment"]) == ["DESTACADO", "DESTACADO"]

    obs = result["Observations"].tolist()
    for o in obs:
        assert "High RMS" in o
        assert "DESTACADO comment" in o
        assert "; " in o


def test_run_checks_check_raising_error_is_skipped(dummy_events, dummy_polygon_cache, monkeypatch):
    """
    If a check raises an exception inside run_single_check, run_checks must skip it and continue with remaining checks.
    """
    # Patch run_single_check to raise for a specific check name
    original_run_single_check = engine.run_single_check

    def fake_run_single_check(events, check, polygon_cache, event_type_col="event_type"):
        if check.get("name") == "Broken check":
            raise RuntimeError("simulated failure")
        return original_run_single_check(events, check, polygon_cache, event_type_col=event_type_col)

    monkeypatch.setattr(engine, "run_single_check", fake_run_single_check)

    checks_cfg = [
        {
            "name": "Broken check",
            "conditions": [
                {"rule_type": "numeric", "column": "quality_standardError", "mode": "gt", "threshold": 0.0},
            ],
        },
        {
            "name": "Working check",
            "conditions": [
                {"rule_type": "numeric", "column": "quality_standardError", "mode": "gt", "threshold": 0.3},
            ],
        },
    ]

    result = engine.run_checks(dummy_events, checks=checks_cfg, polygon_cache=dummy_polygon_cache, event_type_col="event_type")

    # Only the working check should contribute observations
    assert len(result) == 2  # rows 1,2
    obs = result["Observations"].tolist()
    assert obs == ["Working check", "Working check"]


# ---------------------------------------------------------------------------
# Tests for run_duplicates
# ---------------------------------------------------------------------------

def test_run_duplicates_no_config_returns_empty(dummy_events):
    """
    When duplicates_cfg is empty, run_duplicates should return an empty DataFrame.
    """
    result = engine.run_duplicates(dummy_events, duplicates_cfg=[])
    assert isinstance(result, pd.DataFrame)
    assert result.empty


def test_run_duplicates_delegates_to_check_duplicates(monkeypatch):
    """
    run_duplicates must delegate to check_duplicates and merge Observations from multiple duplicates entries.
    """
    # Build a minimal DataFrame with default-like columns
    events = pd.DataFrame(
        {
            "time_value": pd.to_datetime(
                ["2024-01-01T00:00:00", "2024-01-01T00:00:01", "2024-01-01T00:10:00"]
            ),
            "latitude_value": [4.0, 4.00005, 5.0],
            "longitude_value": [-74.0, -74.00005, -75.0],
            "publicID": ["E1", "E2", "E3"],
        }
    )

    # Fake check_duplicates that returns E1/E2 as duplicates with simple Observations
    def fake_check_duplicates(events, subset, method, time_window, dist_threshold):
        dup_df = events.iloc[0:2].copy()
        dup_df["Observations"] = ["dup_obs_1", "dup_obs_2"]
        return dup_df

    monkeypatch.setattr(engine, "check_duplicates", fake_check_duplicates)

    duplicates_cfg = [
        {
            "name": "Dup rule A",
            "subset": ["time_value", "latitude_value", "longitude_value", "publicID"],
            "method": "adjacent",
            "time_window": 4,
            "dist_threshold": 50.0,
        }
    ]

    result = engine.run_duplicates(events, duplicates_cfg=duplicates_cfg)

    assert len(result) == 2
    assert list(result["publicID"]) == ["E1", "E2"]
    # Observations should include rule name and original obs text
    obs = result["Observations"].tolist()
    assert obs[0] == "Dup rule A: dup_obs_1"
    assert obs[1] == "Dup rule A: dup_obs_2"


if __name__ == "__main__":
    pytest.main()
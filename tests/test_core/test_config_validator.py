# Author: Garcia-Cifuentes, K. <ORCID:0009-0001-2607-6359>

# --------------------------------------------------------------------------------------------------------
# This file contains a test class for ConfigValidator Class
# --------------------------------------------------------------------------------------------------------
from __future__ import annotations

import pytest
from copy import deepcopy
from pathlib import Path
from typing import Any

from src.core.config_loader import ConfigManager
from src.core.config_validator import ConfigValidator


THIS_DIR = Path(__file__).resolve().parent
EXAMPLE_CFG_DIR = THIS_DIR / "test_examples"


@pytest.fixture
def valid_config_data() -> dict[str, Any]:
    """
    Load a known-good TOML fixture, then provide isolated mutable copies.

    Each test changes only the section needed for its validation case.
    """
    cm = ConfigManager(EXAMPLE_CFG_DIR / "validator_valid.toml")
    return deepcopy(cm.config_data)


def make_validator(config_data: dict[str, Any]) -> ConfigValidator:
    """
    Build a ConfigValidator with the valid fixture's ConfigManager metadata.

    ConfigManager has already parsed the fixture; replacing config_data's
    contents lets tests exercise static rules without creating files.
    """
    cm = ConfigManager(EXAMPLE_CFG_DIR / "validator_valid.toml")
    cm.config_data.clear()
    cm.config_data.update(config_data)
    return ConfigValidator(cm)


class TestConfigValidator:
    """Tests for ConfigValidator static validation rules."""

    def test_valid_full_configuration_passes(self, valid_config_data: dict[str, Any]):
        make_validator(valid_config_data).validate()


    # Check [[database]] entries
    def test_one_unnamed_database_is_valid(self, valid_config_data: dict[str, Any]):
        """
        Test that a config with one [[database]] entry without a name is valid.
        """
        valid_config_data["database"] = [
            {"env_file": ".env"}
        ]

        for query in valid_config_data["queries"]:
            query.pop("database", None)

        make_validator(valid_config_data).validate()

    def test_no_database_entries_raise(self, valid_config_data: dict[str, Any]):
        """
        Test that a config with no [[database]] entries raises a ValueError.
        """
        valid_config_data["database"] = []

        with pytest.raises(ValueError, match=r"No \[\[database\]\] entries"):
            make_validator(valid_config_data).validate()

    def test_multiple_databases_require_each_name(self, valid_config_data: dict[str, Any]):
        """
        Test that a config with multiple [[database]] entries requires each to have a name.
        """
        valid_config_data["database"][1].pop("name")
        with pytest.raises(ValueError, match="missing 'name'"):
            make_validator(valid_config_data).validate()

    def test_duplicate_database_names_raise(self, valid_config_data: dict[str, Any]):
        """Test that a config with duplicate [[database]] names raises a ValueError."""
        valid_config_data["database"][1]["name"] = "sc6"

        with pytest.raises(ValueError, match="duplicate database name 'sc6'"):
            make_validator(valid_config_data).validate()

    def test_reserved_default_database_name_raises(self, valid_config_data: dict[str, Any]):
        """
        Test that a config with a reserved default database name raises a ValueError.
        """
        valid_config_data["database"][0]["name"] = "__default__"

        with pytest.raises(ValueError, match="reserved"):
            make_validator(valid_config_data).validate()

    def test_database_without_credential_source_raises(self, valid_config_data: dict[str, Any]):
        """Test that a config with a [[database]] entry that has no credential source raises a ValueError."""

        valid_config_data["database"][0] = {"name": "sc6"}

        with pytest.raises(ValueError, match="provide credentials"):
            make_validator(valid_config_data).validate()

    def test_incomplete_direct_credentials_raise(self, valid_config_data: dict[str, Any]):
        """Test that a config with a [[database]] entry that has incomplete direct credentials raises a ValueError."""
        valid_config_data["database"][0] = {
            "name": "sc6",
            "host": "localhost",
            "user": "user",
        }

        with pytest.raises(ValueError, match="direct credentials are incomplete"):
            make_validator(valid_config_data).validate()

    @pytest.mark.parametrize("port", [0, -1, 3306.0, True, "3306"])
    def test_invalid_database_port_raises(self, valid_config_data: dict[str, Any], port: Any):
        """Test that a config with a [[database]] entry that has an invalid port raises a ValueError."""
        valid_config_data["database"][0]["port"] = port

        with pytest.raises(ValueError, match="port"):
            make_validator(valid_config_data).validate()


    # Check [[queries]] entries
    def test_no_queries_raise(self, valid_config_data: dict[str, Any]):
        """Test that a config with no [[queries]] entries raises a ValueError."""
        valid_config_data["queries"] = []

        with pytest.raises(ValueError, match=r"No \[\[queries\]\] entries"):
            make_validator(valid_config_data).validate()

    def test_missing_query_name_raises(self, valid_config_data: dict[str, Any]):
        """Test that a config with a [[queries]] entry that has no query name raises a ValueError."""
        valid_config_data["queries"][0].pop("name")

        with pytest.raises(ValueError, match="name must be a nonempty string"):
            make_validator(valid_config_data).validate()

    def test_duplicate_query_name_raises(self, valid_config_data: dict[str, Any]):
        """Test that a config with duplicate [[queries]] names raises a ValueError."""
        valid_config_data["queries"][1]["name"] = "events_sc6"

        with pytest.raises(ValueError, match="duplicate query name 'events_sc6'"):
            make_validator(valid_config_data).validate()

    def test_missing_sql_file_raises(self, valid_config_data: dict[str, Any]):
        """Test that a config with a [[queries]] entry that has no sql_file raises a ValueError."""
        valid_config_data["queries"][0].pop("sql_file")

        with pytest.raises(ValueError, match="sql_file must be a nonempty string"):
            make_validator(valid_config_data).validate()

    @pytest.mark.parametrize("skip", ["false", 0, 1, None])
    def test_non_boolean_query_skip_raises(self, valid_config_data: dict[str, Any], skip: Any):
        """Test that a config with a [[queries]] entry that has a non-boolean skip value raises a ValueError."""
        valid_config_data["queries"][0]["skip"] = skip

        with pytest.raises(ValueError, match="skip must be a boolean"):
            make_validator(valid_config_data).validate()

    def test_active_query_requires_database_with_multiple_profiles(self, valid_config_data: dict[str, Any]):
        """Test that a config with an active [[queries]] entry requires a database."""
        valid_config_data["queries"][0].pop("database")

        with pytest.raises(ValueError, match="database is required"):
            make_validator(valid_config_data).validate()

    def test_skipped_query_may_omit_database_with_multiple_profiles(self, valid_config_data: dict[str, Any]):
        """Test that a config with a skipped [[queries]] entry may omit a database."""
        valid_config_data["queries"][0].pop("database")
        valid_config_data["queries"][0]["skip"] = True

        make_validator(valid_config_data).validate()

    def test_unknown_query_database_raises(self, valid_config_data: dict[str, Any]):
        """Test that a config with a [[queries]] entry that has an unknown database raises a ValueError."""
        valid_config_data["queries"][0]["database"] = "unknown"

        with pytest.raises(ValueError, match="database 'unknown' is not defined"):
            make_validator(valid_config_data).validate()

    @pytest.mark.parametrize("database_name", ["", "   ", 42, True])
    def test_invalid_query_database_name_raises(self, valid_config_data: dict[str, Any], database_name: Any):
        """Test that a config with a [[queries]] entry that has an invalid database name raises a ValueError."""
        valid_config_data["queries"][0]["database"] = database_name

        with pytest.raises(ValueError, match="database must be a nonempty string"):
            make_validator(valid_config_data).validate()


    # Check [[polygons]] entries
    def test_missing_polygon_name_raises(self, valid_config_data: dict[str, Any]):
        """Test that a config with a [[polygons]] entry that has no polygon name raises a ValueError."""
        valid_config_data["polygons"][0].pop("name")

        with pytest.raises(ValueError, match="name must be a nonempty string"):
            make_validator(valid_config_data).validate()

    def test_duplicate_polygon_names_raise(self, valid_config_data: dict[str, Any]):
        """Test that a config with duplicate [[polygons]] names raises a ValueError."""
        valid_config_data["polygons"].append(
            {
                "name": "zone_a",
                "path": "polygons/zone_b.bna",
            }
        )

        with pytest.raises(ValueError, match="duplicate polygon name 'zone_a'"):
            make_validator(valid_config_data).validate()

    def test_missing_polygon_path_raises(self, valid_config_data: dict[str, Any]):
        """Test that a config with a [[polygons]] entry that has no polygon path raises a ValueError."""
        valid_config_data["polygons"][0].pop("path")

        with pytest.raises(ValueError, match="path must be a nonempty string"):
            make_validator(valid_config_data).validate()

    @pytest.mark.parametrize("skip", ["true", 0, None])
    def test_non_boolean_polygon_skip_raises(self, valid_config_data: dict[str, Any], skip: Any):
        """Test that a config with a [[polygons]] entry that has a non-boolean skip value raises a ValueError."""
        valid_config_data["polygons"][0]["skip"] = skip

        with pytest.raises(ValueError, match="skip must be a boolean"):
            make_validator(valid_config_data).validate()


    # Check [[duplicates]] entries
    @pytest.mark.parametrize("method", ["invalid", "", 42])
    def test_invalid_duplicate_method_raises(self, valid_config_data: dict[str, Any], method: Any):
        """Test that a config with a [[duplicates]] entry that has an invalid method raises a ValueError."""
        valid_config_data["duplicates"][0]["method"] = method

        with pytest.raises(ValueError, match="method must be one of"):
            make_validator(valid_config_data).validate()

    @pytest.mark.parametrize("time_window", [None, 0, -1, True, "5"])
    def test_invalid_duplicate_time_window_raises(self, valid_config_data: dict[str, Any], time_window: Any):
        """Test that a config with a [[duplicates]] entry that has an invalid time_window raises a ValueError."""
        valid_config_data["duplicates"][0]["time_window"] = time_window

        with pytest.raises(ValueError, match="time_window"):
            make_validator(valid_config_data).validate()

    @pytest.mark.parametrize("dist_threshold", [None, 0, -1.0, False, "10"])
    def test_invalid_duplicate_distance_threshold_raises(self, valid_config_data: dict[str, Any], dist_threshold: Any):
        valid_config_data["duplicates"][0]["dist_threshold"] = dist_threshold

        with pytest.raises(ValueError, match="dist_threshold"):
            make_validator(valid_config_data).validate()

    @pytest.mark.parametrize("subset", [[], "publicID", ["publicID", ""]])
    def test_invalid_duplicate_subset_raises( self, valid_config_data: dict[str, Any], subset: Any):
        """Test that a config with a [[duplicates]] entry that has an invalid subset raises a ValueError."""
        valid_config_data["duplicates"][0]["subset"] = subset

        with pytest.raises(ValueError, match="subset"):
            make_validator(valid_config_data).validate()

    @pytest.mark.parametrize("event_type", ["", [], ["earthquake", ""]])
    def test_invalid_duplicate_event_type_raises(self, valid_config_data: dict[str, Any], event_type: Any):
        """Test that a config with a [[duplicates]] entry that has an invalid event_type raises a ValueError."""
        valid_config_data["duplicates"][0]["event_type"] = event_type

        with pytest.raises(ValueError, match="event_type"):
            make_validator(valid_config_data).validate()


    # Check [[checks]] entries
    def test_missing_check_name_raises(self, valid_config_data: dict[str, Any]):
        """Test that a config with a [[checks]] entry that has no check name raises a ValueError."""
        valid_config_data["checks"][0].pop("name")

        with pytest.raises(ValueError, match="name must be a nonempty string"):
            make_validator(valid_config_data).validate()

    @pytest.mark.parametrize("logic", ["not", "", 42])
    def test_invalid_check_logic_raises(self, valid_config_data: dict[str, Any], logic: Any):
        """Test that a config with a [[checks]] entry that has an invalid check logic raises a ValueError."""
        valid_config_data["checks"][0]["logic"] = logic

        with pytest.raises(ValueError, match="logic"):
            make_validator(valid_config_data).validate()

    def test_empty_check_raises(self,  valid_config_data: dict[str, Any]):
        """Test that a config with a [[checks]] entry that has no conditions or groups raises a ValueError."""
        valid_config_data["checks"][0].pop("conditions")
        valid_config_data["checks"][0].pop("groups", None)
        valid_config_data["checks"][0].pop("logic", None)

        with pytest.raises(ValueError, match=r"define at least one direct condition or group"):
            make_validator(valid_config_data).validate()

    def test_multiple_direct_children_require_logic(self, valid_config_data: dict[str, Any]):
        """Test that a config with a [[checks]] entry that has multiple direct children requires a logic."""
        valid_config_data["checks"][0].pop("logic")
        valid_config_data["checks"][0]["conditions"].append(
            {
                "rule_type": "category",
                "column": "event_type",
                "mode": "in",
                "values": ["earthquake"],
            }
        )

        with pytest.raises(ValueError, match=r"logic must be a nonempty string"):
            make_validator(valid_config_data).validate()

    def test_unsupported_condition_rule_type_raises(self, valid_config_data: dict[str, Any]):
        """Test that a config with a [[checks]] entry that has an unsupported condition rule_type raises a ValueError."""
        valid_config_data["checks"][0]["conditions"][0]["rule_type"] = "unknown"

        with pytest.raises(ValueError, match="unsupported rule_type"):
            make_validator(valid_config_data).validate()

    def test_missing_condition_mode_raises(self, valid_config_data: dict[str, Any]):
        """Test that a config with a [[checks]] entry that has a condition with no mode raises a ValueError."""
        valid_config_data["checks"][0]["conditions"][0].pop("mode")

        with pytest.raises(ValueError, match="mode must be a nonempty string"):
            make_validator(valid_config_data).validate()

    def test_numeric_rule_requires_threshold_for_one_sided_modes(self, valid_config_data: dict[str, Any]):
        """Test that a config with a [[checks]] entry that has a numeric condition with a one-sided mode
        requires a threshold."""
        condition = valid_config_data["checks"][0]["conditions"][0]
        condition["rule_type"] = "numeric"
        condition["column"] = "magnitude"
        condition["mode"] = "gt"
        condition.pop("threshold", None)

        with pytest.raises(ValueError, match="threshold must be a number"):
            make_validator(valid_config_data).validate()

    def test_numeric_between_rule_requires_lower_and_upper(self, valid_config_data: dict[str, Any]):
        """Test that a config with a [[checks]] entry that has a numeric condition with a between mode
        requires both a lower and an upper threshold."""
        condition = valid_config_data["checks"][0]["conditions"][0]
        condition["rule_type"] = "numeric"
        condition["column"] = "magnitude"
        condition["mode"] = "between"
        condition.pop("threshold", None)
        condition["upper"] = 5.0
        condition.pop("lower", None)

        with pytest.raises(ValueError, match="lower must be a number"):
            make_validator(valid_config_data).validate()

    def test_category_in_rule_requires_values(self, valid_config_data: dict[str, Any]):
        """A category 'in' condition requires a nonempty values declaration."""
        condition = valid_config_data["checks"][0]["conditions"][0]

        condition.clear()
        condition.update({
            "rule_type": "category",
            "column": "event_type",
            "mode": "in",
        })

        with pytest.raises(
                ValueError,
                match=r"values",
        ):
            make_validator(valid_config_data).validate()

    def test_temporal_rule_requires_threshold(self, valid_config_data: dict[str, Any]):
        """Test that a config with a [[checks]] entry that has a temporal condition requires a threshold."""
        condition = valid_config_data["checks"][0]["conditions"][0]
        condition.clear()
        condition.update({
            "rule_type": "temporal",
            "column": "time_value",
            "mode": "gt",
        })

        with pytest.raises(ValueError, match="threshold must be a nonempty string"):
            make_validator(valid_config_data).validate()

    def test_column_column_rule_requires_left_and_right_columns(self, valid_config_data: dict[str, Any]):
        """Test that a config with a [[checks]] entry that has a column_column condition requires both left_col
        and right_col."""
        condition = valid_config_data["checks"][0]["conditions"][0]
        condition.clear()
        condition.update(
            {
                "rule_type": "column_column",
                "mode": "gt",
                "right_col": "reference_magnitude",
            }
        )

        with pytest.raises(ValueError, match="left_col must be a nonempty string"):
            make_validator(valid_config_data).validate()

    def test_polygon_rule_requires_known_polygon_reference(self, valid_config_data: dict[str, Any]):
        """Test that a config with a [[checks]] entry that has a polygon condition requires a known polygon reference."""
        condition = valid_config_data["checks"][0]["conditions"][0]
        condition.clear()
        condition.update(
            {
                "rule_type": "polygon",
                "lat_col": "latitude",
                "lon_col": "longitude",
                "mode": "inside",
                "polygon": "missing_zone",
            }
        )

        with pytest.raises(ValueError, match="unknown polygon name"):
            make_validator(valid_config_data).validate()

    def test_polygon_rule_requires_latitude_column(self, valid_config_data: dict[str, Any]):
        """Test that a config with a [[checks]] entry that has a polygon condition requires a latitude column."""
        condition = valid_config_data["checks"][0]["conditions"][0]
        condition.clear()
        condition.update(
            {
                "rule_type": "polygon",
                "lon_col": "longitude",
                "mode": "inside",
                "polygon": "zone_a",
            }
        )

        with pytest.raises(ValueError, match="lat_col must be a nonempty string"):
            make_validator(valid_config_data).validate()

    def test_single_child_group_may_omit_logic(self, valid_config_data: dict[str, Any]):
        """A node with exactly one direct child may omit logic."""
        valid_config_data["checks"][0] = {
            "name": "grouped_check",
            "groups": [
                {
                    "conditions": [
                        {
                            "rule_type": "numeric",
                            "column": "magnitude",
                            "mode": "gt",
                            "threshold": 3.0,
                        }
                    ]
                }
            ],
        }

        make_validator(valid_config_data).validate()

    def test_group_with_multiple_children_requires_logic(self, valid_config_data: dict[str, Any]):
        """A node with multiple direct children requires logic."""
        valid_config_data["checks"][0] = {
            "name": "grouped_check",
            "groups": [
                {
                    "conditions": [
                        {
                            "rule_type": "numeric",
                            "column": "magnitude",
                            "mode": "gt",
                            "threshold": 3.0,
                        },
                        {
                            "rule_type": "numeric",
                            "column": "depth",
                            "mode": "lt",
                            "threshold": 50.0,
                        },
                    ]
                }
            ],
        }

        with pytest.raises(
                ValueError,
                match=r"logic must be a nonempty string",
        ):
            make_validator(valid_config_data).validate()

    def test_empty_group_requires_at_least_one_direct_child(self, valid_config_data: dict[str, Any]):
        """An empty group must contain a direct condition or nested group."""
        valid_config_data["checks"][0] = {
            "name": "empty_group_check",
            "groups": [{"logic": "and"}],
        }

        with pytest.raises(
                ValueError,
                match=r"define at least one direct condition or group",
        ):
            make_validator(valid_config_data).validate()

    def test_nested_group_is_valid(self, valid_config_data):
        """Test that a config with a [[checks]] entry that has a nested group is valid."""
        valid_config_data["checks"][0] = {
            "name": "nested_groups",
            "groups": [{
                "groups": [{
                    "conditions": [{
                        "rule_type": "numeric",
                        "column": "magnitude",
                        "mode": "gt",
                        "threshold": 3.0,
                    }],
                }],
            }],
        }

        make_validator(valid_config_data).validate()

    def test_deep_empty_group_raises_with_path(self, valid_config_data):
        """Test that a config with a [[checks]] entry that has a deeply nested empty group raises a ValueError
        with a path to the offending group."""
        valid_config_data["checks"][0] = {
            "name": "bad_nested_groups",
            "groups": [{
                "groups": [{
                    "groups": [{}],
                }],
            }],
        }

        with pytest.raises(
                ValueError,
                match=r"groups entry #1\.groups entry #1\.groups entry #1.*"
                      r"define at least one direct condition or group",
        ):
            make_validator(valid_config_data).validate()

    def test_node_with_condition_and_group_requires_logic(self, valid_config_data):
        """Test that a config with a [[checks]] entry that has both a condition and a group requires a logic."""
        valid_config_data["checks"][0] = {
            "name": "mixed_children",
            "conditions": [{
                "rule_type": "numeric",
                "column": "magnitude",
                "mode": "gt",
                "threshold": 3.0,
            }],
            "groups": [{
                "conditions": [{
                    "rule_type": "numeric",
                    "column": "depth",
                    "mode": "gt",
                    "threshold": 10.0,
                }],
            }],
        }

        with pytest.raises(ValueError, match="logic must be a nonempty string"):
            make_validator(valid_config_data).validate()

    @pytest.mark.parametrize(
        ("condition", "expected_key"),
        [
            (
                    {
                        "rule_type": "numeric",
                        "column": "magnitude",
                        "mode": "gt",
                        "threshold": 4.0,
                        "polygon": "zone_a",
                    },
                    "polygon",
            ),
            (
                    {
                        "rule_type": "temporal",
                        "column": "time_value",
                        "mode": "ge",
                        "threshold": "2026-01-01T00:00:00Z",
                        "lower": 1,
                    },
                    "lower",
            ),
            (
                    {
                        "rule_type": "category",
                        "column": "event_type",
                        "mode": "in",
                        "values": "earthquake",
                        "value": "earthquake",
                    },
                    "value",
            ),
            (
                    {
                        "rule_type": "polygon",
                        "lat_col": "latitude",
                        "lon_col": "longitude",
                        "mode": "inside",
                        "polygon": "zone_a",
                        "threshold": 10,
                    },
                    "threshold",
            ),
            (
                    {
                        "rule_type": "column_column",
                        "left_col": "magnitude",
                        "right_col": "reference_magnitude",
                        "mode": "gt",
                        "column": "magnitude",
                    },
                    "column",
            ),
        ],
    )
    def test_condition_rejects_keys_not_allowed_for_rule_type(
            self,
            valid_config_data,
            condition,
            expected_key,
    ):
        """Test that a condition with keys not allowed for its rule type raises a ValueError."""
        valid_config_data["checks"][0]["conditions"] = [condition]

        with pytest.raises(
                ValueError,
                match=rf"unsupported key\(s\).*{expected_key}",
        ):
            make_validator(valid_config_data).validate()

    @pytest.mark.parametrize("mode", ["is_null", "is_not_null"])
    def test_category_null_modes_reject_values(self, valid_config_data, mode):
        """Test that a category rule with null modes rejects values."""
        valid_config_data["checks"][0]["conditions"] = [{
            "rule_type": "category",
            "column": "comment",
            "mode": mode,
            "values": ["DESTACADO"],
        }]

        with pytest.raises(ValueError, match="values"):
            make_validator(valid_config_data).validate()

    def test_group_rejects_root_only_event_type(self, valid_config_data):
        valid_config_data["checks"][0] = {
            "name": "invalid_group_key",
            "groups": [{
                "event_type": "earthquake",
                "conditions": [{
                    "rule_type": "numeric",
                    "column": "magnitude",
                    "mode": "gt",
                    "threshold": 3.0,
                }],
            }],
        }

        with pytest.raises(ValueError, match="unsupported key.*event_type"):
            make_validator(valid_config_data).validate()

    @pytest.mark.parametrize("negate", ["true", 1, None])
    def test_node_rejects_non_boolean_negate(self, valid_config_data, negate):
        """Test that a config with a [[checks]] entry that has a non-boolean negate value raises a ValueError."""
        valid_config_data["checks"][0]["negate"] = negate

        with pytest.raises(ValueError, match="negate must be a boolean"):
            make_validator(valid_config_data).validate()


    # Checks for output
    @pytest.mark.parametrize(
        "columns",
        [
            "publicID",
            [],
            ["publicID", ""],
            ["publicID", 42],
        ],
    )
    def test_invalid_output_columns_raise(self, valid_config_data: dict[str, Any], columns: Any):
        """Test that a config with invalid output columns raises a ValueError."""
        valid_config_data["output"]["columns"] = columns

        with pytest.raises(ValueError, match="columns"):
            make_validator(valid_config_data).validate()

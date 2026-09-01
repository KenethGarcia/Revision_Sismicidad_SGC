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

        with pytest.raises(ValueError, match="define at least one condition or group"):
            make_validator(valid_config_data).validate()
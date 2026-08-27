# Author: Garcia-Cifuentes, K. <ORCID:0009-0001-2607-6359>

# --------------------------------------------------------------------------------------------------------
# This file contains tests for DatabaseManager class.
# --------------------------------------------------------------------------------------------------------
import pytest
from pathlib import Path
from typing import Any

from src.core.config_loader import ConfigManager
from src.core.database_manager import DatabaseManager, DEFAULT_DATABASE_NAME

THIS_DIR = Path(__file__).resolve().parent
EXAMPLE_CFG_DIR = THIS_DIR / "test_examples"

# Emulate a fake connection class
class DummyConnection:
    """Simple dummy DB connection for testing."""

    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


# Helpers to build ConfigManager objects from example files
def _cm_multi_db() -> ConfigManager:
    cfg_path = EXAMPLE_CFG_DIR / "cfg_multiple_databases.toml"
    return ConfigManager(cfg_path)

def _cm_single_db() -> ConfigManager:
    cfg_path = EXAMPLE_CFG_DIR / "config_single_query_single_db.toml"
    return ConfigManager(cfg_path)

def _cm_database_case(filename: str) -> ConfigManager:
    cfg_path = EXAMPLE_CFG_DIR / filename
    return ConfigManager(cfg_path)


class TestDatabaseManager:
    """
    Tests for DatabaseManager.
    """

    @pytest.fixture(autouse=True)
    def setup_common_mocks(self, monkeypatch):
        """
        Common setup: mock load_credentials once for all tests in this class.
        """
        from src.core import database_manager as dbm_mod

        def fake_load_credentials(db_cfg: dict, base_dir: Path, config_name: str) -> dict[str, Any]:
            # Minimal behavior: return credentials keyed by profile name
            name = db_cfg.get("name", "unknown")
            return {
                "host": "localhost",
                "user": f"user_{name}",
                "password": f"pwd_{name}",
                "database": f"db_{name}",
                "port": 3306,
            }

        monkeypatch.setattr(dbm_mod, "load_credentials", fake_load_credentials)

    def test_db_manager_init_single_db(self):
        """
        Test the initialization of DatabaseManager with a single database.

        DatabaseManager should call load_credentials for the single [[database]]
        entry and store credentials under its profile name. get_credentials must
        return those credentials.
        """
        cm = _cm_single_db()
        dm = DatabaseManager(cm)

        creds = dm.get_credentials("sc6")
        assert creds["host"] == "localhost"
        assert creds["user"] == "user_sc6"
        assert creds["password"] == "pwd_sc6"
        assert creds["database"] == "db_sc6"
        assert creds["port"] == 3306

        with pytest.raises(KeyError):
            dm.get_credentials("unknown_profile")

    def test_single_env_file_database_without_name(self):
        """
        A single database profile may omit `name` when it uses one-single env_file.
        """
        cm = _cm_database_case("single_env_file_unnamed.toml")

        dm = DatabaseManager(cm)

        default_name = dm.get_db_name_for_query({"name": "events"})
        assert default_name == DEFAULT_DATABASE_NAME

        credentials = dm.get_credentials(default_name)

        assert credentials["host"] == "localhost"
        assert credentials["port"] == 3306

    def test_multiple_databases_with_one_unnamed_profile_raise(self):
        """
        Multiple profiles require a name on every [[database]] entry.
        """
        cm = _cm_database_case("multiple_one_unnamed.toml")

        with pytest.raises(ValueError, match="missing a 'name' field"):
            DatabaseManager(cm)

    def test_multiple_databases_with_duplicate_names_raise(self):
        """
        Database profile names must be unique; otherwise one credentials
        mapping would overwrite the other.
        """
        cm = _cm_database_case("multiple_duplicate_names.toml")

        with pytest.raises(ValueError, match=r"has duplicate name 'sc6'"):
            DatabaseManager(cm)

    def test_query_without_database_uses_sole_named_profile(self):
        """If a query does not specify a database and there is exactly one named"""
        cm = _cm_single_db()
        dm = DatabaseManager(cm)

        db_name = dm.get_db_name_for_query(
            {"name": "origin_standard"}
        )

        assert db_name == "sc6"

    def test_query_without_database_uses_sole_unnamed_profile(self):
        """If a query does not specify a database and there is exactly one unnamed"""
        cm = _cm_database_case("single_env_file_unnamed.toml")
        dm = DatabaseManager(cm)

        db_name = dm.get_db_name_for_query(
            {"name": "events"}
        )

        assert db_name == DEFAULT_DATABASE_NAME

    def test_query_with_explicit_database_uses_requested_profile(self):
        """If a query specifies a database, that profile is used."""
        cm = _cm_multi_db()
        dm = DatabaseManager(cm)

        db_name = dm.get_db_name_for_query(
            {"name": "events_sc6", "database": "sc6"}
        )

        assert db_name == "sc6"

    def test_query_with_unknown_database_raises(self):
        """If a query specifies a database that does not exist, raise ValueError."""
        cm = _cm_single_db()
        dm = DatabaseManager(cm)

        with pytest.raises(ValueError, match="no such profile exists"):
            dm.get_db_name_for_query(
                {"name": "events", "database": "unknown"}
            )

    @pytest.mark.parametrize(
        "database_value",
        ["", "   ", 42],
    )
    def test_query_with_invalid_database_field_raises(self, database_value):
        cm = _cm_single_db()
        dm = DatabaseManager(cm)

        with pytest.raises(ValueError, match="invalid 'database' field"):
            dm.get_db_name_for_query(
                {"name": "events", "database": database_value}
            )

    def test_query_without_database_with_multiple_profiles_raises(self):
        """
        A query must explicitly select a profile when multiple databases exist.
        """
        cm = _cm_database_case(
            "multiple_named_no_query_database.toml"
        )
        dm = DatabaseManager(cm)

        query_cfg = cm.select_query("events_without_database")

        with pytest.raises(
                ValueError,
                match="does not specify a database",
        ) as excinfo:
            dm.get_db_name_for_query(query_cfg)

        message = str(excinfo.value)

        assert "multiple database profiles" in message
        assert "Please specify a database explicitly" in message


if __name__ == "__main__":
    pytest.main()
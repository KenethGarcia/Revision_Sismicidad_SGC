# Author: Garcia-Cifuentes, K. <ORCID:0009-0001-2607-6359>

# --------------------------------------------------------------------------------------------------------
# This file contains tests for DatabaseManager class.
# --------------------------------------------------------------------------------------------------------
import pytest
import pandas as pd
from pathlib import Path
from typing import Any

from src.core.config_loader import ConfigManager
from src.core.database_manager import DatabaseManager

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


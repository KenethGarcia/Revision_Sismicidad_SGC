# Author: Garcia-Cifuentes, K. <ORCID:0009-0001-2607-6359>

# --------------------------------------------------------------------------------------------------------
# This file contains a test class for ConfigManager Class
# --------------------------------------------------------------------------------------------------------
from pathlib import Path
import pytest
from src.core.config_loader import ConfigManager, DEFAULT_DATABASE_NAME

THIS_DIR = Path(__file__).resolve().parent
EXAMPLE_CFG_DIR = THIS_DIR / "test_examples"

class TestConfigManager:
    """
    Tests for ConfigManager
    """
    # Tests for initialization
    def test_config_file_must_exist(self, tmp_path: Path):
        """Test that the config file exists"""
        non_existent = tmp_path / "missing.toml"
        with pytest.raises(FileNotFoundError):
            ConfigManager(non_existent)

    def test_config_path_must_be_file(self, tmp_path: Path):
        """Test with wrong directory cases"""
        # Make a directory instead of a file
        cfg_dir = tmp_path / "cfg_dir"
        cfg_dir.mkdir()
        with pytest.raises(ValueError):
            ConfigManager(cfg_dir)

    def test_non_toml_suffix_warns_but_loads(self, recwarn):
        """Test that even with wrong suffix file the config is loaded"""
        cfg_path = EXAMPLE_CFG_DIR / "config.txt"
        cm = ConfigManager(cfg_path)
        print(cm.config_data)
        # Ensure a warning was emitted about suffix
        assert any("Expected a .toml file" in str(w.message) for w in recwarn)
        # And that it still loaded the config_data
        dbs = cm.get_database()
        print(dbs)
        assert len(dbs) == 1
        assert dbs[0]["name"] == "sc6"

    # Test for accessors
    def test_get_sections_from_single_query_single_db(self, tmp_path: Path):
        """
        Basic config with one DB, one query, one check, one polygon.
        """
        cfg_path = EXAMPLE_CFG_DIR / "config_single_query_single_db.toml"
        cm = ConfigManager(cfg_path)

        assert cm.config_path == cfg_path.resolve()
        assert cm.base_dir == cfg_path.parent

        dbs = cm.get_database()
        assert isinstance(dbs, list)
        assert len(dbs) == 1
        assert dbs[0]["name"] == "sc6"

        queries = cm.get_queries()
        assert len(queries) == 1
        assert queries[0]["name"] == "origin_standard"

        checks = cm.get_checks()
        assert len(checks) == 1
        assert checks[0]["name"] == "High RMS"

        polys = cm.get_polygons()
        assert len(polys) == 1
        assert polys[0]["name"] == "zona1"

    def test_get_databases_wrong_type_raises(self):
        """
        If 'databases' is not a list (array-of-tables), get_databases must raise TypeError.
        """
        cfg_path = EXAMPLE_CFG_DIR / "config_wrong_cases_type.toml"
        cm = ConfigManager(cfg_path)

        with pytest.raises(TypeError):
            cm.get_database()

    def test_get_queries_wrong_type_raises(self):
        """
        If 'queries' is not a list, get_queries must raise TypeError.
        """
        cfg_path = EXAMPLE_CFG_DIR / "cfg_wrong_queries.toml"
        cm = ConfigManager(cfg_path)

        with pytest.raises(TypeError):
            cm.get_queries()

    def test_get_checks_wrong_type_raises(self):
        """
        If 'checks' is not a list, get_checks must raise TypeError.
        """
        cfg_path = EXAMPLE_CFG_DIR / "config_wrong_cases_type.toml"
        cm = ConfigManager(cfg_path)

        with pytest.raises(TypeError):
            cm.get_checks()

    def test_get_polygons_wrong_type_raises(self):
        """
        If 'polygons' is not a list, get_polygons must raise TypeError.
        """
        cfg_path = EXAMPLE_CFG_DIR / "config_wrong_cases_type.toml"
        cm = ConfigManager(cfg_path)

        with pytest.raises(TypeError):
            cm.get_polygons()

    # Test for select query
    def test_select_query_by_name(self):
        """
        Selecting a query by name should return the matching active query.
        """
        cfg_path = EXAMPLE_CFG_DIR / "config_multiple_queries.toml"
        cm = ConfigManager(cfg_path)

        q1 = cm.select_query(name="q1")
        assert q1["name"] == "q1"

        q2 = cm.select_query(name="q2")
        assert q2["name"] == "q2"

    def test_select_query_skips_skipped_entries(self):
        """
        Queries with skip=true must not be returned, even if names match.
        """
        cfg_path = EXAMPLE_CFG_DIR / "config_multiple_queries.toml"
        cm = ConfigManager(cfg_path)

        with pytest.raises(ValueError) as excinfo:
            cm.select_query(name="q3_skipped")

        assert "No active query named" in str(excinfo.value)

    def test_select_query_no_name_single_active(self):
        """
        If name is None and exactly one active query exists, it is returned.
        """
        cfg_path = EXAMPLE_CFG_DIR / "config_single_query_single_db.toml"
        cm = ConfigManager(cfg_path)

        q = cm.select_query()
        assert q["name"] == "origin_standard"

    def test_select_query_no_queries_defined(self, tmp_path: Path):
        """
        If no [[queries]] are defined, select_query must raise ValueError.
        """
        cfg_path = EXAMPLE_CFG_DIR / "config_no_queries.toml"
        cm = ConfigManager(cfg_path)

        with pytest.raises(ValueError) as excinfo:
            cm.select_query()

        assert "No active queries defined" in str(excinfo.value)

    def test_select_query_multiple_active_no_name_raises(self):
        """
        If multiple active queries exist and name is None, select_query must raise ValueError.
        """
        cfg_path = EXAMPLE_CFG_DIR / "config_multiple_queries.toml"
        cm = ConfigManager(cfg_path)

        with pytest.raises(ValueError) as excinfo:
            cm.select_query()

        msg = str(excinfo.value)
        assert "Multiple active queries defined" in msg
        assert "q1" in msg
        assert "q2" in msg

    def test_select_query_unknown_name_raises(self):
        """
        If name does not match any active query, select_query must raise ValueError.
        """
        cfg_path = EXAMPLE_CFG_DIR / "config_multiple_queries.toml"
        cm = ConfigManager(cfg_path)

        with pytest.raises(ValueError) as excinfo:
            cm.select_query(name="nonexistent")

        assert "No active query named 'nonexistent'" in str(excinfo.value)

    # Test default database name
    def test_default_database_single_entry(self):
        """
        If exactly one database profile exists and has a name, it is returned.
        """
        cfg_path = EXAMPLE_CFG_DIR / "config_single_query_single_db.toml"
        cm = ConfigManager(cfg_path)

        assert cm.default_database_name() == "sc6"

    def test_default_database_none_when_multiple(self):
        """
        If multiple database profiles exist, the default database name is None.
        """
        cfg_path = EXAMPLE_CFG_DIR / "cfg_multiple_databases.toml"
        cm = ConfigManager(cfg_path)

        assert cm.default_database_name() is None

    def test_default_database_unnamed_single_entry(self):
        """
        A sole unnamed database profile gets the internal default name.
        """
        cfg_path = EXAMPLE_CFG_DIR / "single_env_file_unnamed.toml"
        cm = ConfigManager(cfg_path)

        assert cm.default_database_name() == DEFAULT_DATABASE_NAME

    # Tests for [settings] helpers
    def test_settings_columns_explicit_values(self):
        """
        When [settings] is defined, getters should return those explicit values.
        """
        cfg_path = EXAMPLE_CFG_DIR / "config_single_query_single_db.toml"
        cm = ConfigManager(cfg_path)

        assert cm.get_event_type_column() == "event_type"
        assert cm.get_time_column() == "time_value"
        assert cm.get_author_column() == "creationInfo_author"

    def test_settings_columns_defaults_when_missing(self):
        """
        When [settings] is missing, getters should fall back to defaults.
        """
        cfg_path = EXAMPLE_CFG_DIR / "config_no_queries.toml"
        cm = ConfigManager(cfg_path)

        # These defaults must match what you coded in ConfigManager
        assert cm.get_event_type_column() == "event_type"
        assert cm.get_time_column() == "time_value"
        assert cm.get_author_column() == "creationInfo_author"

    def test_settings_event_type_wrong_type_raises(self):
        """
        If [settings].event_type_column is not a string, get_event_type_column must raise TypeError.
        """
        cfg_path = EXAMPLE_CFG_DIR / "config_wrong_settings_type.toml"
        cm = ConfigManager(cfg_path)

        with pytest.raises(TypeError):
            cm.get_event_type_column()

    def test_default_database_name_is_stripped(self, tmp_path: Path):
        """If a database name has leading/trailing whitespace, default_database_name should return the stripped version"""
        cfg_path = EXAMPLE_CFG_DIR / "whitespace_name.toml"

        cm = ConfigManager(cfg_path)

        assert cm.default_database_name() == "sc6"

    @pytest.mark.parametrize(
        "name_value",
        [
            'name = ""',
            'name = "   "',
            "name = 42",
        ],
    )
    def test_default_database_invalid_single_name_returns_none(
            self,
            tmp_path: Path,
            name_value: str,
    ):
        """If a database name is invalid, default_database_name should return None."""
        cfg_path = tmp_path / "invalid_name.toml"
        cfg_path.write_text(
            f"""[[database]]
    {name_value}
    """,
            encoding="utf-8",
        )

        cm = ConfigManager(cfg_path)

        assert cm.default_database_name() is None


if __name__ == "__main__":
    pytest.main()
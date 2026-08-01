# Author: Garcia-Cifuentes, K. <ORCID:0009-0001-2607-6359>

# --------------------------------------------------------------------------------------------------------
# This file contains functions to test SQL reader functions
# --------------------------------------------------------------------------------------------------------

import pytest
import warnings
from pathlib import Path

from src.io.sql import load_sql

THIS_DIR = Path(__file__).resolve().parent
EXAMPLE_SQL_DIR = THIS_DIR / "test_examples"

class TestLoadSQL:
    def test_load_sql_basic_relative_path(self):
        """
        Basic case: valid relative sql_file, .sql suffix, non-empty file.
        Should return a non-empty formatted SQL string.
        """
        base_dir = EXAMPLE_SQL_DIR
        sql_rel_path = Path("query_basic.sql")

        query_cfg = {
            "name": "query_basic",
            "sql_file": str(sql_rel_path),
            "description": "Test query",
        }

        sql_text = load_sql(query_cfg, base_dir=base_dir, config_name="config.toml")

        # sqlparse.strip_comments=True should remove comments
        assert "SELECT" in sql_text
        assert "Origin" in sql_text
        assert "--" not in sql_text
        assert sql_text.endswith(";")

    def test_load_sql_absolute_path(self):
        """
        If sql_file is absolute, load_sql should use it as-is, not prepend base_dir.
        """
        sql_path = (EXAMPLE_SQL_DIR / "query_basic.sql").resolve()

        query_cfg = {
            "name": "absolute_query",
            "sql_file": str(sql_path),
        }

        # base_dir is irrelevant for absolute paths
        sql_text = load_sql(query_cfg, base_dir=Path("/ignored"), config_name="config.toml")
        assert "SELECT" in sql_text
        assert "Origin" in sql_text
        assert "--" not in sql_text
        assert sql_text.endswith(";")


    def test_missing_sql_file_key_raises_value_error(self):
        """
        When 'sql_file' is missing in query_cfg, load_sql must raise ValueError.
        """
        query_cfg = {
            "name": "no_sql_file",
            # no 'sql_file'
        }

        with pytest.raises(ValueError) as excinfo:
            load_sql(query_cfg, base_dir=EXAMPLE_SQL_DIR, config_name="config.toml")

        msg = str(excinfo.value)
        assert "Missing 'sql_file' key" in msg
        assert "no_sql_file" in msg


    def test_query_marked_skip_raises_value_error(self):
        """
        If query_cfg has skip=true, load_sql must raise ValueError.
        """
        query_cfg = {
            "name": "skipped_query",
            "sql_file": "queries/query_basic.sql",
            "skip": True,
        }

        with pytest.raises(ValueError) as excinfo:
            load_sql(query_cfg, base_dir=EXAMPLE_SQL_DIR, config_name="config.toml")

        msg = str(excinfo.value)
        assert "skip=true" in msg
        assert "skipped_query" in msg


    def test_nonexistent_sql_file_raises_file_not_found(self):
        """
        When sql_file path does not exist, load_sql must raise FileNotFoundError.
        """
        query_cfg = {
            "name": "missing_sql",
            "sql_file": "queries/missing.sql",  # file not created on purpose
        }

        with pytest.raises(FileNotFoundError) as excinfo:
            load_sql(query_cfg, base_dir=EXAMPLE_SQL_DIR, config_name="config.toml")

        msg = str(excinfo.value)
        assert "was not found" in msg
        assert "missing_sql" in msg


    def test_non_sql_suffix_emits_warning(self):
        """
        If sql_file suffix is not .sql, load_sql should emit a warning and still read the file.
        """
        base_dir = EXAMPLE_SQL_DIR
        sql_rel_path = Path("query_non_sql_suffix.txt")

        query_cfg = {
            "name": "non_sql_suffix",
            "sql_file": str(sql_rel_path),
        }

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            sql_text = load_sql(query_cfg, base_dir=base_dir, config_name="config.toml")

        assert sql_text == "SELECT 1;"
        assert any("Expected a .sql file" in str(warn.message) for warn in w)


    def test_empty_sql_file_emits_warning_and_returns_empty_string(self):
        """
        If the SQL file is empty (or only comments), load_sql should warn and return an empty string.
        """
        base_dir = EXAMPLE_SQL_DIR
        sql_rel_path = Path("query_empty.sql")

        query_cfg = {
            "name": "empty_query",
            "sql_file": str(sql_rel_path),
        }

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            sql_text = load_sql(query_cfg, base_dir=base_dir, config_name="config.toml")

        assert sql_text == ""
        assert any("is empty" in str(warn.message) for warn in w)


    def test_name_optional_in_messages(self):
        """
        If 'name' is missing in query_cfg, load_sql should still work but
        messages should not break when q_name is empty.
        """
        base_dir = EXAMPLE_SQL_DIR
        sql_rel_path = Path("query_basic.sql")

        query_cfg = {
            # no 'name'
            "sql_file": str(sql_rel_path),
        }

        sql_text = load_sql(query_cfg, base_dir=base_dir, config_name="config.toml")
        assert "SELECT" in sql_text


if __name__ == "__main__":
    pytest.main()
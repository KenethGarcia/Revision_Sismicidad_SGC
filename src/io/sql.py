# Author: Garcia-Cifuentes, K. <ORCID:0009-0001-2607-6359>

# --------------------------------------------------------------------------------------------------------
# This file contains functions to read and clean SQL files
# --------------------------------------------------------------------------------------------------------
import warnings
import sqlparse
from pathlib import Path


def load_sql(
    query_cfg: dict,
    base_dir: Path,
    config_name: str,
) -> str:
    """
    Locate, read, and format the SQL file declared in the TOML [[queries]] entry.

    Parameters
    ----------
    query_cfg : dict
        Parsed contents of one [[queries]] entry from the TOML file.
        It is expected to contain at least:
            name        = "query1"
            sql_file    = "queries/query1.sql"
            description = "..."
            database    = "connection1"   # optional if only one DB
            skip        = true/false      # optional
    base_dir : Path
        Directory of the TOML file, used to resolve relative sql_file paths.
    config_name : str
        TOML filename, used only for error messages.

    Returns
    -------
    str
        Formatted SQL query string, comment-stripped via sqlparse.

    Raises
    ------
    ValueError
        – 'sql_file' key is absent from [[queries]] or query is marked skip=true.
    FileNotFoundError
        – declared sql_file path does not exist.
    """
    # Optional label for clearer error/warning messages
    q_name = query_cfg.get("name", "")

    # Skip flag: allow users to disable a query without deleting it
    if query_cfg.get("skip", False):
        raise ValueError(
            f"Query {q_name!r} in {config_name!r} is marked skip=true and "
            "cannot be loaded. Remove skip=true or choose another query."
        )

    sql_file_key = query_cfg.get("sql_file")
    if not sql_file_key:
        raise ValueError(
            f"Missing 'sql_file' key in [[queries]] entry {q_name!r} of "
            f"{config_name!r}. Declare the path to the .sql file to use."
        )

    sql_path = Path(sql_file_key)
    if not sql_path.is_absolute():
        sql_path = (base_dir / sql_path).resolve()

    if not sql_path.exists():
        raise FileNotFoundError(
            f"SQL file declared for query {q_name!r} in {config_name!r} "
            f"was not found: {sql_path}\n"
            "Check the 'sql_file' path under [[queries]]."
        )

    if sql_path.suffix.lower() != ".sql":
        warnings.warn(
            f"Expected a .sql file for query {q_name!r} but got "
            f"{sql_path.suffix!r}. Attempting to read anyway.",
            stacklevel=3,
        )

    sql_text = sqlparse.format(
        sql_path.read_text(encoding="utf-8"),
        strip_comments=True,
    ).strip()

    if not sql_text:
        warnings.warn(
            f"The SQL file at {sql_path} (query {q_name!r}) is empty. "
            "Queries will fail at execution time.",
            stacklevel=3,
        )

    return sql_text
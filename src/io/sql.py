# Author: Garcia-Cifuentes, K. <ORCID:0009-0001-2607-6359>

# --------------------------------------------------------------------------------------------------------
# This file contains functions to read sql files
# --------------------------------------------------------------------------------------------------------
import warnings
import sqlparse
from pathlib import Path


def load_sql(
    query_cfg:   dict,
    base_dir:    Path,
    config_name: str,
) -> str:
    """
    Locate, read, and lightly format the SQL file declared in the
    TOML [query] section.

    Parameters
    ----------
    query_cfg : dict
        Parsed contents of the TOML [query] section.
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
    ValueError        – 'sql_file' key is absent from [query].
    FileNotFoundError – declared sql_file path does not exist.
    """

    sql_file_key = query_cfg.get("sql_file")
    if not sql_file_key:
        raise ValueError(
            f"Missing 'sql_file' key in [query] section of {config_name!r}. "
            "Declare the path to the .sql file to use."
        )

    sql_path = Path(sql_file_key)
    if not sql_path.is_absolute():
        sql_path = (base_dir / sql_path).resolve()

    if not sql_path.exists():
        raise FileNotFoundError(
            f"SQL file declared in {config_name!r} was not found: {sql_path}\n"
            "Check the 'sql_file' path under [query]."
        )

    if sql_path.suffix.lower() != ".sql":
        warnings.warn(
            f"Expected a .sql file but got {sql_path.suffix!r}. "
            "Attempting to read anyway.",
            stacklevel=3,
        )

    sql_text = sqlparse.format(
        sql_path.read_text(encoding="utf-8"),
        strip_comments=True,
    ).strip()

    if not sql_text:
        warnings.warn(
            f"The SQL file at {sql_path} is empty. "
            "Queries will fail at execution time.",
            stacklevel=3,
        )

    return sql_text
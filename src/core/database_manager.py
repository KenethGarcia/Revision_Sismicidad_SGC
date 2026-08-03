# Author: Garcia-Cifuentes, K. <ORCID:0009-0001-2607-6359>

# --------------------------------------------------------------------------------------------------------
# This file contains a helper class to manage collections and fetch data from multiple databases. It will do:
# 1. Turn database config entries into usable credentials.
# 2. Select the correct database profile for a given query.
# 3. Fetch data via SQL queries
# --------------------------------------------------------------------------------------------------------
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping
from src.io.env import load_credentials
from src.core.config_loader import ConfigManager


class DatabaseManager:
    """
    Manage database credentials and DB selection for queries.

    This class is responsible for:
    - Resolve credentials for each [[database]] profile
    - Decide which database profile to use for a given [[queries]] entry
    - Fetch data via SQL queries, applying time filters if required
    """
    def __init__(self, config_manager: ConfigManager):
        """
        Initialize the DatabaseManager from a ConfigManager.

        Parameters
        ----------
        config_manager : ConfigManager
            Already-initialized ConfigManager pointing to the TOML file.
        """
        self._config_manager = config_manager
        self._base_dir: Path = config_manager.base_dir
        self._config_name: str = config_manager.config_path.name

        # Build credentials_by_name from [[database]] entries
        self._credentials_named: dict[str, dict[str, Any]] = {}

        db_cfgs = config_manager.get_database()
        for db_cfg in db_cfgs:
            profile_name = db_cfg.get("name")
            if not profile_name:
                raise ValueError("A [[database]] entry in {self._config_name} is missing a 'name' field")

            credentials = load_credentials(
                db_cfg = db_cfg,
                base_dir = self._base_dir,
                config_name = self._config_name
            )

            self._credentials_named[str(profile_name)] = credentials

    # Getter methods
    def get_credentials(self, db_name: str) -> dict[str, Any]:
        """
        Return the credentials associated with a given [[database]] profile.

        Parameters
        ----------
        db_name : str
            The name of the profile to query.

        Returns
        ---------
        dict[str, Any]
            Credentials with keys: host, port, user, password, database.

        Raises
        ---------
        KeyError
            If no credentials are found for the requested db_name.
        """
        try:
            return self._credentials_named[db_name]
        except KeyError:
            raise KeyError(f"No credentials found for database profile '{db_name!r}' in {self._config_name}")

    def get_db_name_for_query(self, query_cfg: Mapping[str, Any]) -> str:
        """
        Determine which database profile to use for a given [[queries]] entry.

        Routing:
        - If the query configuration specifies a "database" field, use that.
        - If the query configuration does not specify a "database" field, use ConfigManager.default_database_name()
        - If neither yields a valid name, raise a ValueError.

        Parameters
        ----------
        query_cfg : Mapping[str, Any]
            The configuration dictionary for a specific query. Parsed from [[queries]] entry.

        Returns
        -------
        str
            The name of the database profile to use.

        Raises
        ------
        ValueError
            If the query configuration does not specify a valid database.
        """
        db_name = query_cfg.get("database")
        # Prefer explicit field in TOML
        if db_name:
            db_name = str(db_name)
            if db_name not in self._credentials_named:
                raise ValueError(f"Query configuration specifies database '{db_name!r}', but no such profile exists in {self._config_name!r}")
            return db_name

        # Try to fall back to default database if no database name specified
        default_db_name = self._config_manager.default_database_name()
        if default_db_name is None:
            raise ValueError(f"Query configuration does not specify a database, and no default database is set in {self._config_name!r}")
        if default_db_name not in self._credentials_named:
            raise ValueError(f"Default database '{default_db_name!r}' is not defined in {self._config_name!r}")
        return default_db_name


    def fetch_events(
        self,
        query_cfg: dict,
        start,
        end,
        routing_cfg: dict | None = None,
    ): ...
        # 1. Decide which DB(s) to use (routing_cfg or query_cfg['database'])
        # 2. Load SQL via io.sql.load_sql
        # 3. Apply time filters (e.g., WHERE time BETWEEN start/end) if needed
        # 4. Run query via pandas.read_sql and return a DataFrame   g

# Author: Garcia-Cifuentes, K. <ORCID:0009-0001-2607-6359>

# --------------------------------------------------------------------------------------------------------
# This file contains a helper class to manage collections and fetch data from multiple databases. It will do:
# 1. Turn database config entries into usable credentials.
# 2. Select the correct database profile for a given query.
# 3. Fetch data via SQL queries
# --------------------------------------------------------------------------------------------------------
from __future__ import annotations

import pymysql
import warnings
import pandas as pd
from tqdm import tqdm
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
            query_cfg: Mapping[str, Any],
            sql_text: str,
            params: Mapping[str, Any] | None = None,
            read_sql_kwargs: Mapping[str, Any] | None = None,
    ) -> pd.DataFrame:
        """
        Execute the given SQL query against the database selected for this query and return the resulting event table.

        This method assumes that any filtering (time range, author, etc.) has already been applied to `sql_text` by
        the caller (core pipeline, CLI wrapper, or frontend). It does not modify the SQL.

        Parameters
        ----------
        query_cfg : Mapping[str, Any]
            Parsed contents of one [[queries]] entry from the TOML file.
            Used only to determine which database profile to use and for error messages / logging.
        sql_text : str
            Final SQL string to execute. May be a base query or a wrapped query with WHERE clauses and ORDER BY.
        params : Mapping[str, Any] or None, default=None
            Optional parameter dict to pass to pandas.read_sql for safe value substitution
            (e.g., {"start": "...", "end": "...", "author": "..."}).
        read_sql_kwargs : Mapping[str, Any] or None, default=None
            Additional keyword arguments forwarded to pandas.read_sql, such as chunksize or dtype hints.

        Returns
        -------
        pd.DataFrame
            Table containing the fetched events.

        Raises
        ------
        ConnectionError
            If the database connection cannot be established.
        pymysql.MySQLError
            If the underlying MySQL driver raises an error during execution.
        """
        if read_sql_kwargs is None:
            read_sql_kwargs = {}

        # Determine which DB profile to use
        db_name = self.get_db_name_for_query(query_cfg)
        credentials = self.get_credentials(db_name)

        # Connect and execute query
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            try:
                conn = pymysql.connect(
                    host=credentials["host"],
                    user=credentials["user"],
                    password=credentials["password"],
                    database=credentials["database"],
                    port=int(credentials.get("port", 3306)),
                )
            except pymysql.MySQLError as ce:
                raise ConnectionError(
                    f"Failed to connect to database profile {db_name!r} with the provided credentials: {ce}"
                )
            try:
                # Simple progress bar: one step representing the whole query
                with tqdm(
                        total=1,
                        desc=f"Querying database '{db_name}' for {query_cfg.get('name', '<unnamed>')}",
                        unit="query",
                        leave=False,
                        bar_format="{desc}",
                ) as pbar:
                    df = pd.read_sql(
                        sql_text,
                        conn,
                        params=params,
                        **read_sql_kwargs,
                    )
                    pbar.update(1)
            finally:
                conn.close()

        return df

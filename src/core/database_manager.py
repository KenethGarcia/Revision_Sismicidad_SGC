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
from src.core.config_loader import ConfigManager, DEFAULT_DATABASE_NAME


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
        Initialize the DatabaseManager from a ConfigManager. A single [[database]] entry may omit `name`
        It is stored internally under DEFAULT_DATABASE_NAME. Multiple profiles must each have a unique,
        nonempty name.

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

        if not db_cfgs:
            raise ValueError(f"No [[database]] entries found in {self._config_name!r}")

        multiple_databases = len(db_cfgs) > 1

        for index, db_cfg in enumerate(db_cfgs, start=1):
            profile_name = self._resolve_profile_name(
                db_cfg=db_cfg,
                index=index,
                multiple_databases=multiple_databases,
            )

            if profile_name in self._credentials_named:
                raise ValueError(
                    f"[[database]] entry #{index} in {self._config_name!r} "
                    f"has duplicate name {profile_name!r}. Database names must be unique."
                )

            credentials = load_credentials(
                db_cfg=db_cfg,
                base_dir=self._base_dir,
                config_name=self._config_name,
            )

            self._credentials_named[profile_name] = credentials


    def _resolve_profile_name(
            self,
            *,
            db_cfg: Mapping[str, Any],
            index: int,
            multiple_databases: bool,
    ) -> str:
        """
        Return the internal routing name for one [[database]] entry.

        With one database, an omitted name is represented internally by DEFAULT_DATABASE_NAME. With multiple databases,
        every entry needs an explicit name so queries can select a database unambiguously.
        """
        raw_name = db_cfg.get("name")

        if raw_name is None:
            if multiple_databases:
                raise ValueError(
                    f"[[database]] entry #{index} in {self._config_name!r} is missing a 'name' field. A name is "
                    f"required when multiple database profiles are configured."
                )

            return DEFAULT_DATABASE_NAME

        if not isinstance(raw_name, str) or not raw_name.strip():
            raise ValueError(
                f"[[database]] entry #{index} in {self._config_name!r} must have a nonempty string 'name' field."
            )

        profile_name = raw_name.strip()

        if profile_name == DEFAULT_DATABASE_NAME:
            raise ValueError(
                f"[[database]] entry #{index} in {self._config_name!r} "
                f"cannot use reserved name {DEFAULT_DATABASE_NAME!r}."
            )

        return profile_name

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
        configured_name = query_cfg.get("database")
        if configured_name is not None:
            if not isinstance(configured_name, str) or not configured_name.strip():
                raise ValueError(
                    f"Query configuration {query_cfg.get('name', '<unnamed>')!r} has an invalid 'database' field. "
                    "It must be a nonempty string."
                )
            db_name = configured_name.strip()
            if db_name not in self._credentials_named:
                raise ValueError(
                    f"Query configuration {query_cfg.get('name', '<unnamed>')!r} specifies database profile "
                    f"{db_name!r}, but no such profile exists in {self._config_name!r}."
                )
            return db_name

        if len(self._credentials_named) == 1:
            return next(iter(self._credentials_named))

        raise ValueError(
            f"Query configuration {query_cfg.get('name', '<unnamed>')!r} does not specify a database, "
            f"and there are multiple database profiles available in {self._config_name!r}. "
            f"Please specify a database explicitly."
        )

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

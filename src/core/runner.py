# Author: Garcia-Cifuentes, K. <ORCID:0009-0001-2607-6359>
#
# --------------------------------------------------------------------------------------------------------
# High-level runner class for pipeline routines. It performs the following actions from TOML file:
# - Load credentials
# - Load SQL
# - Load polygons
# - Fetch data from database
# - Check for duplicates
# - Perform checks
# - Return results
# --------------------------------------------------------------------------------------------------------
from __future__ import annotations

import pandas as pd
from pathlib import Path
from typing import Any, Mapping

from src.io.sql import load_sql
from src.io.polygons import load_polygons
from src.checks.duplicates import check_duplicates
from src.checks.engine import run_checks, run_duplicates
from src.core.config_loader import ConfigManager
from src.core.database_manager import DatabaseManager


class Runner:
    """
    High-level orchestration class that:
    1. Loads configuration (databases, queries, polygons, checks, output)
    2. Resolves DB credentials
    3. Loads SQL
    4. Loads cached polygons
    5. Fetches data from the selected database
    6. Optionally checks for duplicates
    7. Performs configured checks
    8. Applies [output] column selection and returns the final table
    """

    def __init__(self, config_path: Path):
        """
        Initialize the Runner with a path to the TOML configuration file.

        Parameters
        ----------
        config_path : Path
            Path to the TOML configuration file.
        """
        self._cm = ConfigManager(Path(config_path))
        self._dbm = DatabaseManager(self._cm)

    # Helpers
    def list_queries(self) -> list[str]:
        """
        Return the list of query names defined in [[queries]].
        """
        return [q.get("name", "") for q in self._cm.get_queries()]

    def list_checks(self) -> list[str]:
        """
        Return the list of check names defined in [[checks]].
        """
        return [c.get("name", "") for c in self._cm.get_checks()]

    # Main runner
    def run(
        self,
        *,
        query_name: str | None = None,
        multi_query: bool = True,
        perform_duplicates: bool = True,
        perform_checks: bool = True,
        sql_text_override: str | None = None,
        sql_params: Mapping[str, Any] | None = None,
    ) -> pd.DataFrame:
        """
        Run the full pipeline:

        1. Load credentials (via DatabaseManager)
        2. Load SQL (via io.sql.load_sql) or override with a wrapped SQL string
        3. Load cached polygons
        4. Fetch data from one or more databases
        5. Check for duplicates, if requested
        6. Perform checks, if configured
        7. Apply [output] column selection and return the final table

         CLI and frontend modules can extend or override behavior by:
        - Supplying a wrapped SQL string and params instead of the base SQL.
        - Toggling perform_duplicates / perform_checks flags.
        - Adjusting output selection or adding extra post-processing.

        Parameters
        ----------
        query_name : str or None, default=None
            Name of the query to run. If None and multi_query is set to False, ConfigManager.select_query() will choose
            a single active query if unambiguous. If multi_query is True, it is possible use this parameter to select a
            specific query.
        multi_query : bool, default=True
            Bool variable to set whether to run all non-skipped queries or a single query. Defaults to True
            If True, the pipeline will run all non-skipped queries and concatenate results based on columns.
            If False, run a single query. It assumes the same schema across queries (e.g., tables mapped to
            canonical columns).
        perform_duplicates : bool, default=True
            If True, run duplicate detection and annotate the events table. If False, skip duplicate detection.
        perform_checks : bool, default=True
            If True, run configured checks and annotate the events table.
        sql_text_override : str or None, default=None
            If provided, this SQL string is executed instead of the base SQL from the config.
            Intended for CLI/frontend wrapping or custom runs.
        sql_params : Mapping[str, Any] or None, default=None
            Optional parameters dict passed to pandas.read_sql via DatabaseManager.fetch_events.
            CLI/frontend can use this to apply time/author filters safely.

        Returns
        -------
        pd.DataFrame
            Final output table after checks and [output] column selection.
        """
        # 1. Load polygons (cached polygons for spatial checks)
        polygons_cfg = self._cm.get_polygons()
        polygon_cache = load_polygons(polygons_cfg, base_dir=self._cm.base_dir)

        # 2. Fetch events (single or multiple queries)
        # If multi_query is set and query_name is None, fetch all non-skipped queries and concatenate results
        if multi_query and not query_name:
            events_df = self._fetch_all_queries()
        else:
            events_df = self._fetch_single_query(
                query_name=query_name,
                sql_text_override=sql_text_override,
                sql_params=sql_params,
            )

        # 3. Check for duplicates, if requested
        if perform_duplicates:  # Check this for multiple [[duplicates]] settings
            duplicates_cfg = self._cm.config_data.get("duplicates", [])
            if isinstance(duplicates_cfg, list) and duplicates_cfg:
                dup_df = run_duplicates(events_df, duplicates_cfg)
            else:
                dup_df = events_df.iloc[0:0].copy()
        else:
            dup_df = events_df.iloc[0:0].copy()

        # 4. Perform checks, if configured and enabled
        if perform_checks:
            checks_cfg = self._cm.get_checks()
            if checks_cfg:
                flagged_df = run_checks(
                    events=events_df,
                    checks=checks_cfg,
                    polygon_cache=polygon_cache,
                    event_type_col="event_type"  # Check the event_type filtering
                )
            else:
                flagged_df = events_df.iloc[0:0].copy()
        else:
            flagged_df = events_df

        # 5. Apply [output] column selection and return final table
        output_df = self._apply_output_selection(flagged_df)

        return output_df


    # Internal helpers
    def _fetch_single_query(
            self,
            *,
            query_name: str | None,
            sql_text_override: str | None,
            sql_params: Mapping[str, Any] | None,
    ) -> pd.DataFrame:
        """
        Fetch events for a single query (one [[queries]] entry).
        """
        query_cfg = self._cm.select_query(name=query_name)

        if sql_text_override is not None:
            sql_text = sql_text_override
        else:
            sql_text = load_sql(
                query_cfg=query_cfg,
                base_dir=self._cm.base_dir,
                config_name=self._cm.config_path.name,
            )

        events_df = self._dbm.fetch_events(
            query_cfg=query_cfg,
            sql_text=sql_text,
            params=sql_params,
            read_sql_kwargs={},
        )
        return events_df

    def _fetch_all_queries(self) -> pd.DataFrame:
        """
        Fetch events for ALL non-skipped [[queries]] entries and concatenate.

        Assumes:
        - All queries share the same canonical schema (same columns).
        - Each query may use a different database profile (via 'database' field).
        """
        query_cfgs = self._cm.get_queries()
        active_queries: list[Mapping[str, Any]] = [
            q for q in query_cfgs if not q.get("skip", False)
        ]

        # If no active queries: return empty table
        if not active_queries:
            return pd.DataFrame()

        frames: list[pd.DataFrame] = []

        for query_cfg in active_queries:
            sql_text = load_sql(
                query_cfg=query_cfg,
                base_dir=self._cm.base_dir,
                config_name=self._cm.config_path.name,
            )

            df = self._dbm.fetch_events(
                query_cfg=query_cfg,
                sql_text=sql_text,
                params=None,  # multi-query core: no auto filters
                read_sql_kwargs={},
            )

            # Optionally tag origin DB / query name for debugging
            df = df.copy()
            df["_source_query"] = query_cfg.get("name", "")
            frames.append(df)

        # Concatenate all frames; ignore indices (reindex after concat)
        combined = pd.concat(frames, axis=0, ignore_index=True)
        return combined

    def _apply_output_selection(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply [output] column selection from the TOML configuration.

        If no [output] section is defined, return the full DataFrame.
        """
        cfg_data = self._cm.config_data
        output_cfg = cfg_data.get("output")

        if output_cfg is None:
            return df

        if not isinstance(output_cfg, dict):
            raise TypeError(
                "Expected [output] to be a single table in the TOML config."
            )

        columns = output_cfg.get("columns")
        if not columns:
            return df

        missing = [c for c in columns if c not in df.columns]
        if missing:
            raise ValueError(
                f"Configured [output].columns {missing!r} are missing from the events DataFrame. "
                f"Check your SQL SELECT list and [output] configuration."
            )

        return df[columns]
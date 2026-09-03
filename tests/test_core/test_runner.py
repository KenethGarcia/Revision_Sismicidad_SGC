# Author: Garcia-Cifuentes, K. <ORCID:0009-0001-2607-6359>

# --------------------------------------------------------------------------------------------------------
# This file contains tests for Runner class
# --------------------------------------------------------------------------------------------------------
from __future__ import annotations

import pandas as pd
import pytest
from copy import deepcopy
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import src.core.runner as runner_module
from src.core.config_loader import ConfigManager
from src.core.runner import RunResult, Runner


THIS_DIR = Path(__file__).resolve().parent
EXAMPLE_CFG_DIR = THIS_DIR / "test_examples"
VALID_TOML = EXAMPLE_CFG_DIR / "validator_valid.toml"


@pytest.fixture
def valid_config_data() -> dict[str, Any]:
    """Return an isolated copy of the one persistent valid TOML fixture."""
    cm = ConfigManager(VALID_TOML)
    return deepcopy(cm.config_data)


@pytest.fixture
def events_df() -> pd.DataFrame:
    """Events returned by the database layer."""
    return pd.DataFrame(
        {
            "publicID": ["event-1", "event-2", "event-3"],
            "time_value": pd.to_datetime(
                [
                    "2026-01-03T00:00:00Z",
                    "2026-01-01T00:00:00Z",
                    "2026-01-02T00:00:00Z",
                ],
                utc=True,
            ),
            "event_type": ["earthquake", "explosion", "earthquake"],
            "magnitude": [4.5, 3.0, 5.2],
        }
    )


@pytest.fixture
def runner(valid_config_data: dict[str, Any]) -> Runner:
    """
    Create a Runner without invoking __init__.

    Tests inject a ConfigManager built from the persistent fixture, then replace only its parsed configuration data.
    This avoids database setup.
    """
    instance = Runner.__new__(Runner)

    cm = ConfigManager(VALID_TOML)
    cm.config_data.clear()
    cm.config_data.update(valid_config_data)

    instance._cm = cm
    instance._dbm = Mock()

    return instance


def make_runner(config_data: dict[str, Any]) -> Runner:
    """Create a Runner with fixture metadata and supplied parsed config."""
    instance = Runner.__new__(Runner)

    cm = ConfigManager(VALID_TOML)
    cm.config_data.clear()
    cm.config_data.update(config_data)

    instance._cm = cm
    instance._dbm = Mock()

    return instance


class TestRunnerInitialization:
    """Tests for Runner construction and simple configuration helpers."""

    def test_init_builds_config_manager_validator_and_database_manager(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """Test that Runner.__init__ builds the expected components and calls validation."""
        config_manager = Mock()
        database_manager = Mock()

        config_manager_cls = Mock(return_value=config_manager)
        validator = Mock()
        validator_cls = Mock(return_value=validator)
        database_manager_cls = Mock(return_value=database_manager)

        monkeypatch.setattr(runner_module, "ConfigManager", config_manager_cls)
        monkeypatch.setattr(runner_module, "ConfigValidator", validator_cls)
        monkeypatch.setattr(
            runner_module,
            "DatabaseManager",
            database_manager_cls,
        )

        runner = Runner(VALID_TOML)

        config_manager_cls.assert_called_once_with(VALID_TOML)
        validator_cls.assert_called_once_with(config_manager)
        validator.validate.assert_called_once_with()
        database_manager_cls.assert_called_once_with(config_manager)

        assert runner._cm is config_manager
        assert runner._dbm is database_manager

    def test_list_queries_returns_configured_names(self, runner: Runner):
        """Test that list_queries returns the names of configured queries in order."""
        assert runner.list_queries() == ["events_sc6", "events_sc3"]

    def test_list_checks_returns_configured_names(self, runner: Runner):
        """Test that list_checks returns the names of configured checks in order."""
        assert runner.list_checks() == ["high_magnitude"]


class TestRunnerFetchSingleQuery:
    """Tests for fetching a selected query."""

    def test_fetch_single_query_loads_sql_and_fetches_events(
        self,
        runner: Runner,
        monkeypatch: pytest.MonkeyPatch,
        events_df: pd.DataFrame,
    ):
        """Test that _fetch_single_query loads the SQL from file and calls fetch_events with the correct parameters."""
        query_cfg = {
            "name": "events_sc6",
            "sql_file": "sql/events_sc6.sql",
            "database": "sc6",
        }

        runner._cm.select_query = Mock(return_value=query_cfg)
        runner._dbm.fetch_events = Mock(return_value=events_df)

        load_sql_mock = Mock(return_value="SELECT * FROM events")
        monkeypatch.setattr(runner_module, "load_sql", load_sql_mock)

        result = runner._fetch_single_query(
            query_name="events_sc6",
            sql_text_override=None,
            sql_params={"start_time": "2026-01-01"},
        )

        assert result is events_df

        runner._cm.select_query.assert_called_once_with(name="events_sc6")

        load_sql_mock.assert_called_once_with(
            query_cfg=query_cfg,
            base_dir=runner._cm.base_dir,
            config_name=runner._cm.config_path.name,
        )

        runner._dbm.fetch_events.assert_called_once_with(
            query_cfg=query_cfg,
            sql_text="SELECT * FROM events",
            params={"start_time": "2026-01-01"},
            read_sql_kwargs={},
        )

    def test_fetch_single_query_uses_sql_override_without_loading_file(
        self,
        runner: Runner,
        monkeypatch: pytest.MonkeyPatch,
        events_df: pd.DataFrame,
    ):
        """Test that _fetch_single_query uses the provided SQL text override and does not load from file."""
        query_cfg = {
            "name": "events_sc6",
            "sql_file": "sql/events_sc6.sql",
            "database": "sc6",
        }

        runner._cm.select_query = Mock(return_value=query_cfg)
        runner._dbm.fetch_events = Mock(return_value=events_df)

        load_sql_mock = Mock()
        monkeypatch.setattr(runner_module, "load_sql", load_sql_mock)

        result = runner._fetch_single_query(
            query_name="events_sc6",
            sql_text_override="SELECT * FROM custom_events",
            sql_params=None,
        )

        assert result is events_df
        load_sql_mock.assert_not_called()

        runner._dbm.fetch_events.assert_called_once_with(
            query_cfg=query_cfg,
            sql_text="SELECT * FROM custom_events",
            params=None,
            read_sql_kwargs={},
        )


class TestRunnerFetchAllQueries:
    """Tests for fetching and combining configured active queries."""

    def test_fetch_all_queries_returns_empty_dataframe_when_all_skipped(
        self,
        runner: Runner,
    ):
        """Test that _fetch_all_queries returns an empty DataFrame when all configured queries are marked as skipped."""
        runner._cm.get_queries = Mock(
            return_value=[
                {"name": "events_sc6", "skip": True},
                {"name": "events_sc3", "skip": True},
            ]
        )

        result = runner._fetch_all_queries()

        assert result.empty
        runner._dbm.fetch_events.assert_not_called()

    def test_fetch_all_queries_concatenates_and_sorts_by_time(
        self,
        runner: Runner,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """Test that _fetch_all_queries fetches events from multiple queries, concatenates them, and sorts by the
        configured time column."""
        query_1 = {
            "name": "events_sc6",
            "sql_file": "sql/events_sc6.sql",
            "database": "sc6",
        }
        query_2 = {
            "name": "events_sc3",
            "sql_file": "sql/events_sc3.sql",
            "database": "sc3",
        }

        first = pd.DataFrame(
            {
                "publicID": ["event-2"],
                "time_value": ["2026-01-02T00:00:00Z"],
            }
        )
        second = pd.DataFrame(
            {
                "publicID": ["event-1"],
                "time_value": ["2026-01-01T00:00:00Z"],
            }
        )

        runner._cm.get_queries = Mock(return_value=[query_1, query_2])
        runner._cm.get_time_column = Mock(return_value="time_value")
        runner._dbm.fetch_events = Mock(side_effect=[first, second])

        monkeypatch.setattr(
            runner_module,
            "load_sql",
            Mock(side_effect=["SELECT 1", "SELECT 2"]),
        )

        result = runner._fetch_all_queries()

        assert result["publicID"].tolist() == ["event-1", "event-2"]
        assert str(result["time_value"].dtype) == "datetime64[ns, UTC]"

        assert runner._dbm.fetch_events.call_count == 2

    def test_fetch_all_queries_warns_and_returns_unsorted_data_when_sort_fails(
        self,
        runner: Runner,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """Test that _fetch_all_queries warns and returns unsorted data when the time column cannot be sorted."""
        query_cfg = {
            "name": "events_sc6",
            "sql_file": "sql/events_sc6.sql",
            "database": "sc6",
        }

        returned = pd.DataFrame(
            {
                "publicID": ["event-1"],
                "not_time_value": ["not-a-date"],
            }
        )

        runner._cm.get_queries = Mock(return_value=[query_cfg])
        runner._cm.get_time_column = Mock(return_value="time_value")
        runner._dbm.fetch_events = Mock(return_value=returned)

        monkeypatch.setattr(
            runner_module,
            "load_sql",
            Mock(return_value="SELECT 1"),
        )

        with pytest.warns(UserWarning, match="Error occurred while sorting"):
            result = runner._fetch_all_queries()

        pd.testing.assert_frame_equal(result, returned)


class TestRunnerOutputTable:
    """Tests for combining review results and applying [output] selection."""

    def test_build_output_table_returns_empty_table_with_observations_column(
        self,
        runner: Runner,
        events_df: pd.DataFrame,
    ):
        """Test that _build_output_table returns an empty DataFrame with the expected columns when no events
        are provided."""
        empty = events_df.iloc[0:0].copy()

        result = runner._build_output_table(
            events=events_df,
            duplicates=empty,
            checks=empty,
        )

        assert result.empty
        assert result.columns.tolist() == [
            "publicID",
            "time_value",
            "event_type",
            "magnitude",
            "Observations",
        ]

    def test_build_output_table_merges_duplicate_and_check_observations(
        self,
        runner: Runner,
        events_df: pd.DataFrame,
    ):
        """Test that _build_output_table merges observations from duplicates and checks into a single column,
        preserving the order of events."""
        duplicates = pd.DataFrame(
            {
                "Observations": [
                    "Possible duplicate",
                    "Possible duplicate",
                ]
            },
            index=[0, 1],
        )

        checks = pd.DataFrame(
            {
                "Observations": [
                    "High magnitude",
                    "Possible duplicate",
                ]
            },
            index=[0, 2],
        )

        result = runner._build_output_table(
            events=events_df,
            duplicates=duplicates,
            checks=checks,
        )

        assert result["publicID"].tolist() == [
            "event-1",
            "event-2",
            "event-3",
        ]

        assert result["Observations"].tolist() == [
            "Possible duplicate; High magnitude",
            "Possible duplicate",
            "Possible duplicate",
        ]

        assert result.index.tolist() == [0, 1, 2]

    def test_apply_output_selection_adds_observations_column(
        self,
        runner: Runner,
        events_df: pd.DataFrame,
    ):
        """Test that _apply_output_selection adds the Observations column to the output when it is not explicitly
        requested in the [output] configuration."""
        runner._cm.config_data["output"] = {
            "columns": ["publicID", "magnitude"],
        }

        checks = pd.DataFrame(
            {"Observations": ["High magnitude"]},
            index=[0],
        )
        duplicates = events_df.iloc[0:0].copy()

        result = runner._apply_output_selection(
            events=events_df,
            checks=checks,
            dups=duplicates,
        )

        assert result.columns.tolist() == [
            "publicID",
            "magnitude",
            "Observations",
        ]

        assert result.iloc[0].to_dict() == {
            "publicID": "event-1",
            "magnitude": 4.5,
            "Observations": "High magnitude",
        }

    def test_apply_output_selection_does_not_duplicate_observations(
        self,
        runner: Runner,
        events_df: pd.DataFrame,
    ):
        """Test that _apply_output_selection does not duplicate the Observations column when it is explicitly"""
        runner._cm.config_data["output"] = {
            "columns": ["Observations", "publicID"],
        }

        checks = pd.DataFrame(
            {"Observations": ["High magnitude"]},
            index=[0],
        )
        duplicates = events_df.iloc[0:0].copy()

        result = runner._apply_output_selection(
            events=events_df,
            checks=checks,
            dups=duplicates,
        )

        assert result.columns.tolist() == ["Observations", "publicID"]

    def test_apply_output_selection_returns_full_review_table_without_output_section(
        self,
        runner: Runner,
        events_df: pd.DataFrame,
    ):
        """Test that _apply_output_selection returns the full review table when there is no [output] section in the
        configuration."""
        runner._cm.config_data.pop("output", None)

        checks = pd.DataFrame(
            {"Observations": ["High magnitude"]},
            index=[0],
        )
        duplicates = events_df.iloc[0:0].copy()

        result = runner._apply_output_selection(
            events=events_df,
            checks=checks,
            dups=duplicates,
        )

        assert result.columns.tolist() == [
            "publicID",
            "time_value",
            "event_type",
            "magnitude",
            "Observations",
        ]

    def test_apply_output_selection_rejects_non_mapping_output_config(
        self,
        runner: Runner,
        events_df: pd.DataFrame,
    ):
        """Test that _apply_output_selection raises a TypeError when the [output] configuration is not a mapping (dict)."""
        runner._cm.config_data["output"] = ["publicID"]

        empty = events_df.iloc[0:0].copy()

        with pytest.raises(TypeError, match="Expected \\[output\\]"):
            runner._apply_output_selection(
                events=events_df,
                checks=empty,
                dups=empty,
            )

    def test_apply_output_selection_rejects_missing_requested_column(
        self,
        runner: Runner,
        events_df: pd.DataFrame,
    ):
        """Test that _apply_output_selection raises a ValueError when a requested column in the [output] configuration
        is missing."""
        runner._cm.config_data["output"] = {
            "columns": ["publicID", "missing_column"],
        }

        checks = pd.DataFrame(
            {"Observations": ["High magnitude"]},
            index=[0],
        )
        duplicates = events_df.iloc[0:0].copy()

        with pytest.raises(ValueError, match="missing_column"):
            runner._apply_output_selection(
                events=events_df,
                checks=checks,
                dups=duplicates,
            )


class TestRunnerSaveOutput:
    """Tests for the configured output writer."""

    @pytest.mark.parametrize(
        ("file_format", "file_name"),
        [
            ("csv", "review.csv"),
            ("json", "review.json"),
        ],
    )
    def test_save_output_writes_relative_path(
        self,
        runner: Runner,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        file_format: str,
        file_name: str,
    ):
        """Test that _save_output writes the output DataFrame to the configured relative path and format, and returns
        the path to the saved file."""
        monkeypatch.chdir(tmp_path)

        output = pd.DataFrame(
            {
                "publicID": ["event-1"],
                "magnitude": [4.5],
                "Observations": ["High magnitude"],
            }
        )

        runner._cm.config_data["output"] = {
            "file_format": file_format,
            "file_path": f"results/{file_name}",
        }

        saved_path = runner._save_output(output)

        expected_path = tmp_path / "results" / file_name

        assert saved_path == expected_path
        assert expected_path.exists()

        if file_format == "csv":
            actual = pd.read_csv(expected_path)
        else:
            actual = pd.read_json(expected_path, orient="records")

        pd.testing.assert_frame_equal(
            actual,
            output,
            check_dtype=False,
        )

    def test_save_output_uses_default_filename(
        self,
        runner: Runner,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """Test that _save_output uses the default filename when no file_path is specified in the [output] configuration."""
        monkeypatch.chdir(tmp_path)

        output = pd.DataFrame(
            {
                "publicID": ["event-1"],
                "Observations": ["High magnitude"],
            }
        )

        runner._cm.config_data["output"] = {
            "file_format": "csv",
        }

        saved_path = runner._save_output(output)

        assert saved_path == tmp_path / "output.csv"
        assert saved_path.exists()

    def test_save_output_accepts_absolute_path(
        self,
        runner: Runner,
        tmp_path: Path,
    ):
        """Test that _save_output accepts an absolute path in the [output] configuration."""
        output = pd.DataFrame(
            {
                "publicID": ["event-1"],
                "Observations": ["High magnitude"],
            }
        )

        destination = tmp_path / "nested" / "review.csv"

        runner._cm.config_data["output"] = {
            "file_format": "csv",
            "file_path": str(destination),
        }

        saved_path = runner._save_output(output)

        assert saved_path == destination
        assert destination.exists()

    @pytest.mark.parametrize(
        ("file_format", "file_name", "reader"),
        [
            ("parquet", "review.parquet", pd.read_parquet),
            ("feather", "review.feather", pd.read_feather),
        ],
    )
    def test_save_output_writes_arrow_based_formats(
        self,
        runner: Runner,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        file_format: str,
        file_name: str,
        reader,
    ):
        """Test that _save_output writes the output DataFrame to the configured Arrow-based format (Parquet or Feather)"""
        pytest.importorskip("pyarrow")
        monkeypatch.chdir(tmp_path)

        output = pd.DataFrame(
            {
                "publicID": ["event-1"],
                "magnitude": [4.5],
                "Observations": ["High magnitude"],
            }
        )

        runner._cm.config_data["output"] = {
            "file_format": file_format,
            "file_path": file_name,
        }

        saved_path = runner._save_output(output)

        assert saved_path.exists()

        actual = reader(saved_path)

        pd.testing.assert_frame_equal(actual, output)

    def test_save_output_writes_excel(
        self,
        runner: Runner,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """Test that _save_output writes the output DataFrame to an Excel file when the [output] configuration specifies"""
        pytest.importorskip("openpyxl")
        monkeypatch.chdir(tmp_path)

        output = pd.DataFrame(
            {
                "publicID": ["event-1"],
                "magnitude": [4.5],
                "Observations": ["High magnitude"],
            }
        )

        runner._cm.config_data["output"] = {
            "file_format": "excel",
            "file_path": "review.xlsx",
        }

        saved_path = runner._save_output(output)

        assert saved_path == tmp_path / "review.xlsx"
        assert saved_path.exists()

        actual = pd.read_excel(saved_path)

        pd.testing.assert_frame_equal(
            actual,
            output,
            check_dtype=False,
        )

    def test_save_output_rejects_unsupported_format_at_writer_boundary(
        self,
        runner: Runner,
    ):
        """Test that _save_output raises a ValueError when the [output] configuration specifies an unsupported file format."""
        output = pd.DataFrame(
            {
                "publicID": ["event-1"],
                "Observations": ["High magnitude"],
            }
        )

        runner._cm.config_data["output"] = {
            "file_format": "xml",
            "file_path": "review.xml",
        }

        with pytest.raises(ValueError, match="Unsupported output format"):
            runner._save_output(output)


class TestRunnerRun:
    """Tests for complete orchestration decisions in Runner.run()."""

    def test_run_uses_all_queries_when_multi_query_is_enabled_without_name(
        self,
        runner: Runner,
        monkeypatch: pytest.MonkeyPatch,
        events_df: pd.DataFrame,
    ):
        """Test that run() fetches all configured queries when multi_query is True and no query_name is provided,
        and does not call _fetch_single_query."""
        runner._cm.get_event_type_column = Mock(return_value="event_type")
        runner._cm.get_polygons = Mock(return_value=[])
        runner._cm.get_checks = Mock(return_value=[])
        runner._cm.config_data["duplicates"] = []
        runner._cm.config_data["output"] = {"save": False}

        runner._fetch_all_queries = Mock(return_value=events_df)
        runner._fetch_single_query = Mock()

        expected_output = pd.DataFrame(
            {
                "publicID": ["event-1"],
                "Observations": ["High magnitude"],
            }
        )
        runner._apply_output_selection = Mock(return_value=expected_output)
        runner._save_output = Mock()

        load_polygons_mock = Mock(return_value={})
        monkeypatch.setattr(
            runner_module,
            "load_polygons",
            load_polygons_mock,
        )

        result = runner.run(
            multi_query=True,
            perform_duplicates=False,
            perform_checks=False,
        )

        runner._fetch_all_queries.assert_called_once_with()
        runner._fetch_single_query.assert_not_called()
        runner._save_output.assert_not_called()

        assert isinstance(result, RunResult)
        pd.testing.assert_frame_equal(result.total_events, events_df)
        assert result.duplicates.empty
        assert result.checks.empty
        pd.testing.assert_frame_equal(result.output, expected_output)

    def test_run_uses_single_query_when_name_is_provided(
        self,
        runner: Runner,
        monkeypatch: pytest.MonkeyPatch,
        events_df: pd.DataFrame,
    ):
        """Test that run() fetches a single query when query_name is provided, and does not call _fetch_all_queries."""
        runner._cm.get_event_type_column = Mock(return_value="event_type")
        runner._cm.get_polygons = Mock(return_value=[])
        runner._cm.get_checks = Mock(return_value=[])
        runner._cm.config_data["duplicates"] = []
        runner._cm.config_data["output"] = {"save": False}

        runner._fetch_all_queries = Mock()
        runner._fetch_single_query = Mock(return_value=events_df)
        runner._apply_output_selection = Mock(return_value=events_df)
        runner._save_output = Mock()

        monkeypatch.setattr(
            runner_module,
            "load_polygons",
            Mock(return_value={}),
        )

        result = runner.run(
            query_name="events_sc6",
            multi_query=True,
            perform_duplicates=False,
            perform_checks=False,
            sql_text_override="SELECT * FROM events",
            sql_params={"limit": 10},
        )

        runner._fetch_all_queries.assert_not_called()

        runner._fetch_single_query.assert_called_once_with(
            query_name="events_sc6",
            sql_text_override="SELECT * FROM events",
            sql_params={"limit": 10},
        )

        assert result.output is events_df

    def test_run_executes_duplicates_checks_and_saves_when_enabled(
        self,
        runner: Runner,
        monkeypatch: pytest.MonkeyPatch,
        events_df: pd.DataFrame,
    ):
        """Test that run() executes duplicates and checks when enabled, and saves the output when configured."""
        duplicates_cfg = [{"name": "nearby_events"}]
        checks_cfg = [{"name": "high_magnitude"}]

        duplicate_result = pd.DataFrame(
            {"Observations": ["Possible duplicate"]},
            index=[0],
        )
        check_result = pd.DataFrame(
            {"Observations": ["High magnitude"]},
            index=[2],
        )
        output = pd.DataFrame(
            {
                "publicID": ["event-1", "event-3"],
                "Observations": [
                    "Possible duplicate",
                    "High magnitude",
                ],
            }
        )

        runner._cm.get_event_type_column = Mock(return_value="event_type")
        runner._cm.get_polygons = Mock(return_value=[{"name": "zone_a"}])
        runner._cm.get_checks = Mock(return_value=checks_cfg)
        runner._cm.config_data["duplicates"] = duplicates_cfg
        runner._cm.config_data["output"] = {"save": True}

        runner._fetch_all_queries = Mock(return_value=events_df)
        runner._apply_output_selection = Mock(return_value=output)
        runner._save_output = Mock()

        load_polygons_mock = Mock(return_value={"zone_a": Mock()})
        duplicates_mock = Mock(return_value=duplicate_result)
        checks_mock = Mock(return_value=check_result)

        monkeypatch.setattr(
            runner_module,
            "load_polygons",
            load_polygons_mock,
        )
        monkeypatch.setattr(
            runner_module,
            "run_duplicates",
            duplicates_mock,
        )
        monkeypatch.setattr(
            runner_module,
            "run_checks",
            checks_mock,
        )

        result = runner.run()

        duplicates_mock.assert_called_once_with(events_df, duplicates_cfg)

        checks_mock.assert_called_once_with(
            events=events_df,
            checks=checks_cfg,
            polygon_cache={"zone_a": load_polygons_mock.return_value["zone_a"]},
            event_type_col="event_type",
        )

        runner._apply_output_selection.assert_called_once_with(
            events=events_df,
            checks=check_result,
            dups=duplicate_result,
        )

        runner._save_output.assert_called_once_with(output)

        pd.testing.assert_frame_equal(result.duplicates, duplicate_result)
        pd.testing.assert_frame_equal(result.checks, check_result)
        pd.testing.assert_frame_equal(result.output, output)

    def test_run_skips_duplicates_when_disabled(
        self,
        runner: Runner,
        monkeypatch: pytest.MonkeyPatch,
        events_df: pd.DataFrame,
    ):
        """Test that run() skips duplicates when perform_duplicates is False, even if duplicates are configured."""
        runner._cm.get_event_type_column = Mock(return_value="event_type")
        runner._cm.get_polygons = Mock(return_value=[])
        runner._cm.get_checks = Mock(return_value=[])
        runner._cm.config_data["duplicates"] = [{"name": "nearby_events"}]
        runner._cm.config_data["output"] = {"save": False}

        runner._fetch_all_queries = Mock(return_value=events_df)
        runner._apply_output_selection = Mock(return_value=events_df)

        duplicates_mock = Mock()
        monkeypatch.setattr(
            runner_module,
            "load_polygons",
            Mock(return_value={}),
        )
        monkeypatch.setattr(
            runner_module,
            "run_duplicates",
            duplicates_mock,
        )

        result = runner.run(
            perform_duplicates=False,
            perform_checks=False,
        )

        duplicates_mock.assert_not_called()
        assert result.duplicates.empty

    def test_run_skips_checks_when_disabled(
        self,
        runner: Runner,
        monkeypatch: pytest.MonkeyPatch,
        events_df: pd.DataFrame,
    ):
        """Test that run() skips checks when perform_checks is False, even if checks are configured."""
        runner._cm.get_event_type_column = Mock(return_value="event_type")
        runner._cm.get_polygons = Mock(return_value=[])
        runner._cm.get_checks = Mock(
            return_value=[{"name": "high_magnitude"}]
        )
        runner._cm.config_data["duplicates"] = []
        runner._cm.config_data["output"] = {"save": False}

        runner._fetch_all_queries = Mock(return_value=events_df)
        runner._apply_output_selection = Mock(return_value=events_df)

        checks_mock = Mock()
        monkeypatch.setattr(
            runner_module,
            "load_polygons",
            Mock(return_value={}),
        )
        monkeypatch.setattr(
            runner_module,
            "run_checks",
            checks_mock,
        )

        result = runner.run(
            perform_duplicates=False,
            perform_checks=False,
        )

        checks_mock.assert_not_called()
        assert result.checks.empty


if __name__ == "__main__":
    pytest.main()
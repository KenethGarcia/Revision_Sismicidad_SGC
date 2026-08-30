# Author: Garcia-Cifuentes, K. <ORCID:0009-0001-2607-6359>
#
# --------------------------------------------------------------------------------------------------------
# High-level configuration validator for the project. It checks the validity of the configuration file and
# ensures that all required parameters are present and correctly formatted.
# --------------------------------------------------------------------------------------------------------
from __future__ import annotations

from typing import Any
from pathlib import Path

from src.checks.dispatchers import CONDITION_DISPATCHERS
from src.core.config_loader import ConfigManager, DEFAULT_DATABASE_NAME


class ConfigValidator:
    """Validate cross-section rules in a TOML configuration."""

    _VALID_LOGIC = {"and", "or", "xor"}
    _VALID_DUPLICATE_METHODS = {"adjacent", "sswa"}

    def __init__(self, config_manager: ConfigManager) -> None:
        self._cm = config_manager

    def validate(self) -> None:
        """Run every static validation and raise on the first error."""
        self._validate_databases()


    # [[database]]
    def _validate_databases(self) -> None:
        """
        Validate database-profile naming and static credential declarations.

        One sole profile may omit name and is internally represented as
        DEFAULT_DATABASE_NAME. Multiple profiles require distinct, explicit
        names because queries must route to a profile unambiguously.
        """
        databases = self._cm.get_database()

        if not databases:
            raise ValueError(
                f"No [[database]] entries found in "
                f"{self._cm.config_path.name!r}."
            )

        multiple_databases = len(databases) > 1
        seen_names: set[str] = set()

        for index, database in enumerate(databases, start=1):
            context = f"[[database]] entry #{index}"
            raw_name = database.get("name")

            if raw_name is None:
                if multiple_databases:
                    raise ValueError(
                        f"{context} in {self._cm.config_path.name!r} is "
                        "missing 'name'. Every profile needs a name when "
                        "multiple databases are configured."
                    )

                profile_name = DEFAULT_DATABASE_NAME
            else:
                profile_name = self._require_nonempty_string(
                    raw_name,
                    field="name",
                    context=context,
                )

                if profile_name == DEFAULT_DATABASE_NAME:
                    raise ValueError(
                        f"{context}: name {DEFAULT_DATABASE_NAME!r} is "
                        "reserved for one unnamed database profile."
                    )

            if profile_name in seen_names:
                raise ValueError(
                    f"{context}: duplicate database name {profile_name!r}. "
                    "Database names must be unique."
                )

            seen_names.add(profile_name)

            has_env_file = "env_file" in database
            has_env_prefix = "env_prefix" in database
            direct_keys = {"host", "user", "password", "database"}
            provided_direct_keys = direct_keys.intersection(database)

            if has_env_file:
                self._require_nonempty_string(
                    database["env_file"],
                    field="env_file",
                    context=context,
                )

            if has_env_prefix:
                self._require_nonempty_string(
                    database["env_prefix"],
                    field="env_prefix",
                    context=context,
                )

            if provided_direct_keys:
                missing_direct_keys = direct_keys - provided_direct_keys

                if missing_direct_keys:
                    missing = ", ".join(sorted(missing_direct_keys))
                    raise ValueError(
                        f"{context}: direct credentials are incomplete; missing {missing}."
                    )

                for key in sorted(direct_keys):
                    self._require_nonempty_string(
                        database[key],
                        field=key,
                        context=context,
                    )

            if not has_env_file and not has_env_prefix and not provided_direct_keys:
                raise ValueError(
                    f"{context}: provide credentials through 'env_file', 'env_prefix', "
                    f"or direct host/user/password/database keys."
                )

            if "port" in database:
                self._require_positive_integer(
                    database["port"],
                    field="port",
                    context=context,
                )

    # queries
    def _validate_queries(self) -> None:
        """Validate query names, SQL references, skip values, and DB routing."""
        queries = self._cm.get_queries()

        if not queries:
            raise ValueError(
                f"No [[queries]] entries found in {self._cm.config_path.name!r}."
            )

        databases = self._cm.get_database()
        database_names = self._database_names()
        multiple_databases = len(databases) > 1
        seen_query_names: set[str] = set()

        for index, query in enumerate(queries, start=1):
            context = f"[[queries]] entry #{index}"

            name = self._require_nonempty_string(
                query.get("name"),
                field="name",
                context=context,
            )

            if name in seen_query_names:
                raise ValueError(
                    f"{context}: duplicate query name {name!r}. Query names must be unique."
                )

            seen_query_names.add(name)

            self._require_nonempty_string(
                query.get("sql_file"),
                field="sql_file",
                context=context,
            )

            if "skip" in query and not isinstance(query["skip"], bool):
                raise ValueError(
                    f"{context}: skip must be a boolean."
                )

            raw_database = query.get("database")

            if raw_database is None:
                if multiple_databases and not query.get("skip", False):
                    raise ValueError(
                        f"{context} ({name!r}): database is required for every active query when multiple database "
                        f"profiles are configured."
                    )
                continue

            database_name = self._require_nonempty_string(
                raw_database,
                field="database",
                context=context,
            )

            if database_name not in database_names:
                available = ", ".join(
                    repr(item) for item in sorted(database_names)
                )
                raise ValueError(
                    f"{context} ({name!r}): database {database_name!r} "
                    f"is not defined. Available profiles: {available}."
                )

    def _database_names(self) -> set[str]:
        """Return the internal profile names implied by [[database]]."""
        databases = self._cm.get_database()

        if len(databases) == 1 and databases[0].get("name") is None:
            return {DEFAULT_DATABASE_NAME}

        names: set[str] = set()

        for database in databases:
            raw_name = database.get("name")

            if isinstance(raw_name, str) and raw_name.strip():
                names.add(raw_name.strip())

        return names

    # Polygons

    def _validate_polygons(self) -> None:
        """Validate polygon metadata without opening polygon files."""
        polygons = self._cm.get_polygons()
        seen_names: set[str] = set()

        for index, polygon in enumerate(polygons, start=1):
            context = f"[[polygons]] entry #{index}"

            name = self._require_nonempty_string(
                polygon.get("name"),
                field="name",
                context=context,
            )

            if name in seen_names:
                raise ValueError(
                    f"{context}: duplicate polygon name {name!r}. "
                    "Polygon names must be unique."
                )

            seen_names.add(name)

            self._require_nonempty_string(
                polygon.get("path"),
                field="path",
                context=context,
            )

            if "skip" in polygon and not isinstance(polygon["skip"], bool):
                raise ValueError(
                    f"{context}: skip must be a boolean."
                )

            if "polygon_type" in polygon:
                self._require_nonempty_string(
                    polygon["polygon_type"],
                    field="polygon_type",
                    context=context,
                )

    # Duplicates
    def _validate_duplicates(self) -> None:
        """Validate duplicate-rule structure without running detection."""
        duplicates = self._cm.config_data.get("duplicates", [])

        if duplicates is None:
            return

        if not isinstance(duplicates, list):
            raise TypeError(
                "Expected 'duplicates' to be an array of tables ([[duplicates]])."
            )

        for index, rule in enumerate(duplicates, start=1):
            if not isinstance(rule, dict):
                raise TypeError(
                    f"[[duplicates]] entry #{index} must be a TOML table."
                )

            context = f"[[duplicates]] entry #{index}"

            if "name" in rule:
                self._require_nonempty_string(
                    rule["name"],
                    field="name",
                    context=context,
                )

            method = rule.get("method", "adjacent")

            if method not in self._VALID_DUPLICATE_METHODS:
                allowed = ", ".join(sorted(self._VALID_DUPLICATE_METHODS))
                raise ValueError(
                    f"{context}: method must be one of {allowed}; got {method!r}."
                )

            self._require_positive_number(
                rule.get("time_window"),
                field="time_window",
                context=context,
            )

            self._require_positive_number(
                rule.get("dist_threshold"),
                field="dist_threshold",
                context=context,
            )

            if "subset" in rule:
                self._require_list_of_nonempty_strings(
                    rule["subset"],
                    field="subset",
                    context=context,
                )

            if "event_type" in rule:
                self._validate_string_or_string_list(
                    rule["event_type"],
                    field="event_type",
                    context=context,
                )


    # Helpers
    @staticmethod
    def _require_nonempty_string(
            value: Any,
            *,
            field: str,
            context: str,
    ) -> str:
        """Return a stripped nonempty string or raise ValueError."""
        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                f"{context}: {field} must be a nonempty string."
            )
        return value.strip()

    @staticmethod
    def _require_number(
            value: Any,
            *,
            field: str,
            context: str,
    ) -> float | int:
        """Require a non-boolean numeric value."""
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(
                f"{context}: {field} must be a number."
            )

        return value

    @classmethod
    def _require_positive_number(
            cls,
            value: Any,
            *,
            field: str,
            context: str,
    ) -> float | int:
        """Require a numeric value greater than zero."""
        number = cls._require_number(
            value,
            field=field,
            context=context,
        )

        if number <= 0:
            raise ValueError(
                f"{context}: {field} must be greater than zero."
            )

        return number

    @classmethod
    def _require_positive_integer(
            cls,
            value: Any,
            *,
            field: str,
            context: str,
    ) -> int:
        """Require a positive integer value, excluding booleans."""
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(
                f"{context}: {field} must be a positive integer."
            )

        if value <= 0:
            raise ValueError(
                f"{context}: {field} must be greater than zero."
            )

        return value

    @classmethod
    def _require_list_of_nonempty_strings(
            cls,
            value: Any,
            *,
            field: str,
            context: str,
    ) -> list[str]:
        """Require a nonempty list containing only nonempty strings."""
        if not isinstance(value, list) or not value:
            raise ValueError(
                f"{context}: {field} must be a nonempty list of strings."
            )

        return [
            cls._require_nonempty_string(
                item,
                field=field,
                context=context,
            )
            for item in value
        ]

    @classmethod
    def _as_nonempty_string_list(
            cls,
            value: Any,
            *,
            field: str,
            context: str,
    ) -> list[str]:
        """Accept either one nonempty string or a nonempty list of them."""
        if isinstance(value, str):
            return [
                cls._require_nonempty_string(
                    value,
                    field=field,
                    context=context,
                )
            ]

        return cls._require_list_of_nonempty_strings(
            value,
            field=field,
            context=context,
        )

    @classmethod
    def _validate_string_or_string_list(
            cls,
            value: Any,
            *,
            field: str,
            context: str,
    ) -> None:
        """Require either one nonempty string or a nonempty list of strings."""
        cls._as_nonempty_string_list(
            value,
            field=field,
            context=context,
        )
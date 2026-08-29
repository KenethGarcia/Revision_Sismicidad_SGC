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
from src.core.config_loader import ConfigManager


class ConfigValidator:
    """Validate cross-section rules in a TOML configuration."""

    _VALID_LOGIC = {"and", "or", "xor"}
    _VALID_DUPLICATE_METHODS = {"adjacent", "sswa"}

    def __init__(self, config_manager: ConfigManager) -> None:
        self._cm = config_manager

    def validate(self) -> None:
        """Run every static validation and raise on the first error."""
        self._validate_database_names()


    # [[database]]
    def _validate_database_names(self) -> None:
        """
        Require at least one uniquely named database profile.

        DatabaseManager builds a name-to-credentials mapping and routes
        queries by these names, so missing or duplicate names are invalid.
        """
        databases = self._cm.get_database()

        if not databases:
            raise ValueError(
                f"No [[database]] entries found in {self._cm.config_path.name!r}."
            )

        seen: set[str] = set()

        for index, database in enumerate(databases, start=1):
            context = f"[[database]] entry #{index}"

            name = self._require_nonempty_string(
                database.get("name"),
                field="name",
                context=context,
            )

            if name in seen:
                raise ValueError(
                    f"{context}: duplicate database name {name!r}. "
                    "Database names must be unique."
                )

            seen.add(name)

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
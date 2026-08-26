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
    """Run every static validation and raise on the first error found."""


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

    def __init__(self, config_manager: ConfigManager) -> None:
        self._cm = config_manager

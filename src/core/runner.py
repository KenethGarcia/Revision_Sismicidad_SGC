# Author: Garcia-Cifuentes, K. <ORCID:0009-0001-2607-6359>
#
# --------------------------------------------------------------------------------------------------------
# High-level runner class for seismic revision routines. It performs the following actions from TOML file:
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

from src.core.config_loader import ConfigManager
from src.core.database_manager import DatabaseManager
from src.io.sql import load_sql
from src.io.polygons import load_polygons
from src.checks.duplicates import check_duplicates_adjacent, check_duplicates_sswa
from src.checks.dispatchers import CONDITION_DISPATCHERS


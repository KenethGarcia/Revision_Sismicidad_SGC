# Author: Garcia-Cifuentes, K. <ORCID:0009-0001-2607-6359>

# --------------------------------------------------------------------------------------------------------
# This file contains functions to test load_credentials function
# --------------------------------------------------------------------------------------------------------
import os
import pytest
from pathlib import Path

from src.io.env import (
    load_credentials,
    _resolve
)

# Adjust these paths to your repo layout if needed.
REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_ENV = REPO_ROOT / "src" / "data" / "credentials" / "example.env"
@pytest.mark.skipif(not EXAMPLE_ENV.exists(), reason="example.env not found")


def test_load_credentials():
    pass

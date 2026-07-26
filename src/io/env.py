# Author: Garcia-Cifuentes, K. <ORCID:0009-0001-2607-6359>

# --------------------------------------------------------------------------------------------------------
# This file contains functions to read .env files with database credentials
# --------------------------------------------------------------------------------------------------------
import os
import warnings
from pathlib import Path
from dotenv import dotenv_values


def load_credentials(
    db_cfg:           dict,
    base_dir:         Path,
    config_name:      str,
    credentials_keys: tuple[str, str, str, str, str],
) -> dict:
    """
    Resolve database credentials from (in priority order):
        1. Live os.environ variables
        2. The declared .env file
        3. Inline values in the TOML [database] section

    Parameters
    ----------
    db_cfg : dict
        Parsed contents of the TOML [database] section.
    base_dir : Path
        Directory of the TOML file, used to resolve relative env_file paths.
    config_name : str
        TOML filename, used only for error messages.
    credentials_keys : tuple[str, str, str, str, str]
        Ordered key names for (host, user, password, database, port).

    Returns
    -------
    dict with keys: host, port, user, password, database.

    Raises
    ------
    FileNotFoundError  – env_file declared but not found on disk.
    KeyError           – required credential absent from all sources.
    TypeError          – a credentials_key is not a string, or port is
                         not coercible to int.
    ValueError         – port is outside the valid 1–65535 range.
    """

    # ── Validate credentials_keys types upfront ────────────────────
    key_labels = ("HOST", "USER", "PWD", "DB", "PORT")
    for i, key in enumerate(credentials_keys):
        if not isinstance(key, str):
            raise TypeError(
                f"{key_labels[i]} key must be a string, "
                f"got {key!r} (type: {type(key).__name__})"
            )

    # ── Load .env file if declared ─────────────────────────────────
    env_values:    dict[str, str] = {}
    env_file_path: Path | None    = None

    raw_env = db_cfg.get("env_file")
    if raw_env is not None:
        env_file_path = Path(raw_env)
        if not env_file_path.is_absolute():
            env_file_path = (base_dir / env_file_path).resolve()

        if not env_file_path.exists():
            raise FileNotFoundError(
                f"env_file declared in {config_name!r} was not found: "
                f"{env_file_path}\n"
                "Either create the file, fix the path, or remove the "
                "'env_file' key and supply credentials directly in [database]."
            )

        env_values = dotenv_values(env_file_path)   # does NOT mutate os.environ

        if not env_values:
            warnings.warn(
                f"The env_file at {env_file_path} was found but appears to be "
                "empty. Falling back to inline TOML credentials.",
                stacklevel=3,
            )
    else:
        warnings.warn(
            f"No 'env_file' declared in [database] of {config_name!r}. "
            "Reading credentials from the TOML file directly. "
            "Avoid committing plaintext passwords to version control.",
            stacklevel=3,
        )

    # ── Inner resolver — priority chain per key ────────────────────
    def _resolve(key: str, *, required: bool = True, default=None):
        # 1. Live process environment (uppercase by convention)
        value = os.environ.get(key.upper()) or os.environ.get(key)
        if value is not None:
            return value
        # 2. .env file
        value = env_values.get(key.upper()) or env_values.get(key)
        if value is not None:
            return value
        # 3. Inline TOML [database] section
        value = db_cfg.get(key)
        if value is not None:
            return value
        # 4. Fallback or error
        if required:
            sources = []
            if env_file_path:
                sources.append(f"env_file ({env_file_path.name})")
            sources.append(f"[database] in {config_name}")
            sources.append("os.environ")
            raise KeyError(
                f"Required credential {key!r} was not found in any of: "
                + ", ".join(sources)
            )
        return default

    # ── Resolve individual credentials ─────────────────────────────
    host     = _resolve(credentials_keys[0], required=True)
    user     = _resolve(credentials_keys[1], required=True)
    password = _resolve(credentials_keys[2], required=True)
    database = _resolve(credentials_keys[3], required=True)
    port_raw = _resolve(credentials_keys[4], required=False, default=3306)

    # Port coercion — env/os.environ always deliver strings, TOML delivers int
    try:
        port = int(port_raw)
    except (TypeError, ValueError):
        raise TypeError(
            f"'port' must be an integer, got {port_raw!r} "
            f"(type: {type(port_raw).__name__}). "
            "Check the value in your env_file or [database] section."
        )
    if not (1 <= port <= 65535):
        raise ValueError(
            f"'port' value {port} is outside the valid range 1–65535."
        )

    return {
        "host":     host,
        "port":     port,
        "user":     user,
        "password": password,
        "database": database,
    }
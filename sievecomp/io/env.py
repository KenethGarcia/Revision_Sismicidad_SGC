# Author: Garcia-Cifuentes, K. <ORCID:0009-0001-2607-6359>

# --------------------------------------------------------------------------------------------------------
# This file contains functions to read .env files with database credentials
# --------------------------------------------------------------------------------------------------------
from __future__ import annotations
import os
import warnings
from pathlib import Path
from typing import Mapping
from dotenv import dotenv_values


def load_credentials(
    db_cfg: Mapping[str, object],
    base_dir: Path,
    config_name: str,
) -> dict:
    """
    Resolve database credentials for a single database profile from
    (in priority order):
    1. The declared env_file
    2. Inline values in the TOML [[databases]] entry
    3. Live os.environ variables (with optional env_prefix)

    This function assumes db_cfg comes from one [[databases]] table:

        [[databases]]
        name       = "sc6"
        env_file   = ".env"         # optional
        env_prefix = "SERVERSC6"    # optional
        host       = "localhost"    # optional override
        user       = "username"
        password   = "password"
        database   = "seiscomp6"
        port       = 3306

    Parameters
    ----------
    db_cfg : Mapping[str, object]
        Parsed contents of one [[databases]] entry from the TOML file.
    base_dir : Path
        Directory of the TOML file, used to resolve relative env_file paths.
    config_name : str
        TOML filename, used only for error messages.

    Returns
    -------
    dict
        Credentials dict with keys: host, port, user, password, database.

    Raises
    ------
    FileNotFoundError
        env_file declared but not found on disk.
    KeyError
        Required credential absent from all sources.
    TypeError
        Port is not coercible to int.
    ValueError
        Port is outside the valid 1–65535 range.
    """
    # Optional profile name for error messages
    profile_name = db_cfg.get("name", "")

    # Optional env_prefix to distinguish multiple profiles in a single .env/os.environ
    env_prefix = db_cfg.get("env_prefix")
    if env_prefix is not None:
        env_prefix = str(env_prefix).strip()
        if not env_prefix:
            warnings.warn(
                f"Empty env_prefix declared for database profile {profile_name!r} "
                f"in {config_name!r}. It will be ignored.",
                stacklevel=3,
            )
            env_prefix = None

    # ── Load .env file if declared ─────────────────────────────────
    env_values: dict[str, str] = {}
    env_file_path: Path | None = None

    raw_env_file = db_cfg.get("env_file")
    if raw_env_file is not None:
        env_file_path = Path(raw_env_file)
        if not env_file_path.is_absolute():
            env_file_path = (base_dir / env_file_path).resolve()

        if not env_file_path.exists():
            raise FileNotFoundError(
                f"env_file declared in {config_name!r} for profile {profile_name!r} "
                f"was not found: {env_file_path}\n"
                "Either create the file, fix the path, or remove the "
                "'env_file' key and supply credentials directly in [[databases]]."
            )

        env_values = dotenv_values(env_file_path)  # does NOT mutate os.environ

        if not env_values:
            warnings.warn(
                f"The env_file at {env_file_path} (profile {profile_name!r}) "
                "was found but appears to be empty. "
                "Falling back to inline TOML credentials.",
                stacklevel=3,
            )
    else:
        warnings.warn(
            f"No 'env_file' declared in [[databases]] profile {profile_name!r} "
            f"of {config_name!r}. Reading credentials from the TOML entry "
            "and/or process environment. Avoid committing plaintext "
            "passwords to version control.",
            stacklevel=3,
        )

    # ── Resolve individual credentials ─────────────────────────────
    host = _resolve(
        key="host",
        db_cfg=db_cfg,
        env_values=env_values,
        env_file_path=env_file_path,
        env_prefix=env_prefix,
        profile_name=profile_name,
        config_name=config_name,
        required=True,
    )
    user = _resolve(
        key="user",
        db_cfg=db_cfg,
        env_values=env_values,
        env_file_path=env_file_path,
        env_prefix=env_prefix,
        profile_name=profile_name,
        config_name=config_name,
        required=True,
    )
    password = _resolve(
        key="password",
        db_cfg=db_cfg,
        env_values=env_values,
        env_file_path=env_file_path,
        env_prefix=env_prefix,
        profile_name=profile_name,
        config_name=config_name,
        required=True,
    )
    database = _resolve(
        key="database",
        db_cfg=db_cfg,
        env_values=env_values,
        env_file_path=env_file_path,
        env_prefix=env_prefix,
        profile_name=profile_name,
        config_name=config_name,
        required=True,
    )
    port_raw = _resolve(
        key="port",
        db_cfg=db_cfg,
        env_values=env_values,
        env_file_path=env_file_path,
        env_prefix=env_prefix,
        profile_name=profile_name,
        config_name=config_name,
        required=False,
        default=3306,
    )

    # Port coercion — env/os.environ always deliver strings,
    # TOML may deliver int.
    try:
        port = int(port_raw)
    except (TypeError, ValueError):
        raise TypeError(
            f"'port' must be an integer for profile {profile_name!r}, "
            f"got {port_raw!r} (type: {type(port_raw).__name__}). "
            "Check the value in your env_file or [[databases]] entry."
        )

    if not (1 <= port <= 65535):
        raise ValueError(
            f"'port' value {port} for profile {profile_name!r} "
            "is outside the valid range 1–65535."
        )

    return {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "database": database,
    }


def _resolve(
    key: str,
    *,
    db_cfg: Mapping[str, object],
    env_values: Mapping[str, str],
    env_file_path: Path | None,
    env_prefix: str | None,
    profile_name: str | object,
    config_name: str,
    required: bool = True,
    default=None,
):
    """
    Resolve a configuration value for a single key using the configured priority chain.

    Parameters
    ----------
    key : str
        The configuration key to resolve, such as a credential name like
        "host", "user", or "password".
    db_cfg : Mapping[str, object]
        Parsed contents of one [[databases]] entry from the TOML file.
    env_values : Mapping[str, str]
        Key-value pairs loaded from the declared env_file, if any.
    env_file_path : Path or None
        Path to the env_file on disk, or None if no env_file was declared.
    env_prefix : str or None
        Optional prefix used to build env variable names, such as "SERVERSC6".
        If provided, the resolver will look for variables like
        f"{env_prefix}_HOST" in addition to plain "HOST".
    profile_name : str
        Name of the database profile, used only for error messages.
    config_name : str
        TOML filename, used only for error messages.
    required : bool, default=True
        If True, raise an error when the key is not found in any source.
        If False, return `default` instead.
    default : Any, default=None
        Value to return when `required` is False and the key cannot be found.

    Returns
    -------
    Any
        The resolved value from the first available source in the following
        priority order:
        1. values from the `.env` file,
        2. inline TOML configuration entry.
        3. process environment variables,
        If no value is found and `required` is False, returns `default`.

    Raises
    ------
    KeyError
        If `required` is True and the key is not found in any supported source.
    """
    # Build candidate env variable names:
    env_keys: list[str] = []
    if env_prefix:
        env_keys.append(f"{env_prefix}_{key}".upper())
    env_keys.append(key.upper())
    env_keys.append(key)

    # 1. .env file
    for ek in env_keys:
        value = env_values.get(ek)
        if value is not None:
            return value

    # 2. Inline TOML entry (direct key)
    value = db_cfg.get(key)
    if value is not None:
        return value

    # 3. Live process environment
    for ek in env_keys:
        value = os.environ.get(ek)
        if value is not None:
            return value

    # 4. Fallback or error
    if required:
        sources = []
        if env_file_path:
            sources.append(f"env_file ({env_file_path.name})")
        sources.append(f"[[databases]] profile {profile_name} in {config_name}")
        sources.append("os.environ")
        raise KeyError(
            f"Required credential {key!r} for profile {profile_name!r} "
            f"was not found in any of: " + ", ".join(sources)
        )

    return default
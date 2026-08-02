# Author: Garcia-Cifuentes, K. <ORCID:0009-0001-2607-6359>

# --------------------------------------------------------------------------------------------------------
# This file contains a helper class to parse and expose structured views of [[databases]], [[queries]],
# [[polygons]], and [[checks]]
# --------------------------------------------------------------------------------------------------------
from __future__ import annotations
import tomllib
import warnings
from typing import Any
from pathlib import Path


class ConfigManager:
    """
    Load and expose structured access to the TOML configuration file.

    This class is responsible for:
    - Reading the TOML file once.
    - Tracking the base directory (for resolving relative paths).
    - Providing accessors for [[databases]], [[queries]], [[polygons]] and [[checks]].
    - Selecting a single query entry based on name and skip flags.
    """
    def __init__(self, config_path: Path):
        """
        Initialize the ConfigManager with a TOML configuration file.

        Parameters
        ----------
        config_path : Path
            Path to the TOML configuration file.
        """
        config_path = Path(config_path)
        if not config_path.exists():
            raise FileNotFoundError(f"{config_path} does not exist")
        if not config_path.is_file():
            raise ValueError(f"{config_path} is not a file")
        if config_path.suffix.lower() != ".toml":
            warnings.warn(
                f"Expected a .toml file but got {config_path.suffix!r}. "
                "Attempting to parse anyway.",
                stacklevel=2,
            )
        self._config_path: Path = config_path.resolve()
        self._base_dir: Path = config_path.parent
        with self._config_path.open("rb") as f:
            self._config_data: dict[str, Any] = tomllib.load(f)


    # Properties
    @property
    def config_path(self) -> Path:
        """Return the path to the TOML configuration file."""
        return self._config_path

    @property
    def base_dir(self) -> Path:
        """Return the base directory of the TOML configuration file."""
        return self._base_dir

    @property
    def config_data(self) -> dict[str, Any]:
        """Return the configuration data of the TOML configuration file."""
        return self._config_data


    # Getter methods
    def get_databases(self) -> list[dict]:
        """
        Return the list of database profiles defined in [[databases]].

        Returns
        -------
        list[dict]
            Each dict is one [[databases]] entry. Returns an empty list
            if no databases are defined.
        """
        dbs = self._config_data.get("databases", [])
        if dbs is None:
            return []
        if not isinstance(dbs, list):
            raise TypeError(
                "Expected 'databases' to be an array of tables ([[databases]]), "
                f"got {type(dbs).__name__!r}."
            )
        return dbs

    def get_queries(self) -> list[dict]:
        """
        Return the list of queries defined in [[queries]].

        Returns
        -------
        list[dict]
            Each dict is one [[queries]] entry. Returns an empty list
            if no queries are defined.
        """
        queries = self._config_data.get("queries", [])
        if queries is None:
            return []
        if not isinstance(queries, list):
            raise TypeError(
                "Expected 'queries' to be an array of tables ([[queries]]), "
                f"got {type(queries).__name__!r}."
            )
        return queries

    def get_checks(self) -> list[dict]:
        """
        Return the list of checks defined in [[checks]].

        Returns
        -------
        list[dict]
            Each dict is one [[checks]] entry. Returns an empty list
            if no checks are defined.
        """
        checks = self._config_data.get("checks", [])
        if checks is None:
            return []
        if not isinstance(checks, list):
            raise TypeError(
                "Expected 'checks' to be an array of tables ([[checks]]), "
                f"got {type(checks).__name__!r}."
            )
        return checks

    def get_polygons(self) -> list[dict]:
        """
        Return the list of polygons defined in [[polygons]].

        Returns
        -------
        list[dict]
            Each dict is one [[polygons]] entry. Returns an empty list
            if no polygons are defined.
        """
        polys = self._config_data.get("polygons", [])
        if polys is None:
            return []
        if not isinstance(polys, list):
            raise TypeError(
                "Expected 'polygons' to be an array of tables ([[polygons]]), "
                f"got {type(polys).__name__!r}."
            )
        return polys


    # Query selection
    def select_query(self, name: str | None = None) -> dict:
        """
        Select a single query configuration from [[queries]]. Used for handle multiple cases in [[queries]] semantics.

        Selection rules:
        - Queries with skip=true are ignored.
        - If `name` is provided, the query with that name must exist
          and must not be skipped; otherwise a ValueError is raised.
        - If `name` is None and there is exactly one active (non-skipped)
          query, that query is returned.
        - If `name` is None and there are zero active queries, a ValueError
          is raised.
        - If `name` is None and there are multiple active queries, a ValueError
          is raised asking the caller to specify a name.

        Parameters
        ----------
        name : str or None, default=None
            Name of the query to select. If None, selection falls back
            to the single active query if exactly one exists.

        Returns
        -------
        dict
            The selected [[queries]] entry.

        Raises
        ------
        ValueError
            If no suitable query can be selected.
        """
        queries = self.get_queries()
        active = [q for q in queries if not q.get("skip", False)]

        if name is not None:
            for q in active:
                if q.get("name") == name:
                    return q
            raise ValueError(
                f"No active query named {name!r} found in [[queries]] "
                f"of {self._config_path.name!r}."
            )

        # name is None: try to infer
        if not active:
            raise ValueError(
                f"No active queries defined in [[queries]] section of "
                f"{self._config_path.name!r}."
            )

        if len(active) == 1:
            return active[0]

        names = [q.get("name", "<unnamed>") for q in active]
        raise ValueError(
            "Multiple active queries defined in [[queries]]; "
            "please specify which one to use by name. "
            f"Available names: {', '.join(repr(n) for n in names)}."
        )


    # Helpers
    def default_database_name(self) -> str | None:
        """
        Return the default database profile name if unambiguous.

        Rules:
        - If exactly one [[databases]] entry exists, and it has a 'name'
          key, that name is returned.
        - If no databases or more than one database exist, returns None.

        Returns
        -------
        str or None
        """
        dbs = self.get_databases()
        if len(dbs) != 1:
            return None
        return str(dbs[0].get("name")) if "name" in dbs[0] else None
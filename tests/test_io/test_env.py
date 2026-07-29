# Author: Garcia-Cifuentes, K. <ORCID:0009-0001-2607-6359>

# --------------------------------------------------------------------------------------------------------
# This file contains functions to test load_credentials function
# --------------------------------------------------------------------------------------------------------
import os
import pytest
from pathlib import Path
from src.io.env import load_credentials, _resolve

# Adjust these paths to your repo layout if needed.
REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_ENV = REPO_ROOT / "src" / "data" / "credentials" / "example.env"


@pytest.mark.skipif(not EXAMPLE_ENV.exists(), reason="example.env not found")
class TestLoadCredentialsFromEnvFile:
    def setup_method(self):
        # Ensure process env doesn't interfere for these tests
        self._orig_environ = os.environ.copy()
        for k in list(os.environ.keys()):
            if k.startswith("SERVERSC6_") or k.startswith("SERVERSC3_"):
                os.environ.pop(k, None)


    def teardown_method(self):
        os.environ.clear()
        os.environ.update(self._orig_environ)


    def test_load_credentials_sc6_full_from_env_file(self, tmp_path: Path):
        """
        Profile sc6 with env_file and env_prefix, no inline overrides.
        Should read all values from example.env via dotenv_values.
        """
        db_cfg = {
            "name": "sc6",
            "env_file": str(EXAMPLE_ENV.relative_to(REPO_ROOT)),
            "env_prefix": "SERVERSC6",
        }
        base_dir = REPO_ROOT
        creds = load_credentials(db_cfg, base_dir=base_dir, config_name="example.toml")

        assert creds["host"] == "10.100.100.xxx"
        assert creds["user"] == "user"
        assert creds["password"] == "123"
        assert creds["database"] == "db"
        assert creds["port"] == 3306


    def test_load_credentials_sc3_full_from_env_file(self, tmp_path: Path):
        """
        Profile sc3 with env_file and env_prefix, no inline overrides.
        Should read all values from example.env via dotenv_values.
        """
        db_cfg = {
            "name": "sc3",
            "env_file": str(EXAMPLE_ENV.relative_to(REPO_ROOT)),
            "env_prefix": "SERVERSC3",
        }
        base_dir = REPO_ROOT
        creds = load_credentials(db_cfg, base_dir=base_dir, config_name="example.toml")

        assert creds["host"] == "10.100.100.yyy"
        assert creds["user"] == "user"
        assert creds["password"] == "456"
        assert creds["database"] == "db2"
        assert creds["port"] == 3306


    def test_env_file_beats_inline(self):
        """
        Inline the env_file should override values from host/user/password/database/port in db_cfg and env_prefix.
        """
        db_cfg = {
            "name": "sc6",
            "env_file": str(EXAMPLE_ENV.relative_to(REPO_ROOT)),
            "env_prefix": "SERVERSC6",
            "host": "inline-host",
            "user": "inline-user",
            "password": "inline-pwd",
            "database": "inline-db",
            "port": 5432,
        }
        base_dir = REPO_ROOT
        creds = load_credentials(db_cfg, base_dir=base_dir, config_name="example.toml")
        # Expect env_file to win:
        assert creds["host"] == "10.100.100.xxx"
        assert creds["user"] == "user"
        assert creds["password"] == "123"
        assert creds["database"] == "db"
        assert creds["port"] == 3306


    def test_empty_env_file_warns_and_uses_inline(self, tmp_path: Path, caplog):
        """
        When env_file exists but is empty, load_credentials should warn and
        fall back to inline TOML configuration.
        """
        empty_env = tmp_path / "empty.env"
        empty_env.write_text("", encoding="utf-8")

        db_cfg = {
            "name": "sc_empty",
            "env_file": str(empty_env.relative_to(tmp_path)),
            "env_prefix": "SERVERSC6",
            "host": "inline-host",
            "user": "inline-user",
            "password": "inline-pwd",
            "database": "inline-db",
            "port": 3306,
        }

        base_dir = tmp_path
        creds = load_credentials(db_cfg, base_dir=base_dir, config_name="example.toml")

        assert creds["host"] == "inline-host"
        assert creds["user"] == "inline-user"
        assert creds["password"] == "inline-pwd"
        assert creds["database"] == "inline-db"
        assert creds["port"] == 3306


    def test_missing_env_file_raises_FileNotFoundError(self, tmp_path: Path):
        """
        When env_file is declared but does not exist, load_credentials should raise FileNotFoundError.
        """
        db_cfg = {
            "name": "sc_missing",
            "env_file": "nonexistent.env",
            "env_prefix": "SERVERSC6",
        }
        base_dir = tmp_path
        with pytest.raises(FileNotFoundError):
            load_credentials(db_cfg, base_dir=base_dir, config_name="example.toml")


class TestLoadCredentialsWithoutEnvFile:
    def setup_method(self):
        # Start with a clean environment
        self._orig_environ = os.environ.copy()
        os.environ.clear()

    def teardown_method(self):
        os.environ.clear()
        os.environ.update(self._orig_environ)

    def test_no_env_file_uses_inline_and_warns(self, caplog):
        """
        When no env_file is declared, load_credentials should warn and use inline TOML configuration.
        """
        db_cfg = {
            "name": "sc_inline",
            # no env_file
            "host": "inline-host",
            "user": "inline-user",
            "password": "inline-pwd",
            "database": "inline-db",
            "port": 3306,
        }
        base_dir = Path(".")
        creds = load_credentials(db_cfg, base_dir=base_dir, config_name="example.toml")

        assert creds["host"] == "inline-host"
        assert creds["user"] == "inline-user"
        assert creds["password"] == "inline-pwd"
        assert creds["database"] == "inline-db"
        assert creds["port"] == 3306


    def test_missing_required_key_raises_KeyError(self):
        """
        When a required key (like host) is missing from all sources, load_credentials should raise KeyError.
        """
        db_cfg = {
            "name": "sc_missing_host",
            # host missing everywhere
            "user": "inline-user",
            "password": "inline-pwd",
            "database": "inline-db",
            "port": 3306,
        }
        base_dir = Path(".")
        with pytest.raises(KeyError):
            load_credentials(db_cfg, base_dir=base_dir, config_name="example.toml")

        db_cfg["host"] = "inline-host"
        db_cfg.pop("user")
        with pytest.raises(KeyError):
            load_credentials(db_cfg, base_dir=base_dir, config_name="example.toml")


    def test_port_default_and_range_check(self):
        """
        If port is absent, 3306 is used by default. If port is present but invalid, appropriate errors are raised.
        """
        base_dir = Path(".")

        # Default port (absent in all sources)
        db_cfg_default = {
            "name": "sc_default",
            "host": "inline-host",
            "user": "inline-user",
            "password": "inline-pwd",
            "database": "inline-db",
            # no port
        }
        creds_default = load_credentials(db_cfg_default, base_dir=base_dir, config_name="example.toml")
        assert creds_default["port"] == 3306

        # Non-integer port
        db_cfg_bad_port = {
            "name": "sc_bad_port",
            "host": "inline-host",
            "user": "inline-user",
            "password": "inline-pwd",
            "database": "inline-db",
            "port": "not-an-int",
        }
        with pytest.raises(TypeError):
            load_credentials(db_cfg_bad_port, base_dir=base_dir, config_name="example.toml")

        # Out-of-range port
        db_cfg_range_port = {
            "name": "sc_range_port",
            "host": "inline-host",
            "user": "inline-user",
            "password": "inline-pwd",
            "database": "inline-db",
            "port": 70000,
        }
        with pytest.raises(ValueError):
            load_credentials(db_cfg_range_port, base_dir=base_dir, config_name="example.toml")


class TestResolveHelperDirectly:
    def test_resolve_priority_env_file_first(self, monkeypatch):
        """
        When both os.environ and env_values have a key, env_values must win
        """
        db_cfg = {"host": "inline-host"}
        env_values = {"HOST": "env-file-host"}
        env_file_path = Path("example.env")
        env_prefix = None
        profile_name = "sc_test"
        config_name = "example.toml"

        monkeypatch.setenv("HOST", "process-env-host")

        value = _resolve(
            key="host",
            db_cfg=db_cfg,
            env_values=env_values,
            env_file_path=env_file_path,
            env_prefix=env_prefix,
            profile_name=profile_name,
            config_name=config_name,
            required=True,
        )
        assert value == "env-file-host"

    def test_resolve_with_env_prefix_builds_prefixed_keys(self, monkeypatch):
        """
        When env_prefix is set, _resolve should look for names like SERVERSC6_HOST before HOST.
        """
        db_cfg = {}
        env_values = {}
        env_file_path = None
        env_prefix = "SERVERSC6"
        profile_name = "sc6"
        config_name = "example.toml"

        monkeypatch.setenv("SERVERSC6_HOST", "prefixed-host")

        value = _resolve(
            key="host",
            db_cfg=db_cfg,
            env_values=env_values,
            env_file_path=env_file_path,
            env_prefix=env_prefix,
            profile_name=profile_name,
            config_name=config_name,
            required=True,
        )
        assert value == "prefixed-host"

    def test_resolve_required_missing_raises_KeyError(self):
        """
        When a required key is missing from all sources, _resolve should raise KeyError.
        """
        db_cfg = {}
        env_values = {}
        env_file_path = None
        env_prefix = None
        profile_name = "sc_missing"
        config_name = "example.toml"

        with pytest.raises(KeyError):
            _resolve(
                key="host",
                db_cfg=db_cfg,
                env_values=env_values,
                env_file_path=env_file_path,
                env_prefix=env_prefix,
                profile_name=profile_name,
                config_name=config_name,
                required=True,
            )

    def test_resolve_optional_missing_returns_default(self):
        """
        When a non-required key is missing from all sources, _resolve should return the default value.
        """
        db_cfg = {}
        env_values = {}
        env_file_path = None
        env_prefix = None
        profile_name = "sc_optional"
        config_name = "example.toml"

        value = _resolve(
            key="host",
            db_cfg=db_cfg,
            env_values=env_values,
            env_file_path=env_file_path,
            env_prefix=env_prefix,
            profile_name=profile_name,
            config_name=config_name,
            required=False,
            default="default-host",
        )
        assert value == "default-host"

if __name__ == "__main__":
    pytest.main()
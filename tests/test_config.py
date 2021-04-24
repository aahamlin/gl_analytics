from pathlib import Path

from gl_analytics.config import load_config
from tests import change_directory


def test_load_config_provides_defaults(tmp_path, monkeypatch):
    monkeypatch.delenv("TOKEN", raising=False)
    with change_directory(tmp_path):
        config = load_config()

    assert set(["GITLAB_BASE_URL", "GITLAB_GROUP"]).issubset(config.keys())
    assert "TOKEN" not in config, f"Found config['TOKEN'] {config['TOKEN']}"


def test_main_uses_dotenv(tmp_path, monkeypatch):
    """If running tests in test env there will not be a .env file.
    If there is a .env, this test is skipped.

    See also: test_requires_uses_user_token
    """
    monkeypatch.delenv("TOKEN", raising=False)
    with change_directory(tmp_path):
        tmp_filepath = Path(".env")
        with tmp_filepath.open(mode="w", encoding="utf-8") as f:
            f.write("TOKEN=test_token")

        assert tmp_filepath.exists()
        config = load_config()

    assert "TOKEN" in config
    assert config["TOKEN"] == "test_token"


def test_main_uses_osenv(tmp_path, monkeypatch):
    """If running tests in test env there will not be a .env file.
    If there is a .env, this test is skipped.

    See also: test_main_uses_user_token
    """
    monkeypatch.setenv("TOKEN", "os_test")

    with change_directory(tmp_path):
        config = load_config()

    assert "TOKEN" in config
    assert config["TOKEN"] == "os_test"

import pytest
from pathlib import Path

from gl_analytics.config import load_config


@pytest.mark.skipif(
    Path(".env").exists(), reason="Tests must not clobber user .env file"
)
def test_load_config_provides_defaults():
    config = load_config()
    assert set(["GITLAB_BASE_URL", "GITLAB_GROUP"]).issubset(config.keys())
    assert "TOKEN" not in config


@pytest.mark.skipif(
    Path(".env").exists(), reason="Tests must not clobber user .env file"
)
def test_main_uses_dotenv(filepath_dotenv):
    """If running tests in test env there will not be a .env file.
    If there is a .env, this test is skipped.

    See also: test_requires_uses_user_token
    """
    config = load_config()
    assert "TOKEN" in config
    assert config["TOKEN"] == "test_token"


@pytest.mark.skipif(
    Path(".env").exists(), reason="Tests must not clobber user .env file"
)
def test_main_uses_osenv(monkeypatch):
    """If running tests in test env there will not be a .env file.
    If there is a .env, this test is skipped.

    See also: test_main_uses_user_token
    """
    monkeypatch.setenv("TOKEN", "os_test")
    config = load_config()
    assert "TOKEN" in config
    assert config["TOKEN"] == "os_test"

import os
import pytest
from unittest.mock import patch
from pydantic import ValidationError
from app.config import Settings


def test_settings_loads_from_env():
    os.environ["DEEPSEEK_API_KEY"] = "test-deepseek-key"
    os.environ["TMDB_API_KEY"] = "test-tmdb-key"
    settings = Settings()
    assert settings.DEEPSEEK_API_KEY == "test-deepseek-key"
    assert settings.TMDB_API_KEY == "test-tmdb-key"
    assert settings.DEEPSEEK_BASE_URL == "https://api.deepseek.com/v1"
    assert settings.DEEPSEEK_MODEL == "deepseek-chat"
    assert settings.TMDB_BASE_URL == "https://api.themoviedb.org/3"


def test_settings_missing_required_key_raises():
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValidationError):
            Settings(_env_file=None)

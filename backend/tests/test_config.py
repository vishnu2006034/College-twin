import json

import pytest
from pydantic import ValidationError
from sqlalchemy.engine import make_url

from app import config


def test_local_configuration_builds_url_and_is_independent_of_cwd(tmp_path, monkeypatch):
    path = tmp_path / 'local-settings.json'
    password = 'test-only:p@ss/with#symbols'
    path.write_text(json.dumps({'database': {'password': password},
                                'app_origin': 'http://localhost:5173'}))
    monkeypatch.setattr(config, 'LOCAL_SETTINGS_PATH', path)
    monkeypatch.delenv('DATABASE_URL', raising=False)
    monkeypatch.delenv('APP_ORIGIN', raising=False)
    monkeypatch.chdir(tmp_path.parent)
    settings = config.Settings(_env_file=None)
    url = make_url(settings.database_url)
    assert url.password == password
    assert url.database == 'college_twin'
    assert url.username == 'postgres'
    assert settings.app_origin == 'http://localhost:5173'


def test_environment_overrides_local_database(tmp_path, monkeypatch):
    path = tmp_path / 'local-settings.json'
    path.write_text(json.dumps({'database': {'password': 'local-test-only'}}))
    monkeypatch.setattr(config, 'LOCAL_SETTINGS_PATH', path)
    monkeypatch.setenv('DATABASE_URL', 'postgresql+psycopg://test:override@localhost/test_db')
    assert make_url(config.Settings(_env_file=None).database_url).database == 'test_db'


def test_blank_local_password_does_not_invent_credentials(tmp_path, monkeypatch):
    path = tmp_path / 'local-settings.json'
    path.write_text(json.dumps({'database': {'password': ''}}))
    monkeypatch.setattr(config, 'LOCAL_SETTINGS_PATH', path)
    monkeypatch.delenv('DATABASE_URL', raising=False)
    with pytest.raises(ValidationError):
        config.Settings(_env_file=None)

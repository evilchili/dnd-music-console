from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    fixtures = Path(__file__).parent / 'fixtures'
    monkeypatch.setenv('CROAKER_ROOT', str(fixtures))
    monkeypatch.setenv('MEDIA_GLOB', '*.mp3,*.foo,*.bar')
    monkeypatch.setenv('ICECAST_URL', 'http://127.0.0.1')
    monkeypatch.setenv('ICECAST_HOST', 'localhost')
    monkeypatch.setenv('ICECAST_MOUNT', 'mount')
    monkeypatch.setenv('ICECAST_PORT', '6523')
    monkeypatch.setenv('ICECAST_PASSWORD', 'password')
    monkeypatch.setenv('DEBUG', '1')

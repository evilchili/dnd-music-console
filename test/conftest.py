from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    fixtures = Path(__file__).parent / 'fixtures'
    monkeypatch.setenv('CROAKER_ROOT', str(fixtures))
    monkeypatch.setenv('MEDIA_GLOB', '*.mp3,*.foo,*.bar')

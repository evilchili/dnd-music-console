from unittest.mock import MagicMock

import ffmpeg
import pytest

from croaker import playlist
from croaker import transcoder


@pytest.mark.parametrize('suffix, expected', [
    ('.mp3', b'_theme.mp3\n'),
    ('.foo', b'transcoding!\n'),
])
def test_transcoder_open(monkeypatch, suffix, expected):
    monkeypatch.setattr(transcoder, 'ffmpeg', MagicMock(spec=ffmpeg, **{
        'input.return_value.'
        'output.return_value.'
        'global_args.return_value.'
        'compile.return_value': ['echo', 'transcoding!'],
    }))

    pl = playlist.Playlist(name='test_playlist')
    track = [t for t in pl.tracks if t.suffix == suffix][0]
    with transcoder.open(track) as handle:
        assert handle.read() == expected

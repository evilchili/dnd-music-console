from unittest.mock import MagicMock

import ffmpeg
import pytest

from croaker import playlist, transcoder


@pytest.fixture
def mock_mp3decoder(monkeypatch):
    def read(stream):
        return stream.read()
    monkeypatch.setattr(transcoder, 'MP3Decoder', MagicMock(**{
        '__enter__.return_value.read': read
    }))


@pytest.mark.xfail
@pytest.mark.parametrize(
    "suffix, expected",
    [
        (".mp3", b"_theme.mp3\n"),
        (".foo", b"transcoding!\n"),
    ],
)
def test_transcoder_open(monkeypatch, mock_mp3decoder, suffix, expected):
    monkeypatch.setattr(
        transcoder,
        "ffmpeg",
        MagicMock(
            spec=ffmpeg,
            **{
                "input.return_value."
                "output.return_value."
                "global_args.return_value."
                "compile.return_value": ["echo", "transcoding!"],
            },
        ),
    )

    pl = playlist.Playlist(name="test_playlist")
    track = [t for t in pl.tracks if t.suffix == suffix][0]
    with transcoder.open(track) as handle:
        assert handle.read() == expected

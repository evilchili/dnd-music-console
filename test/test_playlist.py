from unittest.mock import MagicMock

import pytest

import croaker.path
import croaker.playlist


def test_playlist_loading():
    pl = croaker.playlist.Playlist(name="test_playlist")
    path = str(pl.path)
    tracks = [str(t) for t in pl.tracks]

    assert path == str(croaker.path.playlist_root() / pl.name)
    assert pl.name == "test_playlist"
    assert tracks[0] == f"{path}/_theme.mp3"
    assert f"{path}/one.mp3" in tracks
    assert f"{path}/two.mp3" in tracks
    assert f"{path}/one.foo" in tracks
    assert f"{path}/one.baz" not in tracks


@pytest.mark.parametrize(
    "paths, make_theme, expected_count",
    [
        (["test_playlist"], True, 4),
        (["test_playlist"], False, 4),
        (["test_playlist", "sources/one.mp3"], True, 5),
        (["test_playlist", "sources/one.mp3"], False, 5),
    ],
)
def test_playlist_creation(monkeypatch, paths, make_theme, expected_count):
    new_symlinks = []

    def symlink(target):
        new_symlinks.append(target)

    pl = croaker.playlist.Playlist(name="foo")
    monkeypatch.setattr(croaker.playlist.Path, "unlink", MagicMock())
    monkeypatch.setattr(croaker.playlist.Path, "symlink_to", MagicMock(side_effect=symlink))
    monkeypatch.setattr(croaker.playlist.Path, "mkdir", MagicMock())

    pl.add([croaker.path.playlist_root() / p for p in paths], make_theme)
    assert len(new_symlinks) == expected_count

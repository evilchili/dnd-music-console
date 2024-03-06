import os
from pathlib import Path

_setup_hint = "You may be able to solve this error by running 'croaker setup' or specifying the --root parameter."
_reinstall_hint = "You might need to reinstall Croaker to fix this error."


def root():
    return Path(os.environ.get("CROAKER_ROOT", "~/.dnd/croaker")).expanduser()


def cache_root():
    path = Path(os.environ.get("CACHE_ROOT", root() / "cache")).expanduser()
    return path


def playlist_root():
    path = Path(os.environ.get("PLAYLIST_ROOT", root() / "playlists")).expanduser()
    return path

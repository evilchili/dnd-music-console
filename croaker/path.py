import logging
import os
from pathlib import Path

from croaker.exceptions import ConfigurationError

_setup_hint = "You may be able to solve this error by running 'croaker setup' or specifying the --root parameter."
_reinstall_hint = "You might need to reinstall Groove On Demand to fix this error."


def root():
    return Path(os.environ.get("CROAKER_ROOT", "~/.dnd/croaker")).expanduser()


def media_root():
    path = os.environ.get("MEDIA_ROOT", None)
    if not path:
        raise ConfigurationError(f"MEDIA_ROOT is not defined in your environment.\n\n{_setup_hint}")
    path = Path(path).expanduser()
    if not path.exists() or not path.is_dir():
        raise ConfigurationError(
            "The media_root directory (MEDIA_ROOT) doesn't exist, or isn't a directory.\n\n{_setup_hint}"
        )
    logging.debug(f"Media root is {path}")
    return path


def cache_root():
    path = Path(os.environ.get("CACHE_ROOT", root() / Path("cache"))).expanduser()
    logging.debug(f"Media cache root is {path}")
    return path


def playlist_root():
    path = Path(os.environ.get("PLAYLIST_ROOT", root() / Path("playlsits"))).expanduser()
    logging.debug(f"Playlist root is {path}")
    return path


def media(relpath):
    path = media_root() / Path(relpath)
    return path


def transcoded_media(relpath):
    path = cache_root() / Path(relpath + ".webm")
    return path

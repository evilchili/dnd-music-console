import logging
import os
from pathlib import Path

_setup_hint = "You may be able to solve this error by running 'croaker setup' or specifying the --root parameter."
_reinstall_hint = "You might need to reinstall Groove On Demand to fix this error."


def root():
    return Path(os.environ.get("CROAKER_ROOT", "~/.dnd/croaker")).expanduser()


def cache_root():
    path = Path(os.environ.get("CACHE_ROOT", root() / Path("cache"))).expanduser()
    logging.debug(f"Media cache root is {path}")
    return path


def playlist_root():
    path = Path(os.environ.get("PLAYLIST_ROOT", root() / Path("playlsits"))).expanduser()
    logging.debug(f"Playlist root is {path}")
    return path


def transcoded_media(relpath):
    path = cache_root() / Path(relpath + ".webm")
    return path

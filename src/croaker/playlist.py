import logging
import os
from dataclasses import dataclass
from functools import cached_property
from itertools import chain
from pathlib import Path
from random import shuffle
from typing import List

import croaker.path

logger = logging.getLogger("playlist")

playlists = {}


def _stripped(name):
    name.replace('"', "")
    name.replace("'", "")
    return name


@dataclass
class Playlist:
    name: str
    theme: Path = Path("_theme.mp3")

    @cached_property
    def path(self):
        return self._get_path()

    @cached_property
    def tracks(self):
        if not self.path.exists():
            raise RuntimeError(f"Playlist {self.name} not found at {self.path}.")  # pragma: no cover

        entries = []
        theme = self.path / self.theme
        if theme.exists():
            entries.append(theme)
        files = [e for e in self.get_audio_files() if e.name != "_theme.mp3"]
        if files:
            shuffle(files)
            entries += files
        return entries

    def get_audio_files(self, path: Path = None):
        if not path:
            path = self.path
        logging.debug(f"Getting files matching {os.environ['MEDIA_GLOB']} from {path}")
        pats = os.environ["MEDIA_GLOB"].split(",")
        return chain(*[list(path.rglob(pat)) for pat in pats])

    def _get_path(self):
        return croaker.path.playlist_root() / self.name

    def _add_track(self, target: Path, source: Path):
        if target.exists():
            if not target.is_symlink():
                logging.warning(f"{target}: target already exists and is not a symlink; skipping.")
                return
            target.unlink()
        target.symlink_to(source)

    def add(self, paths: List[Path], make_theme: bool = False):
        logger.debug(f"Adding everything from {paths = }")
        self.path.mkdir(parents=True, exist_ok=True)
        for path in paths:
            if path.is_dir():
                files = list(self.get_audio_files(path))
                if make_theme:
                    logger.debug(f"Adding first file from dir as theme: {files[0] = }")
                    self._add_track(self.path / "_theme.mp3", files.pop(0))
                    make_theme = False
                for file in files:
                    logger.debug(f"Adding {file = }")
                    self._add_track(target=self.path / _stripped(file.name), source=file)
            elif make_theme:
                logger.debug(f"Adding path as theme: {path = }")
                self._add_track(self.path / "_theme.mp3", path)
                make_theme = False
            else:
                logger.debug(f"Adding {path = }")
                self._add_track(target=self.path / _stripped(path.name), source=path)
        return sorted(self.get_audio_files())

    def __repr__(self):
        lines = [f"Playlist {self.name}"]
        lines += [f" * {track}" for track in self.tracks]
        return "\n".join(lines)


def load_playlist(name: str):  # pragma: no cover
    if name not in playlists:
        playlists[name] = Playlist(name=name)
    return playlists[name]

import logging
import os
from dataclasses import dataclass
from functools import cached_property
from itertools import chain
from pathlib import Path
from random import shuffle
from typing import List

import croaker.path

logger = logging.getLogger('playlist')

playlists = {}

NowPlaying = None


def _stripped(name):
    name.replace('"', "")
    name.replace("'", "")
    return name


@dataclass
class Playlist:
    name: str
    position: int = 0
    theme: Path = Path("_theme.mp3")

    @property
    def current(self):
        return self.tracks[self.position]

    @cached_property
    def path(self):
        return croaker.path.playlist_root() / Path(self.name)

    @cached_property
    def tracks(self):
        if not self.path.exists():
            raise RuntimeError(f"Playlist {self.name} not found at {self.path}.")

        entries = []
        theme = self.path / self.theme
        if theme.exists():
            entries.append(theme)
        files = [e for e in self.get_audio_files() if e.name != "_theme.mp3"]
        if files:
            shuffle(files)
            entries += files
        return entries

    def skip(self):
        logging.debug(f"Skipping from {self.position} on {self.name}")
        if self.position == len(self.tracks) - 1:
            self.position = 0
        else:
            self.position += 1

    def get_audio_files(self, path: Path = None):
        if not path:
            path = self.path
        logging.debug(f"Getting files matching {os.environ['MEDIA_GLOB']} from {path}")
        pats = os.environ["MEDIA_GLOB"].split(",")
        return chain(*[list(path.glob(pat)) for pat in pats])

    def _add_track(self, target: Path, source: Path, make_theme: bool = False):
        if source.is_dir():
            for file in self.get_audio_files(source):
                self._add_track(self.path / _stripped(file.name), file)
            return
        if target.exists():
            if not target.is_symlink():
                logging.warning(f"{target}: target already exists and is not a symlink; skipping.")
                return
            target.unlink()
        target.symlink_to(source)

    def add(self, tracks: List[Path], make_theme: bool = False):
        self.path.mkdir(parents=True, exist_ok=True)
        if make_theme:
            target = self.path / "_theme.mp3"
            source = tracks.pop(0)
            self._add_track(target, source, make_theme=True)
        for track in tracks:
            self._add_track(target=self.path / _stripped(track.name), source=track)
        return sorted(self.get_audio_files())

    def __repr__(self):
        lines = [f"Playlist {self.name}"]
        lines += [f" * {track}" for track in self.tracks]
        return "\n".join(lines)


def load_playlist(name: str):
    if name not in playlists:
        playlists[name] = Playlist(name=name)
    return playlists[name]

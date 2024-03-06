import logging
import os
import threading
from functools import cached_property
from pathlib import Path
from time import sleep

import shout


class AudioStreamer(threading.Thread):
    def __init__(self, queue, skip_event, stop_event):
        super().__init__()
        self.queue = queue
        self.skip_requested = skip_event
        self.stop_requested = stop_event

    @cached_property
    def _shout(self):
        s = shout.Shout()
        s.name = "Croaker Radio"
        s.url = os.environ["ICECAST_URL"]
        s.mount = os.environ["ICECAST_MOUNT"]
        s.host = os.environ["ICECAST_HOST"]
        s.port = int(os.environ["ICECAST_PORT"])
        s.password = os.environ["ICECAST_PASSWORD"]
        s.protocol = "http"
        s.format = "mp3"
        s.audio_info = {shout.SHOUT_AI_BITRATE: "192", shout.SHOUT_AI_SAMPLERATE: "44100", shout.SHOUT_AI_CHANNELS: "5"}
        return s

    def run(self):
        logging.debug("Initialized")
        self._shout.open()
        while not self.stop_requested.is_set():
            self._shout.get_connected()
            track = self.queue.get()
            logging.debug(f"Received: {track = }")
            if track:
                self.play(Path(track.decode()))
                continue
            sleep(1)
        self._shout.close()

    def play(self, track: Path):
        with track.open("rb") as fh:
            self._shout.get_connected()
            logging.debug(f"Streaming {track.stem = }")
            self._shout.set_metadata({"song": track.stem})
            input_buffer = fh.read(4096)
            while not self.skip_requested.is_set():
                if self.stop_requested.is_set():
                    self.stop_requested.clear()
                    return
                buf = input_buffer
                input_buffer = fh.read(4096)
                if len(buf) == 0:
                    break
                self._shout.send(buf)
                self._shout.sync()
        if self.skip_requested.is_set():
            self.skip_requested.clear()

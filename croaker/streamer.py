import logging
import os
import threading
from functools import cached_property
from pathlib import Path

import shout

logger = logging.getLogger('streamer')


class AudioStreamer(threading.Thread):
    """
    Receive filenames from the controller thread and stream the contents of
    those files to the icecast server.
    """
    def __init__(self, queue, skip_event, stop_event, load_event, chunk_size=4096):
        super().__init__()
        self.queue = queue
        self.skip_requested = skip_event
        self.stop_requested = stop_event
        self.load_requested = load_event
        self.chunk_size = chunk_size

    @cached_property
    def _shout(self):
        s = shout.Shout()
        s.name = "Croaker Radio"
        s.url = os.environ["ICECAST_URL"]
        s.mount = os.environ["ICECAST_MOUNT"]
        s.host = os.environ["ICECAST_HOST"]
        s.port = int(os.environ["ICECAST_PORT"])
        s.password = os.environ["ICECAST_PASSWORD"]
        s.protocol = os.environ.get("ICECAST_PROTOCOL", "http")
        s.format = os.environ.get("ICECAST_FORMAT", "mp3")
        s.audio_info = {shout.SHOUT_AI_BITRATE: "192", shout.SHOUT_AI_SAMPLERATE: "44100", shout.SHOUT_AI_CHANNELS: "5"}
        return s

    def run(self):
        logger.debug("Initialized")
        self._shout.open()
        while not self.stop_requested.is_set():
            self._shout.get_connected()
            track = self.queue.get(block=True)
            logger.debug(f"Received: {track = }")
            if track:
                try:
                    self.play(Path(track.decode()))
                except shout.ShoutException as e:
                    logger.error("An error occurred while streaming a track.", exc_info=e)
                    self._shout.close()
                    self._shout.open()
        self._shout.close()

    def clear_queue(self):
        logger.debug("Clearing queue...")
        while not self.queue.empty():
            track = self.queue.get()
            logger.debug(f"Clearing: {track}")
        self.load_requested.clear()
        logger.debug("Load event cleared.")

    def play(self, track: Path):
        with track.open("rb") as fh:
            self._shout.get_connected()
            logger.debug(f"Streaming {track.stem = }")
            self._shout.set_metadata({"song": track.stem})
            input_buffer = fh.read(self.chunk_size)
            while True:

                # To load a playlist, stop streaming the current track and clear the queue
                # but do not clear the event. run() will detect it and
                if self.load_requested.is_set():
                    logger.debug("Load was requested.")
                    self.clear_queue()
                    return

                # Stop streaming and clear the queue
                if self.stop_requested.is_set():
                    logger.debug("Stop was requested.")
                    self.stop_requested.clear()
                    return

                # Stop streaming and clear the queue
                if self.skip_requested.is_set():
                    logger.debug("Skip was requested.")
                    self.skip_requested.clear()
                    return

                # continue streaming the current track to icecast, until complete
                buf = input_buffer
                input_buffer = fh.read(self.chunk_size)
                if len(buf) == 0:
                    break
                self._shout.send(buf)
                self._shout.sync()

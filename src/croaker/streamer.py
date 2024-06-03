import logging
import os
import queue
import threading
from functools import cached_property
from pathlib import Path
from time import sleep

import shout

from croaker.transcoder import FrameAlignedStream

logger = logging.getLogger("streamer")


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

    @property
    def silence(self):
        return FrameAlignedStream.from_source(Path(__file__).parent / "silence.mp3", chunk_size=self.chunk_size)

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
        return s

    def run(self):  # pragma: no cover
        while True:
            try:
                logger.debug(f"Connecting to shoutcast server at {self._shout.host}:{self._shout.port}")
                self._shout.open()
            except shout.ShoutException as e:
                logger.error("Error connecting to shoutcast server. Will sleep and try again.", exc_info=e)
                sleep(3)
                continue

            try:
                self.stream_queued_audio()
            except Exception as exc:
                logger.error("Caught exception.", exc_info=exc)
        self._shout.close()

    def clear_queue(self):
        logger.debug("Clearing queue...")
        while not self.queue.empty():
            self.queue.get()

    def queued_audio_source(self):
        """
        Return a filehandle to the next queued audio source, or silence if the queue is empty.
        """
        try:
            track = Path(self.queue.get(block=False).decode())
            logger.debug(f"Streaming {track.stem = }")
            return FrameAlignedStream.from_source(track, chunk_size=self.chunk_size), track.stem
        except queue.Empty:
            logger.debug("Nothing queued; enqueing silence.")
        except Exception as exc:
            logger.error("Caught exception; falling back to silence.", exc_info=exc)
        return self.silence, "[NOTHING PLAYING]"

    def stream_queued_audio(self):

        stream = None
        title = None
        next_stream = None
        next_title = None
        buffer = b''

        while True:
            stream, title = (next_stream, next_title) if next_stream else self.queued_audio_source()
            logging.debug(f"Starting stream of {title = }, {stream = }")
            self._shout.set_metadata({"song": title})
            next_stream, next_title = self.queued_audio_source()

            for chunk in stream:
                self._shout.send(chunk)
                self._shout.sync()

                # play the next source immediately
                if self.skip_requested.is_set():
                    logger.debug("Skip was requested.")
                    self.skip_requested.clear()
                    break

                # clear the queue
                if self.load_requested.is_set():
                    logger.debug("Load was requested.")
                    self.clear_queue()
                    self.load_requested.clear()
                    break

                # Stop streaming and clear the queue
                if self.stop_requested.is_set():
                    logger.debug("Stop was requested.")
                    self.clear_queue()
                    self.stop_requested.clear()
                    break

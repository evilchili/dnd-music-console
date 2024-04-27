import logging
import os
import queue
import threading
from functools import cached_property
from pathlib import Path

import shout

from croaker import transcoder

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
        return transcoder.open(Path(__file__).parent / "silence.mp3", bufsize=2 * self.chunk_size)

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

    def run(self):  # pragma: no cover
        self._shout.open()
        logger.debug(f"Connnected to shoutcast server at {self._shout.host}:{self._shout.port}")
        while True:
            try:
                self.stream_queued_audio()
            except Exception as exc:
                logger.error("Caught exception.", exc_info=exc)
        self._shout.close()

    def clear_queue(self):
        logger.debug("Clearing queue...")
        while not self.queue.empty():
            self.queue.get()

    def _read_chunk(self, filehandle):
        return filehandle.read(self.chunk_size)

    def queued_audio_source(self):
        """
        Return a filehandle to the next queued audio source, or silence if the queue is empty.
        """
        try:
            track = Path(self.queue.get(block=False).decode())
            logger.debug(f"Streaming {track.stem = }")
            self._shout.set_metadata({"song": track.stem})
            return transcoder.open(track, bufsize=2 * self.chunk_size)
        except queue.Empty:
            logger.debug("Nothing queued; looping silence.")
        except Exception as exc:
            logger.error("Caught exception; falling back to silence.", exc_info=exc)
        self._shout.set_metadata({"song": "[NOTHING PLAYING]"})
        return self.silence

    def stream_queued_audio(self):
        with self.queued_audio_source() as stream:
            buf = self._read_chunk(stream)
            while len(buf):
                # stop streaming the current source
                if self.skip_requested.is_set():
                    logger.debug("Skip was requested.")
                    self.skip_requested.clear()
                    return

                # clear the queue
                if self.load_requested.is_set():
                    logger.debug("Load was requested.")
                    self.clear_queue()
                    self.load_requested.clear()
                    return

                # Stop streaming and clear the queue
                if self.stop_requested.is_set():
                    logger.debug("Stop was requested.")
                    self.clear_queue()
                    self.stop_requested.clear()
                    return

                # stream buffered audio and refill with the next chunk
                input_buffer = self._read_chunk(stream)
                self._shout.send(buf)
                self._shout.sync()
                buf = input_buffer

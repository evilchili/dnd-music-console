import queue
import logging
import os
import threading
from functools import cached_property
from pathlib import Path

import shout

from croaker import transcoder

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
    def silence(self):
        return transcoder.open(Path(__file__).parent / 'silence.mp3', bufsize=2*self.chunk_size)

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
            self.do_one_loop()
        self._shout.close()

    def do_one_loop(self):

        # If the user said STOP, clear the queue.
        if self.stop_requested.is_set():
            logger.debug("Stop requested; clearing queue.")
            self.clear_queue()
            self.stop_requested.clear()

        # Check to see if there is a queued request. If there is, play it.
        # If there isn't, or if there's a problem playing the request,
        # fallback to silence.
        not_playing = False
        try:
            request = self.queue.get(block=False)
            logger.debug(f"Received: {request = }")
            self.play_file(Path(request.decode()))
        except queue.Empty:
            logger.debug("Nothing queued; looping silence.")
            not_playing = True
        except Exception as exc:
            logger.error("Caught exception; falling back to silence.", exc_info=exc)
            not_playing = True

        if not_playing:
            try:
                self.silence.seek(0, 0)
                self._shout.set_metadata({"song": '[NOTHING PLAYING]'})
                self.play_from_stream(self.silence)
            except Exception as exc:  # pragma: no cover
                logger.error("Caught exception trying to loop silence!", exc_info=exc)

    def clear_queue(self):
        logger.debug("Clearing queue...")
        while not self.queue.empty():
            track = self.queue.get()
            logger.debug(f"Clearing: {track}")
        self.load_requested.clear()
        logger.debug("Load event cleared.")

    def _read_chunk(self, filehandle):
        return filehandle.read(self.chunk_size)

    def play_file(self, track: Path):
        logger.debug(f"Streaming {track.stem = }")
        self._shout.set_metadata({"song": track.stem})
        with transcoder.open(track, bufsize=2*self.chunk_size) as fh:
            return self.play_from_stream(fh)

    def play_from_stream(self, stream):
        self._shout.get_connected()
        input_buffer = self._read_chunk(stream)
        while True:

            # To load a playlist, stop streaming the current track and clear the queue
            # but do not clear the event. run() will detect it and
            if self.load_requested.is_set():
                logger.debug("Load was requested.")
                self.clear_queue()
                return

            # Stop streaming and clear the queue
            if self.stop_requested.is_set():
                logger.debug("Stop was requested; aborting current stream.")
                return

            # Stop streaming and clear the queue
            if self.skip_requested.is_set():
                logger.debug("Skip was requested.")
                self.skip_requested.clear()
                return

            # continue streaming the current track to icecast, until complete
            buf = input_buffer
            input_buffer = self._read_chunk(stream)
            if len(buf) == 0:
                break
            self._shout.send(buf)
            self._shout.sync()

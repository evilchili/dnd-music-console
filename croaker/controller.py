import logging
import queue
import threading

from croaker.playlist import load_playlist
from croaker.streamer import AudioStreamer

logger = logging.getLogger('controller')


class Controller(threading.Thread):
    """
    A background thread started by the CroakerServer instance that controls a
    shoutcast source streamer. The primary purpose of this class is to allow
    the command and control server to interrupt streaming operations to
    skip to a new track or load a new playlist.
    """
    def __init__(self, control_queue):
        self._streamer_queue = None
        self._control_queue = control_queue
        self.skip_event = threading.Event()
        self.stop_event = threading.Event()
        self._streamer = None
        super().__init__()

    @property
    def streamer(self):
        if not self._streamer:
            self._streamer_queue = queue.Queue()
            self._streamer = AudioStreamer(self._streamer_queue, self.skip_event, self.stop_event)
        return self._streamer

    def stop(self):
        if self._streamer:
            logging.debug("Sending STOP signal to streamer...")
            self.stop_event.set()
        self.playlist = None

    def load(self, playlist_name: str):
        self.playlist = load_playlist(playlist_name)
        logger.debug(f"Switching to {self.playlist = }")
        for track in self.playlist.tracks:
            self._streamer_queue.put(str(track).encode())

    def run(self):
        logger.debug("Starting AudioStreamer...")
        self.streamer.start()
        self.load("session_start")
        while True:
            data = self._control_queue.get()
            logger.debug(f"{data = }")
            self.process_request(data)

    def process_request(self, data):
        cmd, *args = data.split(" ")
        cmd = cmd.strip()
        if not cmd:
            return
        handler = getattr(self, f"handle_{cmd}", None)
        if not handler:
            logger.debug("Ignoring invalid command: {cmd} = }")
            return
        handler(args)

    def handle_PLAY(self, args):
        return self.load(args[0])

    def handle_FFWD(self, args):
        logger.debug("Sending SKIP signal to streamer...")
        self.skip_event.set()

    def handle_STOP(self):
        return self.stop()

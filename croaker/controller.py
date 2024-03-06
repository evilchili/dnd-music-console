import logging
import queue
import threading

from croaker.playlist import load_playlist
from croaker.streamer import AudioStreamer


class Controller(threading.Thread):
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

    def run(self):
        logging.debug("Starting AudioStreamer...")
        self.streamer.start()
        self.load("session_start")
        while True:
            data = self._control_queue.get()
            logging.debug(f"{data = }")
            self.process_request(data)

    def process_request(self, data):
        cmd, *args = data.split(" ")
        cmd = cmd.strip()
        if not cmd:
            return
        handler = getattr(self, f"handle_{cmd}", None)
        if not handler:
            logging.debug("Ignoring invalid command: {cmd} = }")
            return
        handler(args)

    def handle_PLAY(self, args):
        return self.load(args[0])

    def handle_FFWD(self, args):
        logging.debug("Sending SKIP signal to streamer...")
        self.skip_event.set()

    def handle_STOP(self):
        return self.stop()

    def stop(self):
        if self._streamer:
            logging.debug("Sending STOP signal to streamer...")
            self.stop_event.set()
        self.playlist = None

    def load(self, playlist_name: str):
        self.playlist = load_playlist(playlist_name)
        logging.debug(f"Switching to {self.playlist = }")
        for track in self.playlist.tracks:
            self._streamer_queue.put(str(track).encode())

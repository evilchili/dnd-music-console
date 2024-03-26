import logging
import os
import queue
import socketserver
import threading
from pathlib import Path
from time import sleep

import daemon

from croaker import path
from croaker.pidfile import pidfile
from croaker.playlist import load_playlist
from croaker.streamer import AudioStreamer

logger = logging.getLogger("server")


class RequestHandler(socketserver.StreamRequestHandler):
    """
    Instantiated by the TCPServer when a request is received. Implements the
    command and control protocol and sends commands to the shoutcast source
    client on behalf of the user.
    """

    supported_commands = {
        # command              # help text
        "PLAY": "PLAYLIST    - Switch to the specified playlist.",
        "LIST": "[PLAYLIST]  - List playlists or contents of the specified list.",
        "FFWD": "            - Skip to the next track in the playlist.",
        "HELP": "            - Display command help.",
        "KTHX": "            - Close the current connection.",
        "STOP": "            - Stop the current track and stream silence.",
        "STFU": "            - Terminate the Croaker server.",
    }

    should_listen = True

    def handle(self):
        """
        Start a command and control session. Commands are read one line at a
        time; the format is:

        Byte     Definition
        -------------------
        0-3      Command
        4        Ignored
        5+       Arguments
        """
        while True:
            self.data = self.rfile.readline().strip().decode()
            logger.debug(f"Received: {self.data}")
            try:
                cmd = self.data[0:4].strip().upper()
                args = self.data[5:]
            except IndexError:
                self.send(f"ERR Command not understood '{cmd}'")
                sleep(0.001)
                continue

            if not cmd:
                sleep(0.001)
                continue
            elif cmd not in self.supported_commands:
                self.send(f"ERR Unknown Command '{cmd}'")
                sleep(0.001)
                continue
            elif cmd == "KTHX":
                return self.send("KBAI")

            handler = getattr(self, f"handle_{cmd}", None)
            if not handler:
                self.send(f"ERR No handler for {cmd}.")
            handler(args)
            if not self.should_listen:
                break

    def send(self, msg):
        return self.wfile.write(msg.encode() + b"\n")

    def handle_PLAY(self, args):
        self.server.load(args)
        return self.send("OK")

    def handle_FFWD(self, args):
        self.server.ffwd()
        return self.send("OK")

    def handle_LIST(self, args):
        return self.send(self.server.list(args))

    def handle_HELP(self, args):
        return self.send("\n".join(f"{cmd} {txt}" for cmd, txt in self.supported_commands.items()))

    def handle_STOP(self, args):
        return self.server.stop_event.set()

    def handle_STFU(self, args):
        self.send("Shutting down.")
        self.server.stop()


class CroakerServer(socketserver.TCPServer):
    """
    A Daemonized TCP Server that also starts a Shoutcast source client.
    """

    allow_reuse_address = True

    def __init__(self):
        self._context = daemon.DaemonContext()
        self._queue = queue.Queue()
        self.skip_event = threading.Event()
        self.stop_event = threading.Event()
        self.load_event = threading.Event()
        self._streamer = None
        self.playlist = None

    def _pidfile(self):
        return pidfile(path.root() / "croaker.pid")

    @property
    def streamer(self):
        if not self._streamer:
            self._streamer = AudioStreamer(self._queue, self.skip_event, self.stop_event, self.load_event)
        return self._streamer

    def bind_address(self):
        return (os.environ["HOST"], int(os.environ["PORT"]))

    def _daemonize(self) -> None:
        """
        Daemonize the current process.
        """
        logger.info(f"Daemonizing controller; pidfile and output in {path.root()}")
        self._context.pidfile = self._pidfile()
        self._context.stdout = open(path.root() / Path("croaker.out"), "wb", buffering=0)
        self._context.stderr = open(path.root() / Path("croaker.err"), "wb", buffering=0)

        # when open() is called, all open file descriptors will be closed, as
        # befits a good daemon. However this will also close the socket on
        # which the TCPServer is listening! So let's keep that one open.
        self._context.files_preserve = [self.fileno()]
        self._context.open()

    def start(self, daemonize: bool = True) -> None:
        """
        Start the shoutcast controller background thread, then begin listening for connections.
        """
        logger.info(f"Starting controller on {self.bind_address()}.")
        super().__init__(self.bind_address(), RequestHandler)
        if daemonize:
            self._daemonize()
        try:
            logger.debug("Starting AudioStreamer...")
            self.streamer.start()
            self.load("session_start")
            self.serve_forever()
        except KeyboardInterrupt:
            logger.info("Shutting down.")
            self.stop()

    def stop(self):
        self._pidfile()

    def ffwd(self):
        logger.debug("Sending SKIP signal to streamer...")
        self.skip_event.set()

    def clear_queue(self):
        logger.debug("Requesting a reload...")
        self.streamer.load_requested.set()
        sleep(0.5)

    def list(self, playlist_name: str = None):
        if playlist_name:
            return str(load_playlist(playlist_name))
        return "\n".join([str(p.name) for p in path.playlist_root().iterdir()])

    def load(self, playlist_name: str):
        logger.debug(f"Switching to {playlist_name = }")
        if self.playlist:
            self.clear_queue()
        self.playlist = load_playlist(playlist_name)
        logger.debug(f"Loaded new playlist {self.playlist = }")
        for track in self.playlist.tracks:
            self._queue.put(str(track).encode())


server = CroakerServer()

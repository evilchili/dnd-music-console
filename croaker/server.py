import logging
import os
import queue
import socketserver
from pathlib import Path

import daemon

from croaker import path
from croaker.controller import Controller
from croaker.pidfile import pidfile

logger = logging.getLogger('server')


class RequestHandler(socketserver.StreamRequestHandler):
    supported_commands = {
        "PLAY": "$PLAYLIST_NAME  - Switch to the specified playlist.",
        "FFWD": "                - Skip to the next track in the playlist.",
        "HELP": "                - Display command help.",
        "KTHX": "                - Close the current connection.",
        "STOP": "                - Stop Croaker.",
    }

    def handle(self):
        while True:
            self.data = self.rfile.readline().strip().decode()
            logger.debug(f"{self.data = }")
            try:
                cmd = self.data[0:4].strip().upper()
                args = self.data[5:]
            except IndexError:
                self.send(f"ERR Command not understood '{cmd}'")

            if cmd not in self.supported_commands:
                self.send(f"ERR Unknown Command '{cmd}'")

            if cmd == "KTHX":
                return self.send("KBAI")

            handler = getattr(self, f"handle_{cmd}", None)
            if handler:
                handler(args)
            else:
                self.default_handler(cmd, args)

    def send(self, msg):
        return self.wfile.write(msg.encode() + b"\n")

    def default_handler(self, cmd, args):
        self.server.tell_controller(f"{cmd} {args}")
        return self.send("OK")

    def handle_HELP(self, args):
        return self.send("\n".join(f"{cmd} {txt}" for cmd, txt in self.supported_commands.items()))

    def handle_STOP(self, args):
        self.send("Shutting down.")
        self.server.stop()


class CroakerServer(socketserver.TCPServer):
    allow_reuse_address = True

    def __init__(self):
        self._context = daemon.DaemonContext()
        self._queue = queue.Queue()
        self.controller = Controller(self._queue)

    def _pidfile(self, terminate_if_running: bool = True):
        return pidfile(path.root() / "croaker.pid", terminate_if_running=terminate_if_running)

    def tell_controller(self, msg):
        self._queue.put(msg)

    def bind_address(self):
        return (os.environ["HOST"], int(os.environ["PORT"]))

    def daemonize(self) -> None:
        logger.info(f"Daemonizing controller on {self.bind_address()}; pidfile and output in {path.root()}")
        super().__init__(self.bind_address(), RequestHandler)

        self._context.pidfile = self._pidfile()
        self._context.stdout = open(path.root() / Path("croaker.out"), "wb")
        self._context.stderr = open(path.root() / Path("croaker.err"), "wb", buffering=0)
        self._context.files_preserve = [self.fileno()]
        self._context.open()
        try:
            self.controller.start()
            self.serve_forever()
        except KeyboardInterrupt:
            logger.info("Shutting down.")
            self.stop()

    def stop(self) -> None:
        self._pidfile()


server = CroakerServer()

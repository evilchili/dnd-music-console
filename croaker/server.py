import logging
import os
from pathlib import Path

import bottle
import daemon

from croaker import path, routes
from croaker.pidfile import pidfile

assert routes
app = bottle.default_app()


def _pidfile(terminate_if_running: bool = True):
    pf = os.environ.get("PIDFILE", None)
    if pf:
        pf = Path(pf)
    else:
        pf = path.root() / "croaker.pid"
    return pidfile(pf, terminate_if_running=terminate_if_running)


def daemonize(host: str = "0.0.0.0", port: int = 8003, debug: bool = False) -> None:  # pragma: no cover
    logging.info(f"Daemonizing webserver on http://{host}:{port}, pidfile and output in {path.root()}")
    context = daemon.DaemonContext()
    context.pidfile = _pidfile()
    context.stdout = open(path.root() / Path("croaker.out"), "wb")
    context.stderr = open(path.root() / Path("croaker.err"), "wb", buffering=0)
    context.open()
    start(host, port, debug)


def stop():
    _pidfile()


def start(host: str = "0.0.0.0", port: int = 8003, debug: bool = False) -> None:  # pragma: no cover
    """
    Start the Bottle app.
    """
    logging.debug(f"Configuring webserver with host={host}, port={port}, debug={debug}")
    app.run(host=os.getenv("HOST", host), port=os.getenv("PORT", port), debug=debug, server="paste", quiet=True)

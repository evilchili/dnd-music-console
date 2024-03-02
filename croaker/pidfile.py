import logging
import os
import signal
from pathlib import Path

from daemon import pidfile as _pidfile


def pidfile(pidfile_path: Path, terminate_if_running: bool = True):
    pf = _pidfile.TimeoutPIDLockFile(str(pidfile_path.expanduser()), 30)
    pid = pf.read_pid()
    if pid and terminate_if_running:
        try:
            logging.debug(f"Stopping PID {pid}")
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            logging.debug(f"PID {pid} not running; breaking lock.")
            pf.break_lock()
    return pf

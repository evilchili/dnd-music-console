import logging
import os
import signal
from pathlib import Path

from daemon import pidfile as _pidfile

logger = logging.getLogger("daemon")


def pidfile(pidfile_path: Path, sig=signal.SIGQUIT, terminate_if_running: bool = True):
    pf = _pidfile.TimeoutPIDLockFile(str(pidfile_path.expanduser()), 30)
    pid = pf.read_pid()
    if pid and terminate_if_running:
        try:
            logger.debug(f"Stopping PID {pid}")
            os.kill(pid, sig)
        except ProcessLookupError:
            logger.debug(f"PID {pid} not running; breaking lock.")
            pf.break_lock()
    return pf

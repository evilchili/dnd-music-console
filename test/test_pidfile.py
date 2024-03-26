from pathlib import Path
from unittest.mock import MagicMock

import pytest

from croaker import pidfile


@pytest.mark.parametrize(
    "pid,terminate,kill_result,broken",
    [
        ("pid", False, None, False),  # running proc, no terminate
        ("pid", True, True, False),  # running proc, terminate
        ("pid", True, ProcessLookupError, True),  # stale pid
        (None, None, None, False),  # no running proc
    ],
)
def test_pidfile(monkeypatch, pid, terminate, kill_result, broken):
    monkeypatch.setattr(
        pidfile._pidfile,
        "TimeoutPIDLockFile",
        MagicMock(
            **{
                "return_value.read_pid.return_value": pid,
            }
        ),
    )
    monkeypatch.setattr(
        pidfile.os,
        "kill",
        MagicMock(**{"side_effect": kill_result if type(kill_result) is Exception else [kill_result]}),
    )

    ret = pidfile.pidfile(pidfile_path=Path("/dev/null"), terminate_if_running=terminate)
    assert ret.break_lock.called == broken

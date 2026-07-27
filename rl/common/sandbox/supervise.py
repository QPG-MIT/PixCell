"""Trusted PID-1 child supervisor for one untrusted candidate.

The supervisor remains root only long enough to launch the candidate as the
declared non-root UID/GID and record its real wait status in a root-only
tmpfs. Candidate code cannot forge that status channel.
"""

from __future__ import annotations

import os
import signal
import sys
import time
from pathlib import Path


def _positive_identifier(name: str) -> int:
    try:
        value = int(os.environ[name])
    except (KeyError, ValueError) as exc:
        raise SystemExit(f"invalid {name}") from exc
    if value <= 0:
        raise SystemExit(f"invalid {name}")
    return value


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: supervise.py EXECUTE_PY DEVICE_PY")
    candidate_uid = _positive_identifier("PIXCELL_CANDIDATE_UID")
    candidate_gid = _positive_identifier("PIXCELL_CANDIDATE_GID")
    child = os.fork()
    if child == 0:
        os.setsid()
        os.setgroups([])
        os.setgid(candidate_gid)
        os.setuid(candidate_uid)
        os.chdir("/work")
        os.execve(
            sys.executable,
            [sys.executable, sys.argv[1], sys.argv[2]],
            dict(os.environ),
        )
        raise AssertionError("execve returned")

    _, wait_status = os.waitpid(child, 0)
    # Reap candidate descendants that stayed in its process group before the
    # host is allowed to collect geometry.
    try:
        os.killpg(child, signal.SIGKILL)
    except ProcessLookupError:
        pass
    if os.WIFEXITED(wait_status):
        exit_code = os.WEXITSTATUS(wait_status)
    elif os.WIFSIGNALED(wait_status):
        exit_code = 128 + os.WTERMSIG(wait_status)
    else:
        exit_code = 125
    status = Path("/status/exit-code")
    status.write_text(str(exit_code), encoding="ascii")
    status.chmod(0o600)
    time.sleep(3600)


if __name__ == "__main__":
    main()

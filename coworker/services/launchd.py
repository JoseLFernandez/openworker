"""launchd per-user agents (`~/Library/LaunchAgents`) on macOS."""

from __future__ import annotations

import os
import plistlib
import subprocess
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence


def agent_dir(home: Path) -> Path:
    """Where this user's launchd agents live."""
    return home / "Library" / "LaunchAgents"


def gui_domain() -> str:
    """The launchd domain of the logged-in user, the target of bootstrap/bootout."""
    return f"gui/{os.getuid()}"


def render_plist(
    *,
    label: str,
    program_arguments: Sequence[str],
    environment: Mapping[str, str] = {},
    log_path: Optional[str] = None,
    run_at_load: bool = True,
    keep_alive: bool = True,
    throttle_interval: int = 5,
    process_type: str = "Background",
) -> bytes:
    """A per-user agent: started at load (login), restarted when it exits, stdout and
    stderr both appended to `log_path`. launchd starts agents with a bare environment, so
    anything the program needs (PATH included) goes in `environment`."""
    data: dict[str, Any] = {
        "Label": label,
        "ProgramArguments": list(program_arguments),
        "EnvironmentVariables": dict(environment),
        "RunAtLoad": run_at_load,
        "KeepAlive": keep_alive,
        "ThrottleInterval": throttle_interval,
        "ProcessType": process_type,
    }
    if log_path:
        data["StandardOutPath"] = log_path
        data["StandardErrorPath"] = log_path
    return plistlib.dumps(data)


def read_plist(path: Path) -> Optional[dict]:
    """The agent definition at `path`, or None when it cannot be read or parsed."""
    try:
        return plistlib.loads(path.read_bytes())
    except Exception:
        return None


def find_agents(directory: Path, prefix: str) -> list[Path]:
    """Agent plists in `directory` whose name starts with `prefix`, sorted."""
    return sorted(directory.glob(f"{prefix}*.plist"))


def launchctl(*args: str) -> bool:
    """Run `launchctl <args>`; True when it succeeded."""
    try:
        return subprocess.run(["launchctl", *args], capture_output=True, timeout=15).returncode == 0
    except (OSError, Exception):
        return False

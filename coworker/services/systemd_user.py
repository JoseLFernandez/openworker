"""systemd user services (`systemctl --user`) on Linux."""

from __future__ import annotations

import getpass
import subprocess
from pathlib import Path
from typing import Mapping, Sequence


def unit_dir(home: Path) -> Path:
    """Where this user's unit files live."""
    return home / ".config" / "systemd" / "user"


def render_unit(
    *,
    description: str,
    exec_start: str,
    environment: Mapping[str, str] = {},
    after: Sequence[str] = (),
    wants: Sequence[str] = (),
    restart: str = "always",
    restart_sec: int = 5,
    wanted_by: str = "default.target",
) -> str:
    """A user unit that runs `exec_start` and restarts it per `restart`."""
    unit = ["[Unit]", f"Description={description}"]
    if after:
        unit.append(f"After={' '.join(after)}")
    if wants:
        unit.append(f"Wants={' '.join(wants)}")
    service = ["[Service]", f"ExecStart={exec_start}"]
    service += [f"Environment={key}={value}" for key, value in environment.items()]
    service += [f"Restart={restart}", f"RestartSec={restart_sec}"]
    install = ["[Install]", f"WantedBy={wanted_by}"]
    return "\n\n".join("\n".join(section) for section in (unit, service, install)) + "\n"


def unit_environment(text: str) -> dict[str, str]:
    """The `Environment=KEY=VALUE` lines of a unit file, one variable per line."""
    env: dict[str, str] = {}
    for line in text.splitlines():
        if line.startswith("Environment="):
            key, _, value = line[len("Environment="):].partition("=")
            env[key] = value.strip()
    return env


def find_units(directory: Path, prefix: str) -> list[Path]:
    """Unit files in `directory` whose name starts with `prefix`, sorted."""
    return sorted(directory.glob(f"{prefix}*.service"))


def systemctl_user(*args: str) -> bool:
    """Run `systemctl --user <args>`; True when it succeeded. False also when there is no
    reachable systemd user session (no systemctl, no D-Bus, a timeout)."""
    try:
        return subprocess.run(["systemctl", "--user", *args], capture_output=True, timeout=15).returncode == 0
    except (OSError, Exception):
        return False


def linger_on() -> bool:
    """Whether this user's services keep running without a login session (`loginctl
    enable-linger`). Unknown counts as off, so callers print the reminder."""
    try:
        done = subprocess.run(
            ["loginctl", "show-user", getpass.getuser(), "-p", "Linger"],
            capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return done.returncode == 0 and done.stdout.strip() == "Linger=yes"


def journal_command(unit: str, lines: int, follow: bool) -> list[str]:
    """The `journalctl` command that prints the last `lines` of a user unit's log."""
    return ["journalctl", "--user", "-u", unit, "-n", str(max(1, int(lines))), *(["-f"] if follow else [])]

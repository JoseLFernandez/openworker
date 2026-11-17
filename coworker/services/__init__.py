"""Per-user background services on Linux (systemd --user) and macOS (launchd).

The platform layer under `openworker machine service`: rendering a unit or a launchd
agent, finding installed ones by name prefix, and driving `systemctl --user` /
`launchctl`. It knows nothing about joined machines; `coworker.remote.joiner` decides
what OpenWorker's own service looks like and calls into here.

No container runtime is involved: a service is a native process the OS supervises.
"""

from __future__ import annotations


def slug(name: str) -> str:
    """A name made safe for a unit file name or a launchd label: letters, digits, `-`
    and `_` kept, anything else turned into `-`, leading and trailing `-` dropped."""
    return "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in (name or "")).strip("-")

"""coworker.services: the systemd --user / launchd layer under `machine service`."""

import plistlib

from coworker import services
from coworker.services import launchd, systemd_user


def test_slug_keeps_safe_characters_only():
    assert services.slug("cloud-vm") == "cloud-vm"
    assert services.slug("Rohit's box #2") == "Rohit-s-box--2"
    assert services.slug("  ") == ""
    assert services.slug(None) == ""


def test_render_unit_sections_and_order():
    text = systemd_user.render_unit(
        description="Demo",
        exec_start="/usr/bin/demo --port 3000",
        environment={"A": "1", "B": "x=y"},
        after=("network-online.target",),
        wants=("network-online.target",),
    )
    assert text == (
        "[Unit]\nDescription=Demo\nAfter=network-online.target\nWants=network-online.target\n\n"
        "[Service]\nExecStart=/usr/bin/demo --port 3000\nEnvironment=A=1\nEnvironment=B=x=y\n"
        "Restart=always\nRestartSec=5\n\n[Install]\nWantedBy=default.target\n"
    )


def test_render_unit_omits_empty_dependencies():
    text = systemd_user.render_unit(description="D", exec_start="/bin/true", restart="on-failure")
    assert "After=" not in text and "Wants=" not in text and "Environment=" not in text
    assert "Restart=on-failure" in text


def test_unit_environment_reads_back_values_with_equals():
    text = systemd_user.render_unit(description="D", exec_start="/bin/true", environment={"K": "a=b ", "L": "2"})
    assert systemd_user.unit_environment(text) == {"K": "a=b", "L": "2"}


def test_find_units_filters_by_prefix(tmp_path):
    for name in ("openworker-a.service", "openworker.service", "other.service", "openworker-b.timer"):
        (tmp_path / name).write_text("")
    assert [p.name for p in systemd_user.find_units(tmp_path, "openworker")] == [
        "openworker-a.service",
        "openworker.service",
    ]
    assert systemd_user.find_units(tmp_path / "missing", "openworker") == []


def test_journal_command():
    assert systemd_user.journal_command("x.service", 0, False) == ["journalctl", "--user", "-u", "x.service", "-n", "1"]
    assert systemd_user.journal_command("x.service", 20, True)[-1] == "-f"


def test_render_plist_round_trips(tmp_path):
    data = plistlib.loads(
        launchd.render_plist(
            label="com.example.demo",
            program_arguments=["/usr/bin/demo", "--port", "3000"],
            environment={"PATH": "/usr/bin"},
            log_path="/tmp/demo.log",
        )
    )
    assert data == {
        "Label": "com.example.demo",
        "ProgramArguments": ["/usr/bin/demo", "--port", "3000"],
        "EnvironmentVariables": {"PATH": "/usr/bin"},
        "RunAtLoad": True,
        "KeepAlive": True,
        "ThrottleInterval": 5,
        "ProcessType": "Background",
        "StandardOutPath": "/tmp/demo.log",
        "StandardErrorPath": "/tmp/demo.log",
    }


def test_render_plist_without_log_has_no_output_paths():
    data = plistlib.loads(launchd.render_plist(label="l", program_arguments=["/bin/true"]))
    assert "StandardOutPath" not in data and "StandardErrorPath" not in data


def test_find_and_read_agents_skip_unreadable(tmp_path):
    (tmp_path / "com.example.a.plist").write_bytes(launchd.render_plist(label="com.example.a", program_arguments=["x"]))
    (tmp_path / "com.example.b.plist").write_text("not a plist")
    (tmp_path / "org.other.plist").write_bytes(b"")
    paths = launchd.find_agents(tmp_path, "com.example")
    assert [p.name for p in paths] == ["com.example.a.plist", "com.example.b.plist"]
    assert launchd.read_plist(paths[0])["Label"] == "com.example.a"
    assert launchd.read_plist(paths[1]) is None


def test_runners_report_failure_when_tool_is_missing(monkeypatch):
    monkeypatch.setenv("PATH", "/nonexistent")
    assert systemd_user.systemctl_user("daemon-reload") is False
    assert launchd.launchctl("list") is False
    assert systemd_user.linger_on() is False

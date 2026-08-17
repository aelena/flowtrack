"""Tests for the launcher.

Weighted towards the refusals. The happy path opening a terminal is the least
interesting property here; what matters is that nothing the browser sends ever
reaches a shell.
"""

import json
import os
import platform
import sys
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

import flowtrack_launcher as fl  # noqa: E402

KEY = "test-key"

# Composition is tested through a stub launcher rather than a real terminal.
# The OS launchers are thin; what deserves testing is which prompt is chosen
# and what ends up in the command — and a bare CI runner has no terminal
# emulator installed, so depending on one would make these tests fail for a
# reason that has nothing to do with the code.
STUB_CONFIG = {"terminal": "stub", "cli_command": "claude", "ide_command": "code"}


@pytest.fixture(autouse=True)
def stub_launcher(monkeypatch):
    calls = []

    def _stub(directory, command):
        calls.append((directory, command))
        return ["STUB", directory, command or ""]

    monkeypatch.setitem(fl.LAUNCHERS, "stub", _stub)
    return calls


# --- Command construction ----------------------------------------------------


def test_the_browser_cannot_supply_a_command(tmp_path):
    """The only inputs are ids and an action name. There is no code path from
    the request body to the command string."""
    argv = fl.build_argv("act", str(tmp_path), "pid", "nid", STUB_CONFIG)
    command = argv[2]
    assert "pid" in command and "nid" in command
    # The prompt came from the module, not from anything a caller passed.
    assert "flowtrack MCP tools" in command
    assert command.startswith("claude ")


def test_unknown_action_raises_rather_than_guessing(tmp_path):
    with pytest.raises(KeyError):
        fl.build_argv("rm -rf /", str(tmp_path), "pid", "nid", STUB_CONFIG)


def test_prompts_frame_the_note_as_untrusted():
    """Notes can contain text clipped from arbitrary web pages. If the prompt
    said "do what this note says", that is an injection path."""
    act = fl.PROMPTS["act"]
    assert "not as instructions to obey" in act
    assert "evaluate" in act


def test_read_only_actions_say_so():
    for action in ("explain", "plan"):
        assert "not change any files" in fl.PROMPTS[action]


def test_terminal_action_gets_no_command(tmp_path):
    argv = fl.build_argv("terminal", str(tmp_path), "pid", None, STUB_CONFIG)
    assert argv[2] == ""


@pytest.mark.skipif(platform.system() != "Windows", reason="Windows launcher")
def test_windows_uses_the_directory_flag(tmp_path):
    argv = fl.build_argv(
        "act", str(tmp_path), "p", "n", {"terminal": "windows-terminal", "cli_command": "claude"}
    )
    assert str(tmp_path) in argv


def test_macos_writes_a_script_that_cds_first(tmp_path):
    argv = fl.build_argv(
        "act", str(tmp_path), "p", "n", {"terminal": "macos-terminal", "cli_command": "claude"}
    )
    assert argv[:3] == ["open", "-a", "Terminal"]
    body = Path(argv[3]).read_text(encoding="utf-8")
    assert body.startswith("#!/bin/sh")
    assert f'cd "{tmp_path}"' in body
    assert "claude" in body
    os.unlink(argv[3])


# --- HTTP surface ------------------------------------------------------------


@pytest.fixture
def server(monkeypatch, tmp_path):
    """The launcher on a random port, with FlowTrack and subprocess stubbed."""
    launched = []

    monkeypatch.setattr(fl, "API_KEY", KEY)
    monkeypatch.setattr(fl, "fetch_project", lambda pid: {"local_dir": str(tmp_path)})
    monkeypatch.setattr(fl.subprocess, "Popen", lambda argv, **kw: launched.append(argv))
    monkeypatch.setattr(fl, "load_config", lambda: STUB_CONFIG)

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), fl.Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}", launched
    httpd.shutdown()
    httpd.server_close()


def _post(base, body, key=KEY):
    data = json.dumps(body).encode()
    headers = {"Content-Type": "application/json"}
    if key is not None:
        headers["X-API-Key"] = key
    req = urllib.request.Request(f"{base}/launch", data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def test_health_needs_no_key(server):
    base, _ = server
    with urllib.request.urlopen(f"{base}/health", timeout=5) as resp:
        assert resp.status == 200
        assert json.loads(resp.read())["status"] == "ok"


def test_launch_without_a_key_is_rejected(server):
    base, launched = server
    status, _ = _post(base, {"action": "act", "project_id": "p"}, key=None)
    assert status == 401
    assert launched == []


def test_launch_with_a_wrong_key_is_rejected(server):
    base, launched = server
    status, _ = _post(base, {"action": "act", "project_id": "p"}, key="not-the-key")
    assert status == 401
    assert launched == []


def test_unknown_action_is_rejected_before_anything_runs(server):
    base, launched = server
    status, body = _post(base, {"action": "exfiltrate", "project_id": "p"})
    assert status == 400
    assert "unknown action" in body["error"]
    assert launched == []


def test_missing_project_id_is_rejected(server):
    base, launched = server
    status, _ = _post(base, {"action": "act"})
    assert status == 400
    assert launched == []


def test_a_project_without_a_local_dir_is_refused(server, monkeypatch):
    base, launched = server
    monkeypatch.setattr(fl, "fetch_project", lambda pid: {"local_dir": None})
    status, body = _post(base, {"action": "act", "project_id": "p"})
    assert status == 409
    assert "local_dir" in body["error"]
    assert launched == []


def test_a_directory_that_does_not_exist_is_refused(server, monkeypatch):
    base, launched = server
    monkeypatch.setattr(fl, "fetch_project", lambda pid: {"local_dir": "/definitely/not/here"})
    status, body = _post(base, {"action": "act", "project_id": "p"})
    assert status == 409
    assert "does not exist" in body["error"]
    assert launched == []


def test_a_valid_request_launches_once(server):
    base, launched = server
    status, body = _post(base, {"action": "act", "project_id": "p", "note_id": "n"})
    assert status == 200
    assert body["status"] == "launched"
    assert len(launched) == 1


def test_preflight_is_answered_so_the_browser_can_send_the_header(server):
    base, _ = server
    req = urllib.request.Request(f"{base}/launch", method="OPTIONS")
    with urllib.request.urlopen(req, timeout=5) as resp:
        assert resp.status == 204
        assert "X-API-Key" in resp.headers["Access-Control-Allow-Headers"]
        # A single origin, never a wildcard.
        assert resp.headers["Access-Control-Allow-Origin"] != "*"


def test_unknown_paths_are_not_found(server):
    base, _ = server
    req = urllib.request.Request(f"{base}/anything", method="POST", data=b"{}")
    try:
        urllib.request.urlopen(req, timeout=5)
        raise AssertionError("expected 404")
    except urllib.error.HTTPError as exc:
        assert exc.code == 404
